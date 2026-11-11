"""Conversation storage in SQLite. Every query is scoped to the signed-in user id and parameterized,
so one account can never read or delete another account's conversations."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from config import DB_PATH


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _conn():
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with _conn() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK (role IN ('user','assistant')),
            content TEXT NOT NULL,
            sources_json TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS preferences (
            user_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            PRIMARY KEY (user_id, key)
        );
        CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id, updated_at DESC);
        """)


def create_conversation(user_id, title="New chat"):
    with _conn() as con:
        cur = con.execute("INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (?,?,?,?)",
                          (user_id, title[:80], _now(), _now()))
        return cur.lastrowid


def _owned(con, user_id, conversation_id):
    return con.execute("SELECT id FROM conversations WHERE id=? AND user_id=?",
                       (conversation_id, user_id)).fetchone() is not None


def list_conversations(user_id):
    with _conn() as con:
        rows = con.execute("""SELECT c.id, c.title, c.created_at, c.updated_at,
                                     (SELECT COUNT(*) FROM messages m WHERE m.conversation_id=c.id) AS n_messages
                              FROM conversations c WHERE c.user_id=? ORDER BY c.updated_at DESC, c.id DESC""",
                           (user_id,)).fetchall()
        return [dict(r) for r in rows]


def get_messages(user_id, conversation_id):
    with _conn() as con:
        if not _owned(con, user_id, conversation_id):
            return []
        rows = con.execute("SELECT role, content, sources_json, created_at FROM messages "
                           "WHERE conversation_id=? ORDER BY id", (conversation_id,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["sources"] = json.loads(d.pop("sources_json")) if d.get("sources_json") else []
            out.append(d)
        return out


def add_message(user_id, conversation_id, role, content, sources=None):
    with _conn() as con:
        if not _owned(con, user_id, conversation_id):
            raise PermissionError("Conversation does not belong to this user.")
        con.execute("INSERT INTO messages (conversation_id, role, content, sources_json, created_at) VALUES (?,?,?,?,?)",
                    (conversation_id, role, content, json.dumps(sources) if sources else None, _now()))
        con.execute("UPDATE conversations SET updated_at=? WHERE id=?", (_now(), conversation_id))


def rename_conversation(user_id, conversation_id, title):
    with _conn() as con:
        con.execute("UPDATE conversations SET title=? WHERE id=? AND user_id=?", (title[:80], conversation_id, user_id))


def clear_conversation(user_id, conversation_id):
    with _conn() as con:
        if _owned(con, user_id, conversation_id):
            con.execute("DELETE FROM messages WHERE conversation_id=?", (conversation_id,))


def delete_conversation(user_id, conversation_id):
    with _conn() as con:
        con.execute("DELETE FROM conversations WHERE id=? AND user_id=?", (conversation_id, user_id))


def get_preference(user_id, key, default=None):
    with _conn() as con:
        row = con.execute("SELECT value FROM preferences WHERE user_id=? AND key=?", (user_id, key)).fetchone()
        return row["value"] if row else default


def set_preference(user_id, key, value):
    with _conn() as con:
        con.execute("INSERT INTO preferences (user_id, key, value) VALUES (?,?,?) "
                    "ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value", (user_id, key, str(value)))
