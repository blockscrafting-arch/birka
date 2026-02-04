"""
Скрипт диагностики и восстановления админ-доступа и компаний.

Использование:
  cd backend && python -m scripts.fix_admin_and_companies list     # список пользователей и ролей
  cd backend && python -m scripts.fix_admin_and_companies fix      # выставить admin по ADMIN_TELEGRAM_IDS
  cd backend && python -m scripts.fix_admin_and_companies fix --telegram-id=123456  # выставить admin одному

Требует .env с POSTGRES_DSN. В проде: docker compose -f docker-compose.prod.yml exec backend python -m scripts.fix_admin_and_companies list
"""
import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.company import Company
from app.db.models.user import User
from app.db.session import AsyncSessionLocal


async def list_users(session: AsyncSession) -> None:
    """Вывести пользователей и роли."""
    result = await session.execute(
        select(User.id, User.telegram_id, User.role, User.first_name, User.last_name).order_by(User.id)
    )
    rows = result.all()
    admin_ids = set(settings.admin_telegram_ids)
    print("Пользователи (id, telegram_id, role, first_name, last_name):")
    for r in rows:
        mark = " <- должен быть admin (в ADMIN_TELEGRAM_IDS)" if r.telegram_id in admin_ids else ""
        print(f"  {r.id}  {r.telegram_id}  {r.role!r}  {r.first_name} {r.last_name}{mark}")
    print(f"\nADMIN_TELEGRAM_IDS из .env: {settings.ADMIN_TELEGRAM_IDS!r} -> {admin_ids}")


async def fix_admin(session: AsyncSession, telegram_id: int | None = None) -> None:
    """Выставить роль admin пользователям по ADMIN_TELEGRAM_IDS или одному telegram_id."""
    if telegram_id is not None:
        ids_to_admin = [telegram_id]
    else:
        ids_to_admin = settings.admin_telegram_ids
    if not ids_to_admin:
        print("Не заданы ADMIN_TELEGRAM_IDS и не передан --telegram-id. Ничего не делаю.")
        return
    result = await session.execute(select(User).where(User.telegram_id.in_(ids_to_admin)))
    users = result.scalars().all()
    for u in users:
        if u.role != "admin":
            u.role = "admin"
            print(f"  user_id={u.id} telegram_id={u.telegram_id} -> role=admin")
    await session.commit()
    if not users:
        print("Пользователи с указанными telegram_id не найдены.")
    else:
        print("Готово. Перелогиньтесь в приложении, чтобы увидеть админку.")


async def list_companies(session: AsyncSession) -> None:
    """Вывести компании и владельцев."""
    result = await session.execute(
        select(Company.id, Company.name, Company.user_id).order_by(Company.id)
    )
    rows = result.all()
    print("Компании (id, name, user_id):")
    for r in rows:
        print(f"  {r.id}  {r.name!r}  user_id={r.user_id}")


async def main() -> None:
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "list"
    telegram_id = None
    for arg in sys.argv[2:]:
        if arg.startswith("--telegram-id="):
            try:
                telegram_id = int(arg.split("=", 1)[1])
            except ValueError:
                print("Неверный --telegram-id")
                sys.exit(1)

    async with AsyncSessionLocal() as session:
        if cmd == "list":
            await list_users(session)
            print()
            await list_companies(session)
        elif cmd == "fix":
            await fix_admin(session, telegram_id=telegram_id)
        else:
            print("Использование: fix_admin_and_companies list | fix [--telegram-id=N]")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
