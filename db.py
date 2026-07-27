import sqlite3
import json
import logging
from typing import Optional, List, Dict, Any
import config

from pathlib import Path

logger = logging.getLogger("cevondocs")


def get_connection(db_path: str = config.DATABASE_PATH) -> sqlite3.Connection:
    """Returns a SQLite connection with row factory enabled."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = config.DATABASE_PATH) -> None:
    """Creates the documents table if it does not already exist."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                status TEXT NOT NULL,
                extracted_json TEXT,
                reviewed_json TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.commit()
    logger.info(f"Database initialized at '{db_path}'")


def insert_document(
    doc_id: str,
    filename: str,
    status: str,
    extracted_json: Optional[str] = None,
    created_at: str = "",
    db_path: str = config.DATABASE_PATH,
) -> None:
    """Inserts a new document record into the database."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO documents (id, filename, status, extracted_json, reviewed_json, created_at)
            VALUES (?, ?, ?, ?, NULL, ?);
            """,
            (doc_id, filename, status, extracted_json, created_at),
        )
        conn.commit()
    logger.info(f"Inserted document '{doc_id}' with status '{status}' into DB.")


def get_document(doc_id: str, db_path: str = config.DATABASE_PATH) -> Optional[Dict[str, Any]]:
    """Retrieves a single document by ID as a dictionary."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_pending(db_path: str = config.DATABASE_PATH) -> List[Dict[str, Any]]:
    """Retrieves all documents with status='pending_review'."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM documents WHERE status = 'pending_review' ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def approve_document(
    doc_id: str, reviewed_json: str, db_path: str = config.DATABASE_PATH
) -> bool:
    """Updates status to 'approved' and sets reviewed_json."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE documents
            SET status = 'approved', reviewed_json = ?
            WHERE id = ?;
            """,
            (reviewed_json, doc_id),
        )
        conn.commit()
        return cursor.rowcount > 0
