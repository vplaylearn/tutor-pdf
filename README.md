# PDF Tutor

A multi-PDF tutor: upload PDFs, ask questions, get answers grounded in the
document. React/TypeScript frontend, FastAPI backend, PyMuPDF text extraction,
Neon Postgres storage, and answer generation via a chat-LLM gateway.

Deployable to Vercel as a single project (frontend + API same-origin). See
[DEPLOY.md](DEPLOY.md).

## How it works

- **Ingestion**: PyMuPDF extracts text and parses Question/Answer pairs (falling
  back to per-page chunks). Chunks + metadata are stored in Postgres as JSONB.
- **Retrieval**: exact question match → "Question N" lookup → lexical overlap →
  top-N fallback. No embeddings.
- **Answering**: the retrieved context is sent to the chat gateway
  (`CHAT_API_URL`), which generates a grounded answer. If the gateway is
  unreachable, the stored answer text is returned as a fallback.
- Speech-to-text and text-to-speech run in the browser.

## Local development

Backend (needs a Postgres `DATABASE_URL`, e.g. Neon):
```
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt
DATABASE_URL=postgres://... .venv/bin/uvicorn app.main:app --reload
```

Frontend:
```
cd frontend
npm install
npm run dev
```
Open http://localhost:5173

## Configuration

Copy `backend/.env.example` to `backend/.env` and fill in `DATABASE_URL`. See
[DEPLOY.md](DEPLOY.md) for all variables and Vercel setup.
