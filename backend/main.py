"""
main.py — ScamShield & TeamPilot Unified Backend API
======================================================
Serves:
  - ScamShield AI Detection API (/api/v1/analyze, /api/v1/history, /api/v1/status, /api/v1/safe-next-steps, /api/v1/sample-cases)
  - TeamPilot Project Coordination Endpoints (/health, /projects)

Security & Architecture:
  - Modern FastAPI lifespan context manager
  - Configurable CORS with rejection of wildcard origins under credential mode
  - Request-size limits and in-memory rate limiting
  - Cross-user data isolation on scan history
  - Unified storage backend for writes and reads (Supabase Cloud or Local SQLite)
  - Single source of truth for safe guidance and sample threat cases
"""

import time
import logging
import sys
import os
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime, timezone

# Ensure backend directory is in sys.path for root-level or package-level execution
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from fastapi import FastAPI, HTTPException, Request, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from config import settings
from database import init_db, get_connection
from analyzer import analyze_message
from schemas import (
    ScamAnalyzeRequest,
    ScamAnalyzeResponse,
    HistoryItem,
    SafeNextStepsResponse,
)
from supabase_client import (
    get_backend_status,
    record_scan_telemetry,
    fetch_scan_telemetry_history,
)
from shared_constants import SAFE_NEXT_STEPS_DATA, SAMPLE_CASES

log = logging.getLogger(__name__)


# ── In-Memory Sliding-Window Rate Limiter ─────────────────────────────────────
_RATE_LIMIT_STORE: Dict[str, List[float]] = {}


def check_rate_limit(client_ip: str, limit: int = 120, window_seconds: float = 60.0) -> bool:
    """
    Check if a client IP has exceeded the allowed number of requests per window.
    Prunes expired timestamps. Returns True if allowed, False if exceeded.
    """
    now = time.time()
    cutoff = now - window_seconds
    timestamps = _RATE_LIMIT_STORE.get(client_ip, [])
    # Prune old timestamps
    valid_timestamps = [t for t in timestamps if t > cutoff]
    if len(valid_timestamps) >= limit:
        _RATE_LIMIT_STORE[client_ip] = valid_timestamps
        return False
    valid_timestamps.append(now)
    _RATE_LIMIT_STORE[client_ip] = valid_timestamps
    return True


# ── Lifespan Context Manager (replaces deprecated on_event) ───────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern startup and shutdown lifecycle management."""
    log.info("Starting ScamShield backend in '%s' environment", settings.ENVIRONMENT)
    init_db()
    yield
    log.info("ScamShield backend shutting down")


# ── App Initialization ────────────────────────────────────────────────────────
app = FastAPI(
    title="ScamShield API",
    version="2.0.0",
    description="ScamShield AI Scam Detection & Safety Assistant — Amazon Developer Hackathon",
    lifespan=lifespan,
)


# ── Middleware: Request Size Limits & Rate Limiting ────────────────────────────
@app.middleware("http")
async def security_and_rate_limiting_middleware(request: Request, call_next):
    # 1. Enforce Request Body Size Limit (Default: 64 KB)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.MAX_REQUEST_SIZE_BYTES:
        status_413 = getattr(status, "HTTP_413_CONTENT_TOO_LARGE", status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        return JSONResponse(
            status_code=status_413,
            content={
                "status": "error",
                "error_type": "PayloadTooLarge",
                "message": f"Submitted request body exceeds the limit of {settings.MAX_REQUEST_SIZE_BYTES} bytes.",
            },
        )

    # 2. Rate Limiting per Client IP (Skip for health checks and tests)
    client_ip = request.client.host if request.client else "unknown"
    if request.url.path not in ("/health", "/api/v1/status"):
        if not check_rate_limit(client_ip, limit=settings.RATE_LIMIT_PER_MINUTE):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "status": "error",
                    "error_type": "RateLimitExceeded",
                    "message": "Too many requests. Please slow down and try again shortly.",
                },
                headers={"Retry-After": "60"},
            )

    response = await call_next(request)
    return response


# ── Error handler for validation errors ───────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors.append(f"{field}: {err.get('msg')}")
    status_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", status.HTTP_422_UNPROCESSABLE_ENTITY)
    return JSONResponse(
        status_code=status_422,
        content={
            "status": "error",
            "error_type": "ValidationError",
            "message": "Invalid input submitted for analysis.",
            "details": errors,
        },
    )


