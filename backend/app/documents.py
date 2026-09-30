"""Document storage backed by Postgres (see app/db.py)."""
from psycopg.types.json import Jsonb
from app.db import get_conn


def list_documents():
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT metadata FROM documents ORDER BY created_at'
        ).fetchall()
    return [r[0] for r in rows]


def get_document(i):
    with get_conn() as conn:
        row = conn.execute(
            'SELECT metadata FROM documents WHERE document_id = %s', (i,)
        ).fetchone()
    return row[0] if row else None


def get_chunks(i):
    with get_conn() as conn:
        row = conn.execute(
            'SELECT chunks FROM documents WHERE document_id = %s', (i,)
        ).fetchone()
    return row[0] if row else []


def save_document(document_id, metadata, chunks):
    with get_conn() as conn:
        conn.execute(
            'INSERT INTO documents (document_id, metadata, chunks) VALUES (%s, %s, %s)',
            (document_id, Jsonb(metadata), Jsonb(chunks)),
        )


def document_id_exists(i):
    with get_conn() as conn:
        row = conn.execute(
            'SELECT 1 FROM documents WHERE document_id = %s', (i,)
        ).fetchone()
    return row is not None


def delete_document(i):
    with get_conn() as conn:
        cur = conn.execute('DELETE FROM documents WHERE document_id = %s', (i,))
    return cur.rowcount > 0
