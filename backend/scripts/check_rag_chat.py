#!/usr/bin/env python3
"""Проверка RAG через чат: отправка примеров вопросов и проверка ключевых слов в ответе.

Использование:
  export BASE_URL=http://localhost:8000
  export SESSION_TOKEN=your-admin-or-user-token
  python -m scripts.check_rag_chat

Опционально CHECK=1 — проверять наличие ожидаемых подстрок в ответе (exit 1 при отсутствии).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

# Примеры вопросов и ожидаемые подстроки в ответе (хотя бы одна должна встретиться)
RAG_CHECKS = [
    {
        "message": "Как упаковать зеркало на ВБ?",
        "expected_substrings": ["пузырчат", "коробк", "хрупк", "картон", "плёнк"],
        "description": "упаковка зеркала WB",
    },
    {
        "message": "Как упаковать обувь на Wildberries?",
        "expected_substrings": ["коробк", "пакет", "скотч", "резинк", "обув"],
        "description": "упаковка обуви WB",
    },
    {
        "message": "Как упаковать посуду?",
        "expected_substrings": ["пузырчат", "коробк", "плёнк", "стекл"],
        "description": "упаковка посуды",
    },
]


def main() -> None:
    base_url = (os.getenv("BASE_URL") or "http://localhost:8000").rstrip("/")
    token = os.getenv("SESSION_TOKEN")
    check_mode = os.getenv("CHECK", "").strip().lower() in ("1", "true", "yes")

    if not token:
        print("Задайте SESSION_TOKEN (токен сессии пользователя или админа).", file=sys.stderr)
        sys.exit(2)

    failed = []
    for item in RAG_CHECKS:
        msg = item["message"]
        desc = item.get("description", msg[:50])
        expected = item.get("expected_substrings") or []

        try:
            r = httpx.post(
                f"{base_url}/api/v1/ai/chat",
                json={"message": msg},
                headers={"X-Session-Token": token},
                timeout=30.0,
            )
            r.raise_for_status()
            data = r.json()
            answer = (data.get("answer") or "").lower()
            print(f"[{desc}] Ответ: {answer[:200]}...")
        except Exception as e:
            print(f"[{desc}] Ошибка: {e}", file=sys.stderr)
            failed.append(desc)
            continue

        if check_mode and expected:
            found = any(s.lower() in answer for s in expected)
            if not found:
                print(f"[{desc}] Ожидалась хотя бы одна из подстрок: {expected}", file=sys.stderr)
                failed.append(desc)

    if failed:
        print(f"\nПровалено: {failed}", file=sys.stderr)
        sys.exit(1)
    print("\nВсе проверки пройдены.")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    main()
