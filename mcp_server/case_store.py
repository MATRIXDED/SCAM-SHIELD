"""
mcp_server/case_store.py — Stateful scam-incident store
========================================================
Keeps scam "cases" alive across Alexa+ sessions so the assistant can follow an
incident from first suspicious message to family alert to official report.

Privacy: the raw message is NEVER stored. Only the HMAC fingerprint produced by
the analyzer, the risk score/level, and short warning-sign labels are kept.

Path is controlled by SCAMSHIELD_CASES_DB (default: <repo>/data/cases.db).
"""

import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_DB_OVERRIDE: Optional[str] = None


def set_db_path(path: Optional[str]) -> None:
    """Override the DB path (used by tests for isolation)."""
    global _DB_OVERRIDE
    _DB_OVERRIDE = str(path) if path else None


def get_db_path() -> Path:
    if _DB_OVERRIDE:
        return Path(_DB_OVERRIDE)
    env = os.environ.get("SCAMSHIELD_CASES_DB")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "data" / "cases.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _conn():
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        _init(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _init(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY,
            family_id TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            max_score INTEGER NOT NULL DEFAULT 0,
            max_level TEXT NOT NULL DEFAULT 'UNKNOWN',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'message',
            fingerprint TEXT,
            channel TEXT,
            risk_score INTEGER NOT NULL,
            risk_level TEXT NOT NULL,
            signals TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_evidence_fp ON evidence (fingerprint);
        CREATE TABLE IF NOT EXISTS coach (
            case_id TEXT PRIMARY KEY,
            answers TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            status TEXT NOT NULL,
            delivery TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )


def _level_rank(level: str) -> int:
    if level.startswith("HIGH"):
        return 3
    if level.startswith("ELEVATED"):
        return 2
    if level.startswith("LOW"):
        return 1
    return 0


# ── Cases ─────────────────────────────────────────────────────────────────────

def create_case(family_id: str, title: str) -> Dict[str, Any]:
    case_id = "case_" + secrets.token_hex(4)
    now = _now()
    with _conn() as c:
        c.execute(
            "INSERT INTO cases (id, family_id, title, created_at, updated_at) VALUES (?,?,?,?,?)",
            (case_id, family_id, title, now, now),
        )
    return get_case(case_id)  # type: ignore[return-value]


def get_case(case_id: str) -> Optional[Dict[str, Any]]:
    with _conn() as c:
        row = c.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        if not row:
            return None
        case = dict(row)
        ev = c.execute(
            "SELECT kind, fingerprint, channel, risk_score, risk_level, signals, created_at "
            "FROM evidence WHERE case_id = ? ORDER BY id",
            (case_id,),
        ).fetchall()
        case["evidence"] = [
            {**dict(e), "signals": json.loads(e["signals"])} for e in ev
        ]
        al = c.execute(
            "SELECT id, status, delivery, created_at FROM alerts WHERE case_id = ? ORDER BY id",
            (case_id,),
        ).fetchall()
        case["alerts"] = [dict(a) for a in al]
        return case


def add_evidence(
    case_id: str,
    kind: str,
    fingerprint: Optional[str],
    channel: Optional[str],
    risk_score: int,
    risk_level: str,
    signals: List[str],
) -> None:
    now = _now()
    with _conn() as c:
        c.execute(
            "INSERT INTO evidence (case_id, kind, fingerprint, channel, risk_score, risk_level, signals, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (case_id, kind, fingerprint, channel, risk_score, risk_level, json.dumps(signals[:8]), now),
        )
        row = c.execute("SELECT max_score, max_level FROM cases WHERE id = ?", (case_id,)).fetchone()
        new_score, new_level = row["max_score"], row["max_level"]
        if risk_score >= new_score:
            new_score, new_level = risk_score, risk_level
        elif _level_rank(risk_level) > _level_rank(new_level):
            new_level = risk_level
        c.execute(
            "UPDATE cases SET max_score = ?, max_level = ?, updated_at = ? WHERE id = ?",
            (new_score, new_level, now, case_id),
        )


def count_family_sightings(family_id: str, fingerprint: str, exclude_case: Optional[str] = None) -> int:
    """How many times this exact (normalized) message fingerprint was seen in this family."""
    with _conn() as c:
        q = (
            "SELECT COUNT(*) AS n FROM evidence e JOIN cases k ON k.id = e.case_id "
            "WHERE k.family_id = ? AND e.fingerprint = ?"
        )
        params: list = [family_id, fingerprint]
        if exclude_case:
            q += " AND e.case_id != ?"
            params.append(exclude_case)
        return int(c.execute(q, params).fetchone()["n"])


def set_status(case_id: str, status: str) -> None:
    with _conn() as c:
        c.execute("UPDATE cases SET status = ?, updated_at = ? WHERE id = ?", (status, _now(), case_id))


# ── Live-call coach answers ───────────────────────────────────────────────────

def get_coach_answers(case_id: str) -> Dict[str, bool]:
    with _conn() as c:
        row = c.execute("SELECT answers FROM coach WHERE case_id = ?", (case_id,)).fetchone()
        return json.loads(row["answers"]) if row else {}


def save_coach_answers(case_id: str, answers: Dict[str, bool]) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO coach (case_id, answers, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(case_id) DO UPDATE SET answers = excluded.answers, updated_at = excluded.updated_at",
            (case_id, json.dumps(answers), _now()),
        )


# ── Alerts (family outbox) ────────────────────────────────────────────────────

def add_alert(case_id: str, status: str, delivery: str, body: str) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO alerts (case_id, status, delivery, body, created_at) VALUES (?,?,?,?,?)",
            (case_id, status, delivery, body, _now()),
        )
        return int(cur.lastrowid)


def update_alert(alert_id: int, status: str, delivery: str) -> None:
    with _conn() as c:
        c.execute("UPDATE alerts SET status = ?, delivery = ? WHERE id = ?", (status, delivery, alert_id))


def get_pending_alert(case_id: str) -> Optional[Dict[str, Any]]:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM alerts WHERE case_id = ? AND status = 'pending_confirmation' ORDER BY id DESC LIMIT 1",
            (case_id,),
        ).fetchone()
        return dict(row) if row else None


def list_outbox(limit: int = 20) -> List[Dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, case_id, status, delivery, body, created_at FROM alerts ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
