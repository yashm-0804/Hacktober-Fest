"""Shared SQLite store for cases, doctor escalations and chat messages.

The API's patient and doctor endpoints read and write the same file from worker
threads, so every call opens a fresh connection (check_same_thread=False) and closes it.
DB path: env APP_DB, default `app.db` in the repo root.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = ROOT / "cache" / "uploads"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    context TEXT,
    allergies TEXT,
    image_path TEXT,
    payload_json TEXT
);
CREATE TABLE IF NOT EXISTS escalations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER,
    med_index INTEGER,
    raw_text TEXT,
    candidates_json TEXT,
    context TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    resolution_json TEXT,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    escalation_id INTEGER NOT NULL,
    sender TEXT NOT NULL,
    text TEXT NOT NULL,
    ts REAL NOT NULL
);
"""


def db_path() -> str:
    return os.environ.get("APP_DB") or str(ROOT / "app.db")


@contextmanager
def _conn():
    con = sqlite3.connect(db_path(), check_same_thread=False, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(_SCHEMA)
        yield con
        con.commit()
    finally:
        con.close()


def _loads(s, default=None):
    if not s:
        return default
    try:
        return json.loads(s)
    except (TypeError, ValueError):
        return default


# ---------- uploads ----------

def save_upload(data: bytes) -> str:
    """Save image bytes to cache/uploads/<sha256>.jpg and return the path."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{hashlib.sha256(data).hexdigest()}.jpg"
    if not path.exists():
        path.write_bytes(data)
    return str(path)


# ---------- cases ----------

def save_case(context: str, allergies, image_path: str | None, payload: dict) -> int:
    if isinstance(allergies, (list, tuple)):
        allergies = ", ".join(allergies)
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO cases(created_at, context, allergies, image_path, payload_json) VALUES (?,?,?,?,?)",
            (time.time(), context, allergies, image_path, json.dumps(payload, default=str)),
        )
        return int(cur.lastrowid)


def update_case(case_id: int, payload: dict) -> None:
    with _conn() as con:
        con.execute("UPDATE cases SET payload_json=? WHERE id=?", (json.dumps(payload, default=str), case_id))


def get_case(case_id: int) -> dict | None:
    with _conn() as con:
        row = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["payload"] = _loads(d.pop("payload_json"), {})
    return d


# ---------- escalations ----------

def open_escalation(case_id: int | None, med_index: int, raw_text: str, candidates: list, context: str) -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO escalations(case_id, med_index, raw_text, candidates_json, context, status, created_at)"
            " VALUES (?,?,?,?,?,'open',?)",
            (case_id, med_index, raw_text, json.dumps(candidates, default=str), context, time.time()),
        )
        return int(cur.lastrowid)


def _esc(row) -> dict:
    d = dict(row)
    d["candidates"] = _loads(d.pop("candidates_json"), [])
    d["resolution"] = _loads(d.pop("resolution_json"), None)
    return d


def get_escalation(eid: int) -> dict | None:
    with _conn() as con:
        row = con.execute("SELECT * FROM escalations WHERE id=?", (eid,)).fetchone()
    return _esc(row) if row else None


def list_open() -> list[dict]:
    return list_escalations("open")


_ESC_SUMMARY = """SELECT e.*,
    (SELECT COUNT(*) FROM messages m WHERE m.escalation_id = e.id) AS message_count,
    (SELECT MAX(m.ts) FROM messages m WHERE m.escalation_id = e.id) AS last_message_at
    FROM escalations e"""


def list_escalations(status: str | None = "open") -> list[dict]:
    """status "open" / "resolved", or None for all. Oldest first, each with message_count and last_message_at."""
    with _conn() as con:
        if status:
            rows = con.execute(f"{_ESC_SUMMARY} WHERE e.status=? ORDER BY e.created_at, e.id", (status,)).fetchall()
        else:
            rows = con.execute(f"{_ESC_SUMMARY} ORDER BY e.created_at, e.id").fetchall()
    return [_esc(r) for r in rows]


def list_for_case(case_id: int) -> list[dict]:
    with _conn() as con:
        rows = con.execute(f"{_ESC_SUMMARY} WHERE e.case_id=? ORDER BY e.created_at, e.id", (case_id,)).fetchall()
    return [_esc(r) for r in rows]


def resolve(eid: int, resolution: dict) -> None:
    with _conn() as con:
        con.execute("UPDATE escalations SET status='resolved', resolution_json=? WHERE id=?",
                    (json.dumps(resolution, default=str), eid))


# ---------- messages ----------

def add_message(eid: int, sender: str, text: str) -> int:
    if sender not in ("patient", "doctor", "system"):
        raise ValueError(f"bad sender {sender!r}")
    with _conn() as con:
        cur = con.execute("INSERT INTO messages(escalation_id, sender, text, ts) VALUES (?,?,?,?)",
                          (eid, sender, text, time.time()))
        return int(cur.lastrowid)


def messages(eid: int) -> list[dict]:
    with _conn() as con:
        rows = con.execute("SELECT * FROM messages WHERE escalation_id=? ORDER BY id", (eid,)).fetchall()
    return [dict(r) for r in rows]
