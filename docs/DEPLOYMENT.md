# Развёртывание

## Инфраструктура

- **VPS Beget**, Nginx (reverse proxy), Docker (при использовании контейнеров).
- Frontend — статика (сборка Vite); отдача через Nginx или из контейнера.
- Backend — FastAPI (uvicorn/gunicorn) за Nginx.

## Секреты и конфигурация

- Все секреты и чувствительные параметры — в **переменных окружения** (env), не в репозитории.
- Примеры: `POSTGRES_DSN`, `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_IDS`, `S3_*`, `DADATA_TOKEN`.

## Nginx

- Для маршрутов загрузки файлов обязательно задать **client_max_body_size** (соответствовать лимиту бэкенда, например 10 MB).

## База данных

- Перед запуском приложения применить миграции Alembic к PostgreSQL.
