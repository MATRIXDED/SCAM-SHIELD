"""
TeamPilot — AI Project Recovery Command Center
Backend entry point (Phase 0: health check only)

Run with:
    .venv\\Scripts\\uvicorn.exe main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, get_connection
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime, timezone
  

# ── App instance ────────────────────────────────────────────────────────────
# 'title' and 'version' appear in the auto-generated docs at /docs
app = FastAPI(
    title="TeamPilot API",
    version="0.1.0",
    description="AI Project Recovery Command Center — Alexa+ MCP Hackathon",
)

@app.on_event("startup")
def startup_event():
    init_db()
class ProjectCreate(BaseModel):
    name: str
    description: str | None = None

# ── CORS middleware ──────────────────────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing.
# Without this, the browser blocks requests from localhost:5173 (React)
# to localhost:8000 (FastAPI) because they're on different ports.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ───────────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health_check():
    """
    Simple liveness probe.
    Returns 200 OK when the server is running.
    The frontend and tests call this first to confirm the backend is up.
    """
    return {
        "status": "ok",
        "service": "TeamPilot",
        "version": "0.1.0",
        "phase": "Phase 0 — Setup verified",
    }

@app.post("/projects", tags=["Projects"], status_code=201)
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


@app.get("/projects", tags=["Projects"])
def list_projects():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM projects ORDER BY created_at DESC"
        ).fetchall()

    return [dict(row) for row in rows]
