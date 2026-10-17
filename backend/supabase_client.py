"""
supabase_client.py — Supabase Integration & Local Fallback
============================================================
Handles interactions with Supabase database with secure server-side credentials.
If Supabase environment variables are not configured, seamlessly operates
in Local Demo Mode backed by SQLite / memory, ensuring full functionality.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
import httpx

log = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

def is_supabase_configured() -> bool:
    """Return True if valid Supabase connection details are present."""
    return bool(SUPABASE_URL and SUPABASE_KEY and SUPABASE_URL.startswith("http"))


def get_backend_status() -> Dict[str, Any]:
    """Return backend storage mode and connectivity details."""
    configured = is_supabase_configured()
    return {
        "supabase_configured": configured,
        "mode": "supabase_cloud" if configured else "local_sqlite_demo",
        "privacy_guarantee": "Strict: Raw message contents are never persisted.",
        "storage_target": SUPABASE_URL if configured else "backend/teampilot.db (SQLite)",
    }


def record_scan_telemetry(
    fingerprint: str,
    risk_score: int,
    risk_level: str,
    channel: str,
    preview_length: int,
    warning_count: int,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Persist scan telemetry to Supabase if configured; otherwise local database.
    Privacy rule: Only anonymized hash and summary indicators are saved.
    """
    if is_supabase_configured():
        endpoint = f"{SUPABASE_URL.rstrip('/')}/rest/v1/scam_assessments"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
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
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.post(endpoint, json=payload, headers=headers)
                if res.status_code in (200, 201):
                    data = res.json()
                    return {"source": "supabase", "data": data[0] if data else {}}
                else:
                    log.warning("Supabase insert returned status %s: %s", res.status_code, res.text)
        except Exception as exc:
            log.warning("Supabase request failed, falling back to local SQLite: %s", exc)

    # Fallback to local SQLite database
    from database import record_scam_scan
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
