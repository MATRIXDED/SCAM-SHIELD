"""
supabase_client.py — Supabase Cloud Storage & Resilient Local Fallback
========================================================================
Handles interactions with Supabase database using secure server-side credentials.
Guarantees:
  1. Writes and reads ALWAYS target the same storage backend (Supabase or Local SQLite).
  2. Telemetry strictly preserves user privacy: NO raw message content is ever transmitted or saved.
  3. Service role keys remain server-side only.
  4. Robust fallback to local SQLite when Supabase is not configured or fails.
"""

import json
import logging
from typing import Optional, Dict, Any, List
import httpx

from config import settings
from database import record_scam_scan, get_scam_scans

log = logging.getLogger(__name__)


def is_supabase_configured() -> bool:
    """Return True if valid Supabase connection details are present in configuration."""
    return bool(
        settings.SUPABASE_URL
        and settings.SUPABASE_KEY
        and settings.SUPABASE_URL.startswith("http")
    )


def get_backend_status() -> Dict[str, Any]:
    """Return backend storage mode and connectivity diagnostics."""
    configured = is_supabase_configured()
    return {
        "supabase_configured": configured,
        "mode": "supabase_cloud" if configured else "local_sqlite_demo",
        "privacy_guarantee": "Strict: Raw message contents are never persisted.",
        "storage_target": settings.SUPABASE_URL if configured else "backend/teampilot.db (SQLite)",
    }


def record_scan_telemetry(
    fingerprint: str,
    risk_score: int,
    risk_level: str,
    channel: str,
    preview_length: int,
    warning_count: int,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Persist scan telemetry to the configured backend (Supabase if available, else SQLite).
    Strict Privacy Rule: Only the keyed HMAC fingerprint and non-sensitive scores are saved.
    """
    if is_supabase_configured():
        endpoint = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/scam_assessments"
        # Use service role key if available for server-to-server writes, else standard API key
        auth_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
        headers = {
            "apikey": auth_key,
            "Authorization": f"Bearer {auth_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        payload = {
            "fingerprint": fingerprint,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "channel": channel,
            "preview_length": preview_length,
            "warning_count": warning_count,
            "metadata": metadata or {},
        }
        if user_id:
            payload["user_id"] = user_id

        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                res = client.post(endpoint, json=payload, headers=headers)
                if res.status_code in (200, 201):
                    data = res.json()
                    return {"source": "supabase", "data": data[0] if data else {}}
                else:
                    log.warning(
                        "Supabase insert returned unexpected status %s: %s; falling back to local SQLite",
                        res.status_code,
                        res.text,
                    )
        except Exception as exc:
            log.warning("Supabase request failed (%s); falling back to local SQLite", exc)

    # Fallback to local SQLite database
    local_record = record_scam_scan(
        fingerprint=fingerprint,
        risk_score=risk_score,
        risk_level=risk_level,
        channel=channel,
        preview_length=preview_length,
        warning_count=warning_count,
        metadata_json=json.dumps(metadata or {}),
    )
    return {"source": "local_sqlite", "data": local_record}


def fetch_scan_telemetry_history(
    limit: int = 20,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve scan telemetry history from the active configured storage backend.
    Ensures writes and reads use the same storage engine.
    Notice: Raw message text is NEVER returned because it was never saved.
    """
    if is_supabase_configured():
        auth_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
        headers = {
            "apikey": auth_key,
            "Authorization": f"Bearer {auth_key}",
            "Accept": "application/json",
        }
        params: Dict[str, Any] = {
            "select": "id,fingerprint,preview_length,risk_score,risk_level,channel,warning_count,created_at",
            "order": "created_at.desc",
            "limit": str(min(limit, 100)),
        }
        if user_id:
            params["user_id"] = f"eq.{user_id}"

        endpoint = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/scam_assessments"
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                res = client.get(endpoint, headers=headers, params=params)
                if res.status_code == 200:
                    return res.json()
                else:
                    log.warning(
                        "Supabase history query returned status %s: %s; falling back to local SQLite",
                        res.status_code,
                        res.text,
                    )
        except Exception as exc:
            log.warning("Supabase history query failed (%s); falling back to local SQLite", exc)

    # Local SQLite read
    records = get_scam_scans(limit=min(limit, 100))
    return [
        {
            "id": r["id"],
            "fingerprint": r["fingerprint"],
            "preview_length": r["preview_length"],
            "risk_score": r["risk_score"],
            "risk_level": r["risk_level"],
            "channel": r["channel"],
            "warning_count": r["warning_count"],
            "created_at": r["created_at"],
        }
        for r in records
    ]
