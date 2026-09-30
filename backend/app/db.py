"""Postgres storage (Neon). Documents + their parsed chunks live as JSONB.

Connection comes from DATABASE_URL (Neon/Vercel injects this). psycopg v3.
"""
import os
import psycopg

DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    metadata    JSONB NOT NULL,
    chunks      JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL is not set. Add your Neon connection string to the environment.')
    # autocommit keeps the call sites simple; each op is a single statement.
    return psycopg.connect(DATABASE_URL, autocommit=True)


def init_schema():
    with get_conn() as conn:
        conn.execute(SCHEMA)