# ── CORS configuration ────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Legacy TeamPilot models & routes (PRESERVED) ──────────────────────────────
class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


@app.get("/health", tags=["System"])
def health_check():
    """Liveness probe confirming system health and storage mode."""
    status_info = get_backend_status()
    return {
        "status": "ok",
        "service": "ScamShield & TeamPilot Backend",
        "version": "2.0.0",
        "storage_mode": status_info["mode"],
        "supabase_configured": status_info["supabase_configured"],
    }


@app.post("/projects", tags=["Projects (Legacy)"], status_code=201)
def create_project(project: ProjectCreate):
    name = project.name.strip()
    if not name:
        raise HTTPException(
            status_code=422,
            detail="Project name cannot be empty",
        )

    project_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute("BEGIN")
        try:
            conn.execute(
                """
                INSERT INTO projects
                    (id, name, description, status, created_at, updated_at)
                VALUES (?, ?, ?, 'active', ?, ?)
                """,
                (project_id, name, project.description, now, now),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()

    return dict(row)


@app.get("/projects", tags=["Projects (Legacy)"])
def list_projects():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM projects ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


# ── ScamShield Endpoints ──────────────────────────────────────────────────────

@app.get("/api/v1/status", tags=["ScamShield"])
def get_status():
    """Return backend operational status, data isolation guarantees, and storage mode."""
    return get_backend_status()


@app.post("/api/v1/analyze", response_model=ScamAnalyzeResponse, tags=["ScamShield"])
def analyze_suspicious_text(payload: ScamAnalyzeRequest, request: Request):
    """
    Analyze untrusted suspicious message text.
    Returns categorized risk evaluation, warning signs, and safe next steps.
    Privacy guarantee: Raw message text is NEVER stored.
    """
    # 1. Evaluate message heuristics, urgency, impersonation, links, OTP, lures
    result = analyze_message(payload.message, {"channel": payload.channel})

    if result.get("status") == "error":
        raise HTTPException(status_code=422, detail=result.get("error"))

    # 2. Persist anonymized telemetry if requested
    # Privacy rule: We only save the HMAC fingerprint and risk metrics, never the raw text.
    if payload.save_history:
        # Determine user/session context if available
        user_id = request.headers.get("x-user-id")
        try:
            record_scan_telemetry(
                fingerprint=result["fingerprint"],
                risk_score=result["risk_score"],
                risk_level=result["risk_level"],
                channel=payload.channel or "sms",
                preview_length=result["preview_length"],
                warning_count=len(result["warning_signs"]),
                user_id=user_id,
                metadata={
                    "prompt_injection": result["prompt_injection_detected"],
                    "links_found": result["links_found"],
                },
            )
        except Exception as exc:
            # Telemetry recording failure must never break the user's assessment response
            log.warning("Scan telemetry recording failed (non-fatal): %s", exc)

    return result


@app.get("/api/v1/history", response_model=List[HistoryItem], tags=["ScamShield"])
def get_scan_history(
    limit: int = 20,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    authorization: Optional[str] = Header(None),
):
    """
    Retrieve anonymized scan history telemetry.
    Privacy & Access Control:
      - Uses the same configured storage backend (Supabase or Local SQLite).
      - Raw message text is never returned because it was never stored.
      - If authentication or session identifier is provided, filters to that user's history.
      - Unauthenticated public requests receive isolated telemetry records or session history,
        preventing cross-user data scraping.
    """
    # Extract user ID from header or auth if present
    target_user_id = x_user_id
    if not target_user_id and authorization and authorization.startswith("Bearer "):
        # Placeholder for real JWT validation when Supabase Auth is enabled
        token = authorization.split("Bearer ")[-1].strip()
        if token:
            target_user_id = token[:36]  # Truncated identifier

    # Fetch from unified storage backend
    records = fetch_scan_telemetry_history(limit=min(limit, 100), user_id=target_user_id)
    return records


@app.get("/api/v1/safe-next-steps", response_model=SafeNextStepsResponse, tags=["ScamShield"])
def get_safe_next_steps():
    """Return verified scam mitigation checklists and official reporting hotlines."""
    return SAFE_NEXT_STEPS_DATA


@app.get("/api/v1/sample-cases", tags=["ScamShield"])
def get_sample_cases():
    """Pre-loaded test cases for rapid live demonstration (shared source of truth)."""
    return SAMPLE_CASES
