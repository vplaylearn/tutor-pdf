import os, shutil, tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from app.db import init_schema
from app.documents import delete_document, get_document, list_documents
from app.models import AskRequest, AskResponse, DocumentResponse, Source
from app.rag import build_answer, search
from services.ingest import ingest_pdf


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Idempotent (CREATE TABLE IF NOT EXISTS). Don't crash the function on a
    # transient DB hiccup at cold start -- the first real request will surface it.
    try:
        init_schema()
    except Exception:
        pass
    yield


app = FastAPI(title='Local PDF Tutor', lifespan=lifespan)

# Comma-separated allowed origins; defaults to local Vite dev server.
_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5173')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(',') if o.strip()],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/api/documents', response_model=list[DocumentResponse])
def docs():
    return list_documents()


@app.post('/api/documents/upload', response_model=DocumentResponse)
async def upload(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, 'Only PDF files are supported.')
    # Write to the system temp dir (writable on Vercel within one invocation),
    # ingest, then remove. Nothing persists to disk.
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tf:
        shutil.copyfileobj(file.file, tf)
        p = Path(tf.name)
    try:
        # Preserve the uploaded filename for metadata/title.
        return ingest_pdf(p, original_name=file.filename)
    except Exception as e:
        raise HTTPException(500, f'PDF ingestion failed: {e}') from e
    finally:
        p.unlink(missing_ok=True)


@app.delete('/api/documents/{document_id}')
def remove(document_id: str):
    if not delete_document(document_id):
        raise HTTPException(404, 'Document not found.')
    return {'status': 'deleted', 'document_id': document_id}


@app.post('/api/doubt', response_model=AskResponse)
def doubt(req: AskRequest):
    if not get_document(req.document_id):
        raise HTTPException(404, 'Document not found.')
    rs = search(req.document_id, req.question)
    return {'answer': build_answer(rs, req.question), 'sources': [Source(**r) for r in rs]}


# Serve the built frontend same-origin (declared last so /api routes win).
# `public/` is populated by the Vercel build (vite build -> backend/public).
# Absent in local backend-only dev, which is fine -- the Vite dev server serves it then.
_public = Path(__file__).resolve().parents[1] / 'public'
if _public.is_dir():
    from fastapi.staticfiles import StaticFiles
    app.mount('/', StaticFiles(directory=str(_public), html=True), name='frontend')
