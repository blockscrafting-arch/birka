# Развёртывание

## Инфраструктура

- **VPS Beget**, Nginx (reverse proxy), Docker (при использовании контейнеров).
- Frontend — статика (сборка Vite); отдача через Nginx или из контейнера.
- Backend — FastAPI (uvicorn/gunicorn) за Nginx.

## Секреты и конфигурация

- Все секреты и чувствительные параметры — в **переменных окружения** (env), не в репозитории.
- Примеры: `POSTGRES_DSN`, `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_IDS`, `S3_*`, `DADATA_TOKEN`, `ENCRYPTION_KEY` (опционально: Fernet-ключ для шифрования API-ключей WB/Ozon в БД; сгенерировать: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).

## Nginx

- Для маршрутов загрузки файлов обязательно задать **client_max_body_size** (соответствовать лимиту бэкенда, например 10 MB).

## База данных

- Перед запуском приложения применить миграции Alembic к PostgreSQL.

## Команды деплоя (из корня репозитория)

Все команды выполнять из **корня проекта** (`/opt/birka` или ваш путь к репозиторию), не из `frontend/` или `backend/`.

```bash
# 1. Перейти в корень проекта
cd /opt/birka

# 2. Подтянуть код
git pull origin main

# 3. Сборка фронтенда (опционально, если не используете Docker для фронта)
cd frontend && npm run build && cd ..

# 4. Собрать и запустить контейнеры
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d

# 5. Применить миграции БД
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

Если бэкенд **не в Docker** (запуск напрямую на VPS):

```bash
cd /opt/birka/backend
alembic upgrade head
```
