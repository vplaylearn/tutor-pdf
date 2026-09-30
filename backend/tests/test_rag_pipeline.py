"""Self-check: RAG-by-LLM pipeline.

Verifies that (1) text retrieval picks the correct chunk without embeddings, and
(2) the chat gateway produces a grounded answer from that chunk.

Run from backend/ with a Postgres URL set:
    DATABASE_URL=postgres://... python tests/test_rag_pipeline.py

Hits the live chat gateway (CHAT_API_URL) and the Postgres in DATABASE_URL.
No API key required by default.
Not a framework test -- asserts and exits non-zero on failure.
"""
import sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymupdf
from services.ingest import ingest_pdf
from app.rag import search, build_answer, NOT_FOUND
from app.documents import delete_document
from app.db import init_schema

PDF_TEXT = """Question 1:
What is the boiling point of water?
Answer: The boiling point of water is 100 degrees Celsius at sea level.

Question 2:
What state is ice?
Answer: Ice is the solid state of water.

Question 3:
How do plants make food?
Answer: Plants make food through photosynthesis using sunlight.
"""


def make_pdf(path):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), PDF_TEXT, fontsize=11)
    doc.save(str(path))
    doc.close()


def run_checks(did):
    # --- retrieval: correct chunk picked without embeddings ---
    retrieval = [
        ("What is the boiling point of water?", 1, "exact"),
        ("question 2", 2, "question_number"),
        ("How do plants make food?", 3, "exact"),
    ]
    for query, want_num, want_type in retrieval:
        rs = search(did, query)
        assert rs, f"no result for {query!r}"
        got = rs[0]
        assert got.get('question_number') == want_num, (
            f"{query!r}: expected Q{want_num}, got Q{got.get('question_number')}"
        )
        assert got['match_type'] == want_type, (
            f"{query!r}: expected {want_type}, got {got['match_type']}"
        )
        print(f"OK retrieval  {query!r:45} -> Q{want_num} ({want_type})")

    # --- generation: grounded answer from the chat gateway ---
    q = "At what temperature does water boil?"
    ans = build_answer(search(did, q), q)
    assert ans and ans != NOT_FOUND, f"expected a grounded answer, got: {ans!r}"
    assert "100" in ans, f"answer should mention 100 (C); got: {ans!r}"
    print(f"OK generation grounded answer -> {ans!r}")

    # --- generation: refuses when context lacks the answer ---
    q = "Who wrote Hamlet?"
    ans = build_answer(search(did, q), q)
    assert "hamlet" not in ans.lower() or NOT_FOUND.lower() in ans.lower(), (
        f"expected refusal for out-of-context question; got: {ans!r}"
    )
    print(f"OK generation out-of-context -> {ans!r}")


def main():
    init_schema()
    did = None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / 'selfcheck_sample.pdf'
            make_pdf(pdf)
            meta = ingest_pdf(pdf, original_name='selfcheck_sample.pdf')
            did = meta['document_id']
        assert meta['records'] == 3, f"expected 3 Q/A records, got {meta['records']}"
        assert meta['answer_engine'] == 'chat-llm', meta
        run_checks(did)
        print("\nAll checks passed: text retrieval + LLM answer generation working.")
    finally:
        if did:
            delete_document(did)


if __name__ == '__main__':
    main()
