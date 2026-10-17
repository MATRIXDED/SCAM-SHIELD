"""
database.py — TeamPilot persistence layer
==========================================
Responsibilities:
  - Define the path to the SQLite database file.
  - Open connections with foreign-key enforcement and sensible defaults.
  - Create all four tables (idempotent: safe to call on every startup).
  - Detect dependency cycles before they are inserted.
  - Expose init_db() for the FastAPI startup hook.

This module has ZERO imports outside Python's standard library.
All seed data lives in seed.py, not here.
"""

import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

# Path(__file__) is the absolute path to this file (database.py).
# .parent gives us the directory it lives in (backend/).
# We store the database next to the source files so it's easy to find
# and easy to delete when resetting during development.
DB_PATH = Path(__file__).parent / "teampilot.db"

log = logging.getLogger(__name__)


# ── Connection management ─────────────────────────────────────────────────────

@contextmanager
def get_connection():
    """
    Open a SQLite connection, configure it correctly, and guarantee cleanup.

    Usage:
        with get_connection() as conn:
            conn.execute("SELECT ...")

    Why a context manager?
        If an exception occurs inside the `with` block, Python still runs
        the cleanup code (conn.close()). Without this, a crashed request
        could leak an open file handle.

    Settings applied to every connection:
        - PRAGMA foreign_keys = ON
            SQLite ignores foreign-key constraints by default. This line
            activates them. It must be set on every new connection because
            SQLite resets it each time.
        - isolation_level = None  (autocommit OFF — we manage transactions)
            We use explicit BEGIN/COMMIT/ROLLBACK so we control exactly
            when data is written to disk.
        - row_factory = sqlite3.Row
            Rows behave like dicts: row["title"] instead of row[2].
            This makes the code readable and avoids index fragility.
        - detect_types = PARSE_DECLTYPES
            Allows sqlite3 to convert TEXT columns declared as TIMESTAMP
            back to Python datetime objects if we ever use them.
    """
    conn = sqlite3.connect(
        DB_PATH,
        detect_types=sqlite3.PARSE_DECLTYPES,
    )
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None  # we control transactions manually

    try:
        # This is the single most important line in this file.
        # Without it, INSERT with a bad foreign key silently succeeds.
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
    finally:
        # Always runs — even if the caller raises an exception.
        conn.close()


# ── Schema definition ─────────────────────────────────────────────────────────

# We keep the DDL (Data Definition Language) as a single list of SQL strings.
# This is intentional: it is readable, diffable, and simple to extend.
# For a hackathon-scale project, a full migration framework (like Alembic)
# would add more complexity than value.

