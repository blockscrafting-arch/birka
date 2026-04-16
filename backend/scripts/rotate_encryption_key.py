"""
Скрипт ротации ENCRYPTION_KEY: перешифрование API-ключей компаний новым ключом.

Использование:
  1. Сгенерировать новый ключ: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  2. В .env задать:
     OLD_ENCRYPTION_KEY=<текущий ключ>
     NEW_ENCRYPTION_KEY=<новый ключ>
  3. Запустить:
     cd backend && python -m scripts.rotate_encryption_key
  4. После успешного выполнения заменить в .env ENCRYPTION_KEY на NEW_ENCRYPTION_KEY и перезапустить приложение.

Требует .env с POSTGRES_DSN, OLD_ENCRYPTION_KEY, NEW_ENCRYPTION_KEY.
В проде: docker compose -f docker-compose.prod.yml exec backend python -m scripts.rotate_encryption_key
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_value, encrypt_value
from app.db.models.company_api_keys import CompanyAPIKeys
from app.db.session import AsyncSessionLocal


async def rotate(session: AsyncSession, old_secret: str, new_secret: str) -> int:
    """
    Перешифровать все записи CompanyAPIKeys: расшифровать старым ключом, зашифровать новым.
    Возвращает количество обновлённых записей.
    """
    result = await session.execute(select(CompanyAPIKeys))
    rows = result.scalars().all()
    count = 0
    for row in rows:
        changed = False
        for field in ("wb_api_key", "ozon_client_id", "ozon_api_key"):
            value = getattr(row, field)
            if value is None or not value.strip():
                continue
            plain = decrypt_value(value, old_secret)
            new_cipher = encrypt_value(plain, new_secret)
            if new_cipher != value:
                setattr(row, field, new_cipher)
                changed = True
        if changed:
            count += 1
    await session.commit()
    return count


async def main() -> None:
    old_key = os.environ.get("OLD_ENCRYPTION_KEY", "").strip()
    new_key = os.environ.get("NEW_ENCRYPTION_KEY", "").strip()
    if not old_key or not new_key:
        print("Задайте OLD_ENCRYPTION_KEY и NEW_ENCRYPTION_KEY в окружении.")
        sys.exit(1)
    if old_key == new_key:
        print("OLD_ENCRYPTION_KEY и NEW_ENCRYPTION_KEY должны отличаться.")
        sys.exit(1)

    async with AsyncSessionLocal() as session:
        n = await rotate(session, old_key, new_key)
    print(f"Перешифровано записей: {n}. Замените ENCRYPTION_KEY на NEW_ENCRYPTION_KEY и перезапустите приложение.")


if __name__ == "__main__":
    asyncio.run(main())
