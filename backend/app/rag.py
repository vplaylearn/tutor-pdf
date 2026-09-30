import re
from app.documents import get_chunks
from app.llm import chat

STOP = {'the','is','a','an','of','to','in','on','for','and','or','what','why','how','does','do','are','was','were','with','from'}
NOT_FOUND = 'I could not find an answer in the selected PDF.'


def norm(s): return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9\s]', ' ', s.lower())).strip()
def toks(s): return {x for x in norm(s).split() if x not in STOP}


def records(i):
    return get_chunks(i)


def search(i, q):
    """Retrieve the most relevant chunk(s) using pure text matching.
    exact -> question_number -> lexical overlap -> top-N fallback (no embeddings)."""
    rs = records(i)
    if not rs:
        return []
    # exact question match
    for r in rs:
        if r.get('question') and norm(r['question']) == norm(q):
            r.update(score=1.0, match_type='exact'); return [r]
    # "Question N" / "Q N"
    m = re.search(r'\b(?:question|q)\s*(\d+)\b', q, re.I)
    if m:
        r = next((x for x in rs if x.get('question_number') == int(m.group(1))), None)
        if r:
            r.update(score=1.0, match_type='question_number'); return [r]
    # lexical overlap
    qt = toks(q); best = None; bs = 0
    for r in rs:
        rt = toks(r.get('question', '') + ' ' + r.get('answer', ''))
        s = len(qt & rt) / len(qt) if qt else 0
        if s > bs:
            best, bs = r, s
    if best is not None and bs >= .55:
        best.update(score=bs, match_type='lexical'); return [best]
    # no confident text match: return the top few by weak lexical overlap as
    # LLM context. ponytail: naive top-3 by overlap, no ranking model. Good
    # enough since the LLM does the reasoning; upgrade path = re-add embeddings.
    scored = sorted(rs, key=lambda r: len(qt & toks(r.get('question','')+' '+r.get('answer',''))), reverse=True)
    out = []
    for r in scored[:3]:
        r.update(score=bs, match_type='llm_context'); out.append(r)
    return out


def build_answer(rs, question=''):
    """Generate a grounded answer from retrieved chunks via the LLM, falling back
    to the raw retrieved text if the gateway is unreachable."""
    if not rs:
        return NOT_FOUND
    context = '\n\n'.join(r.get('answer', r.get('text', '')) for r in rs if r.get('answer') or r.get('text'))
    # Prefer the user's real question; for an exact hit the chunk's question is
    # equivalent, but the user's phrasing is what we should answer.
    ask = question or rs[0].get('question') or context[:200]
    try:
        return chat(context, ask)
    except Exception:
        # transport failure -> degrade gracefully to the stored answer
        return rs[0].get('answer', rs[0].get('text', '')) or NOT_FOUND
