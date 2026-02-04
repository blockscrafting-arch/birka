"""Seed RAG with packaging requirements from docs/rag/*.txt.

Run from backend directory with OPENAI_API_KEY set:
  python -m scripts.seed_rag_documents

Reads all .txt files from docs/rag/ (relative to project root) and uploads them
into document_chunks with embeddings.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import AsyncSessionLocal
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
    """Find docs/rag/*.txt and upload each to RAG."""
    rag_dir = _resolve_rag_dir()
    if not rag_dir or not rag_dir.is_dir():
        print("Directory not found for docs/rag. Set DOCS_RAG_PATH or copy docs into image.")
        return
    files = sorted(rag_dir.glob("*.txt"))
    if not files:
        print(f"No .txt files in {rag_dir}")
        return
    async with AsyncSessionLocal() as db:
        for path in files:
            content = path.read_text(encoding="utf-8")
            name = path.name
            count = await upload_document_to_rag(db, content, name)
            print(f"  {name}: {count} chunks")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