_SCHEMA_STATEMENTS = [

    # ── projects ──────────────────────────────────────────────────────────────
    # A project is the top-level container for a set of related tasks.
    # status: 'active' means the project is ongoing; 'archived' means done.
    """
    CREATE TABLE IF NOT EXISTS projects (
        id          TEXT    PRIMARY KEY,
        name        TEXT    NOT NULL,
        description TEXT,
        status      TEXT    NOT NULL DEFAULT 'active',
        created_at  TEXT    NOT NULL,
        updated_at  TEXT    NOT NULL,
        CHECK (status IN ('active', 'archived'))
    )
    """,

    # ── tasks ─────────────────────────────────────────────────────────────────
    # Core unit of work within a project.
    #
    # status values:
    #   ready        — can be started immediately, no open blockers
    #   in_progress  — currently being worked on
    #   blocked      — cannot proceed until a prerequisite is resolved
    #   completed    — done and verified
    #   cancelled    — will not be done
    #
    # priority values:
    #   low | medium | high | critical
    #
    # effort_days: the team's estimate in working days (integer, nullable).
    # owner: person or team handle responsible for this task.
    #
    # Why REFERENCES projects(id)?
    #   This is a foreign key. SQLite will reject any task whose project_id
    #   does not match an existing project row. With FK enforcement on, this
    #   is a hard guarantee at the database level.
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id          TEXT    PRIMARY KEY,
        project_id  TEXT    NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        title       TEXT    NOT NULL,
        description TEXT,
        status      TEXT    NOT NULL DEFAULT 'ready',
        priority    TEXT    NOT NULL DEFAULT 'medium',
        owner       TEXT,
        effort_days INTEGER,
        created_at  TEXT    NOT NULL,
        updated_at  TEXT    NOT NULL,
        CHECK (status   IN ('ready', 'in_progress', 'blocked', 'completed', 'cancelled')),
        CHECK (priority IN ('low', 'medium', 'high', 'critical')),
        CHECK (effort_days IS NULL OR effort_days > 0)
    )
    """,

    # ── task_dependencies ─────────────────────────────────────────────────────
    # Encodes "prerequisite_id must complete before dependent_id can start".
    #
    # Reading the relationship:
    #   prerequisite_id → dependent_id
    #   "Auth Service"  → "Login Screen"
    #   means: Login Screen is BLOCKED BY Auth Service.
    #
    # Constraints:
    #   UNIQUE (prerequisite_id, dependent_id) — prevents duplicate edges.
    #   CHECK (prerequisite_id != dependent_id) — prevents self-loops at DB level.
    #   Cycle detection (A→B→C→A) is done in Python before INSERT.
    #
    # ON DELETE CASCADE: if a task is deleted, its dependency edges are
    # automatically removed. This keeps the graph consistent.
    """
    CREATE TABLE IF NOT EXISTS task_dependencies (
        id              TEXT    PRIMARY KEY,
        prerequisite_id TEXT    NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
        dependent_id    TEXT    NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
        created_at      TEXT    NOT NULL,
        UNIQUE (prerequisite_id, dependent_id),
        CHECK  (prerequisite_id != dependent_id)
    )
    """,

    # ── action_history ────────────────────────────────────────────────────────
    # Append-only audit log. Rows are NEVER updated or deleted.
    # Each row captures one moment in the lifecycle of an action.
    #
    # action_type: what kind of event this is.
    #   propose  — agent suggested a change
    #   approve  — user approved the suggestion
    #   reject   — user rejected the suggestion
    #   execute  — system attempted to apply the change
    #   verify   — system confirmed the change is persisted (read-after-write)
    #   fail     — execution or verification failed
    #
    # state: where this action stands in the workflow.
    #   PROPOSED | APPROVED | REJECTED | EXECUTING | EXECUTED | VERIFIED | FAILED
    #
    # payload: JSON string — what was INTENDED (the plan).
    # outcome: JSON string — what ACTUALLY HAPPENED (may differ from payload).
    # actor: who triggered this entry — 'user', 'agent', or 'system'.
    #
    # Note: entity_type + entity_id form a loose foreign key (not enforced by
    # SQLite) because history entries may refer to entities that were later
    # archived or deleted — and we want to keep the history.
    """
    CREATE TABLE IF NOT EXISTS action_history (
        id          TEXT    PRIMARY KEY,
        action_type TEXT    NOT NULL,
        entity_type TEXT,
        entity_id   TEXT,
        state       TEXT    NOT NULL,
        payload     TEXT,
        outcome     TEXT,
        actor       TEXT    NOT NULL DEFAULT 'system',
        created_at  TEXT    NOT NULL,
        CHECK (action_type IN ('propose', 'approve', 'reject', 'execute', 'verify', 'fail')),
        CHECK (state IN ('PROPOSED', 'APPROVED', 'REJECTED', 'EXECUTING',
                         'EXECUTED', 'VERIFIED', 'FAILED')),
        CHECK (actor IN ('user', 'agent', 'system'))
    )
    """,

    # ── scam_scans (ScamShield Telemetry & History) ───────────────────────────
    # Privacy-conscious scan records.
    # CRITICAL: We NEVER store the raw message text.
    # Only the SHA-256 fingerprint, risk scoring, category indicators, and preview size.
    """
    CREATE TABLE IF NOT EXISTS scam_scans (
        id             TEXT    PRIMARY KEY,
        fingerprint    TEXT    NOT NULL,
        risk_score     INTEGER NOT NULL,
        risk_level     TEXT    NOT NULL,
        channel        TEXT    NOT NULL DEFAULT 'sms',
        preview_length INTEGER NOT NULL,
        warning_count  INTEGER NOT NULL DEFAULT 0,
        metadata_json  TEXT,
        created_at     TEXT    NOT NULL
    )
    """,

    # ── Indexes ───────────────────────────────────────────────────────────────
    # Indexes are separate CREATE statements because CREATE TABLE IF NOT EXISTS
    # does not update indexes if the table already exists.
    # Each index targets a specific query pattern we know we'll run:

    # "Give me all tasks for project X" — used by the dashboard task list.
    "CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id)",

    # "What blocks this task?" / "What does this task block?"
    # — used by the dependency graph and blocker detection.
    "CREATE INDEX IF NOT EXISTS idx_deps_prerequisite ON task_dependencies(prerequisite_id)",
    "CREATE INDEX IF NOT EXISTS idx_deps_dependent    ON task_dependencies(dependent_id)",

    # "Show me recent history for task X" — used by the activity timeline.
    "CREATE INDEX IF NOT EXISTS idx_history_entity  ON action_history(entity_id, entity_type)",
    "CREATE INDEX IF NOT EXISTS idx_history_created ON action_history(created_at)",

    # ScamShield lookup indexes
    "CREATE INDEX IF NOT EXISTS idx_scam_scans_fingerprint ON scam_scans(fingerprint)",
    "CREATE INDEX IF NOT EXISTS idx_scam_scans_created     ON scam_scans(created_at)",
]


# ── Cycle detection ───────────────────────────────────────────────────────────

def would_create_cycle(conn: sqlite3.Connection, prerequisite_id: str, dependent_id: str) -> bool:
    """
    Return True if adding the edge (prerequisite_id → dependent_id) would
    create a cycle in the dependency graph.

    Algorithm: Depth-first reachability from dependent_id.
    If we can reach prerequisite_id by following existing edges forward
    from dependent_id, then adding the new edge closes a cycle.

    Example:
        Existing: A → B → C
        Proposed: C → A  (would make A → B → C → A — a cycle)
        We start from A (the proposed dependent_id) and ask:
        "Can we reach C (the proposed prerequisite_id) by following edges?"
        Yes: A → B → C. So we return True.

    This runs entirely in Python with a single SQL query per step.
    For a project with dozens of tasks, performance is not a concern.
    """
    # We want to know: can we reach `prerequisite_id` starting from `dependent_id`?
    # If yes, adding prerequisite_id → dependent_id creates a cycle.
    visited: set[str] = set()
    frontier: list[str] = [dependent_id]

    while frontier:
        current = frontier.pop()
        if current == prerequisite_id:
            return True  # cycle confirmed
        if current in visited:
            continue
        visited.add(current)

        # Find all tasks that `current` is a prerequisite for (i.e., its dependents)
        rows = conn.execute(
            "SELECT dependent_id FROM task_dependencies WHERE prerequisite_id = ?",
            (current,),
        ).fetchall()
        frontier.extend(row["dependent_id"] for row in rows)

    return False


# ── Public API ────────────────────────────────────────────────────────────────

def init_db() -> None:
    """
    Create all tables and indexes if they do not already exist.

    This function is idempotent: calling it ten times has the same effect
    as calling it once. It will NEVER drop tables, erase data, or fail
    if the database already contains rows.

    Called once at FastAPI startup (see main.py lifespan hook).
    Also called directly by tests and seed.py.
    """
    log.info("Initializing database at %s", DB_PATH)

    with get_connection() as conn:
        # BEGIN a transaction so all DDL succeeds or all rolls back together.
        # If any statement fails (e.g., disk full), none of the tables exist
        # in a half-created state.
        conn.execute("BEGIN")
        try:
            for statement in _SCHEMA_STATEMENTS:
                conn.execute(statement)
            conn.execute("COMMIT")
            log.info("Database schema ready.")
        except Exception:
            conn.execute("ROLLBACK")
            log.exception("Schema initialization failed — rolled back.")
            raise


def get_db_path() -> Path:
    """Return the absolute path to the database file. Used by tests."""
    return DB_PATH


def record_scam_scan(
    fingerprint: str,
    risk_score: int,
    risk_level: str,
    channel: str,
    preview_length: int,
    warning_count: int,
    metadata_json: str | None = None,
) -> dict:
    """
    Store an anonymized scan result in the database.
    Privacy rule: RAW MESSAGE CONTENT IS NEVER SAVED.
    """
    from uuid import uuid4
    from datetime import datetime, timezone

    scan_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute("BEGIN")
        try:
            conn.execute(
                """
                INSERT INTO scam_scans
                    (id, fingerprint, risk_score, risk_level, channel, preview_length, warning_count, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (scan_id, fingerprint, risk_score, risk_level, channel, preview_length, warning_count, metadata_json, now),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

        row = conn.execute("SELECT * FROM scam_scans WHERE id = ?", (scan_id,)).fetchone()
        return dict(row) if row else {}


def get_scam_scans(limit: int = 50) -> list[dict]:
    """Retrieve recent anonymized scan activity."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, fingerprint, risk_score, risk_level, channel, preview_length, warning_count, created_at
            FROM scam_scans
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

