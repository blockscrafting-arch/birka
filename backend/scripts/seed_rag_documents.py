"""Seed RAG with packaging requirements from docs/rag/*.txt and docs/rag/*.docx.

Run from backend directory with OPENAI_API_KEY set:
  python -m scripts.seed_rag_documents

Reads all .txt and .docx files from docs/rag/ (e.g. Как_правильно_упаковать_разные_виды_товаров.docx)
and uploads them into document_chunks with embeddings.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import AsyncSessionLocal
from app.services.document_processor import index_document
from app.services.rag import upload_document_to_rag


def _resolve_rag_dir() -> Path | None:
    """Resolve docs/rag directory from env or common locations."""
    env_path = os.getenv("DOCS_RAG_PATH")
    if env_path:
        path = Path(env_path).expanduser()
        if path.is_dir():
            return path
    # Local dev: project root (backend/scripts -> backend -> project root)
    project_root = Path(__file__).resolve().parent.parent.parent
    candidates = [
        project_root / "docs" / "rag",
        Path("/app/docs/rag"),  # container path when docs are copied
        Path("/docs/rag"),      # legacy path (if mounted)
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


async def main() -> None:
    """Find docs/rag/*.txt and docs/rag/*.docx and upload each to RAG."""
    rag_dir = _resolve_rag_dir()
    if not rag_dir or not rag_dir.is_dir():
        print("Directory not found for docs/rag. Set DOCS_RAG_PATH or copy docs into image.")
        return
    files_txt = sorted(rag_dir.glob("*.txt"))
    files_docx = sorted(rag_dir.glob("*.docx"))
    if not files_txt and not files_docx:
        print(f"No .txt or .docx files in {rag_dir}")
        return
    async with AsyncSessionLocal() as db:
        for path in files_txt:
            content = path.read_text(encoding="utf-8")
            name = path.name
            count = await upload_document_to_rag(db, content, name)
            print(f"  {name}: {count} chunks")
        for path in files_docx:
            content = path.read_bytes()
            name = path.name
            count = await index_document(db, name, content, "docx")
            print(f"  {name}: {count} chunks")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
