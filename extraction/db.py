"""
Persistance des conversations — SQLite (fichier local, zéro config).
Suffisant pour un PoC (le cahier des charges exclut explicitement la
mise en production à grande échelle) ; suffirait à remplacer par
PostgreSQL/DynamoDB si le projet passait en production.
"""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("./conversations.db")


@contextmanager
def get_connexion():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_connexion() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                titre TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                contenu TEXT NOT NULL,
                sources TEXT,
                fiable INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)


def creer_conversation(titre: str, conversation_id: str | None = None) -> dict:
    conv_id = conversation_id or str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    with get_connexion() as conn:
        conn.execute(
            "INSERT INTO conversations (id, titre, created_at) VALUES (?, ?, ?)",
            (conv_id, titre, created_at),
        )
    return {"id": conv_id, "titre": titre, "created_at": created_at}


def lister_conversations() -> list[dict]:
    with get_connexion() as conn:
        lignes = conn.execute(
            "SELECT id, titre, created_at FROM conversations ORDER BY created_at DESC"
        ).fetchall()
    return [dict(l) for l in lignes]


def obtenir_conversation(conversation_id: str) -> dict | None:
    with get_connexion() as conn:
        conv = conn.execute(
            "SELECT id, titre, created_at FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        if not conv:
            return None
        messages = conn.execute(
            "SELECT role, contenu, sources, fiable, created_at FROM messages "
            "WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,),
        ).fetchall()

    return {
        **dict(conv),
        "messages": [
            {
                "role": m["role"],
                "contenu": m["contenu"],
                "sources": json.loads(m["sources"]) if m["sources"] else [],
                "fiable": bool(m["fiable"]) if m["fiable"] is not None else None,
                "created_at": m["created_at"],
            }
            for m in messages
        ],
    }


def ajouter_message(conversation_id: str, role: str, contenu: str,
                     sources: list | None = None, fiable: bool | None = None):
    with get_connexion() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, contenu, sources, fiable, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                conversation_id,
                role,
                contenu,
                json.dumps(sources, ensure_ascii=False) if sources is not None else None,
                int(fiable) if fiable is not None else None,
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def supprimer_conversation(conversation_id: str):
    with get_connexion() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
