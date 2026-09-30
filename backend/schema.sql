-- Run once against your Neon database (psql or the Neon SQL editor).
-- The app also creates this automatically on startup via init_schema().
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    metadata    JSONB NOT NULL,
    chunks      JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
