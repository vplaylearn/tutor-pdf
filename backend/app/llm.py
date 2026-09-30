"""Chat-LLM client for RAG answer generation.

Talks to the OpenAI-compatible gateway at CHAT_API_URL (default: the
ai-cloud-server chat endpoint). No API key required by that gateway; if a
future endpoint needs one, set CHAT_API_KEY and it is sent as a Bearer token.

Stdlib-only HTTP so the Vercel function bundle stays tiny (no openai/torch).
"""
import os
import json
import urllib.request
import urllib.error

CHAT_API_URL = os.getenv('CHAT_API_URL', 'https://ai-cloud-server-delta.vercel.app/api/chat')
CHAT_MODEL = os.getenv('CHAT_MODEL', 'auto')
CHAT_API_KEY = os.getenv('CHAT_API_KEY', '')
TIMEOUT = float(os.getenv('CHAT_TIMEOUT', '60'))

SYSTEM_PROMPT = (
    "You are a helpful PDF tutor. Answer the question using ONLY the provided "
    "context from the document. Be clear and concise. If the answer is not "
    "contained in the context, reply exactly: I could not find an answer in the selected PDF."
)


def chat(context: str, question: str) -> str:
    """Generate a grounded answer from retrieved PDF context. Raises on transport
    failure so the caller can fall back to the raw retrieved text."""
    payload = {
        'model': CHAT_MODEL,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': f'Context:\n{context}\n\nQuestion: {question}'},
        ],
    }
    headers = {'Content-Type': 'application/json', 'User-Agent': 'local-pdf-tutor'}
    if CHAT_API_KEY:
        headers['Authorization'] = f'Bearer {CHAT_API_KEY}'
    req = urllib.request.Request(
        CHAT_API_URL, data=json.dumps(payload).encode('utf-8'), headers=headers
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = json.loads(r.read())
    return data['choices'][0]['message']['content'].strip()
