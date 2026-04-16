# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Проект

Telegram Mini App «Бирка» — система фулфилмента. Клиенты видят статусы/дефекты, склад управляет приёмкой/упаковкой/отгрузкой, AI-бот отвечает на вопросы.

## Стек

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Alembic, Celery + Redis, Sentry
- **Frontend:** React 18, TypeScript (strict), Vite, Tailwind CSS 3, React Query, Zustand, Sentry
- **БД:** PostgreSQL 15 + pgvector (RAG), Redis (кеш/брокер)
- **Инфра:** Docker Compose, Nginx (SSL, gzip), S3 (Beget), LibreOffice (headless)
- **Линтер:** Ruff (backend), ESLint + TypeScript strict (frontend)

## Команды

```bash
# Backend
cd backend && python3 -m pytest tests/ -v --tb=short --cov=app  # тесты с coverage
cd backend && ruff check app/                                     # линтер
cd backend && ruff format --check app/                            # формат
cd backend && alembic upgrade head                                # миграции
cd backend && uvicorn app.main:app --reload --port 8000           # dev-сервер

# Frontend
cd frontend && npm run dev        # dev-сервер
cd frontend && npm run build      # сборка
cd frontend && npm run lint       # линтер
cd frontend && npx tsc --noEmit   # type check
cd frontend && npm test -- --run  # тесты (vitest)

# Docker
docker compose up -d                                     # dev
docker compose -f docker-compose.prod.yml up -d          # prod
bash scripts/deploy-prod.sh                              # полный деплой (сборка + бэкап + миграции + health check)

# Make
make test-backend      # pytest
make test-frontend     # lint + test
make build-frontend    # vite build
make check-readiness   # тесты бэка + сборка фронта
make health            # curl /health
```

## Архитектура

### Backend (FastAPI)

- **Entrypoint:** `backend/app/main.py` — создание приложения, lifespan, CORS, Sentry, `/health`
- **API:** `/api/v1/` — 11 роутеров в `app/api/v1/routes/` (auth, admin, companies, products, orders, services, shipping, warehouse, fbo, destinations, ai)
- **Сервисы:** `app/services/` — бизнес-логика (AI, RAG, S3 с tenacity retry, marketplace API, Excel, PDF, barcode)
- **Модели:** `app/db/models/` — 22+ SQLAlchemy ORM модели, async через asyncpg
- **Схемы:** `app/schemas/` — Pydantic v2 request/response модели
- **Фоновые задачи:** `app/celery_app.py` + `app/tasks/` — конвертация документов, авто-закрытие отгрузок, очистка сессий, очистка orphaned S3 объектов. Все задачи имеют `autoretry_for` + `retry_backoff`

### Frontend (React SPA)

- **Entrypoint:** `frontend/src/main.tsx` (Sentry init) → `App.tsx` (ErrorBoundary, React Router)
- **Роуты:** `/client/*`, `/warehouse/*`, `/admin/*` — ролевая навигация
- **API-клиент:** `src/services/api.ts` — fetch-обёртка с auth-заголовками, auto token refresh при 401
- **Code splitting:** все страницы через `React.lazy()` + `Suspense`
- **Хуки:** `src/hooks/` — useUser, useOrders, useProducts и др. (React Query)
- **Сторы:** `src/stores/` — Zustand (aiChatStore, uploadStore)
- **Компоненты:** `src/components/` — layout/, shared/ (BarcodeScanner, PhotoUpload), ui/

### Аутентификация

- Заголовок `X-Telegram-Init-Data` — HMAC-SHA256 валидация через Telegram Bot Token
- Заголовок `X-Session-Token` — сессия из БД с expires_at, автоочистка через Celery beat
- Роли: client (по умолчанию), warehouse, admin
- Админы задаются через `ADMIN_TELEGRAM_IDS` в .env
- RBAC: `get_current_user()` + `require_roles()` в `app/api/v1/deps.py`
- Rate limiting: slowapi на всех мутирующих admin endpoints (30/min), auth (10/min), uploads (60/min)
- Frontend: auto token refresh через Telegram initData при 401

### Ключевые паттерны

- **S3:** В БД хранится только ключ объекта, URL строится на бэке через `FILE_PUBLIC_BASE_URL`. Загрузка non-chunked с tenacity retry (3 попытки, exponential backoff), после загрузки HEAD-проверка. Еженедельная Celery-задача `s3_cleanup` удаляет orphaned объекты
- **AI:** OpenAI/OpenRouter через `openai_service.py`, function calling (8 инструментов в `ai_tools.py`), RAG через pgvector + embeddings. Company_id валидируется на входе endpoint'а И в ai_tools._ensure_company (defense-in-depth)
- **Marketplace:** WB/Ozon API через зашифрованные ключи (Fernet) в `CompanyAPIKeys`. ENCRYPTION_KEY обязателен в production (model_validator). `CompanyAPIKeysOut` возвращает `has_wb/has_ozon_client_id/has_ozon_api_key` (computed_field) + masked строки. `DELETE /companies/{id}/api-keys` — удаление всех ключей
- **OrderCounter:** atomic upsert через `INSERT ON CONFLICT DO UPDATE RETURNING` — безопасно при параллельных запросах
- **Celery Beat:** авто-закрытие просроченных отгрузок (с retry), конвертация RTF/DOCX/PDF через LibreOffice (с retry), очистка сессий (каждый час), очистка S3 (воскресенье 03:00)
- **Пакинг:** remainder = received − defect − packed. Нельзя упаковать больше, чем доступно за вычетом брака
- **Notifications:** Telegram-уведомления после commit обёрнуты в try/except — ошибка уведомления не ломает API-ответ
- **Логирование:** structlog (JSON-формат в stdout), уровень INFO. ~135 точек логирования: routes (40), services (90), tasks (5). Покрыты: S3 retry, cache fallback, crypto no-key, Celery задачи, Telegram уведомления, contract PDF ошибки. Запрещено логировать ПДн. Sentry для ошибок уровня exception/critical
- **DB pooling:** pool_size=10, max_overflow=20, pool_recycle=3600, pool_pre_ping=True

### Безопасность (production)

- `config.py` model_validator: ENCRYPTION_KEY, CORS_ORIGINS≠*, TELEGRAM_BOT_TOKEN — обязательны
- Docker: `read_only`, `cap_drop: ALL`, `no-new-privileges`, `tmpfs` для backend/celery
- Healthchecks: redis (redis-cli ping), backend (curl /health)
- Log rotation: json-file, max-size 10m, max-file 3
- `deploy-prod.sh`: pg_dump бэкап перед миграциями + health check loop после
- Nginx: gzip, security headers (CSP, HSTS, X-Frame-Options), DNS resolver TTL 60s
- FK cascades: OrderPhoto, PackingRecord → CASCADE DELETE; shipment/fbo → SET NULL

### Миграции

Alembic, 30 версий в `backend/alembic/versions/` (0001–0030). Требуется расширение pgvector для таблицы document_chunk (RAG embeddings). Последние миграции: 0028 (indexes), 0029 (FK cascades), 0030 (CASCADE on photos/packing).

## Правила кода

- Публичные функции/классы — с docstrings
- Все ошибки логировать через единый логгер (structlog), без ПДн
- Валидация входа через Pydantic, доверять только проверенным данным
- Новые Celery-задачи обязательно с `autoretry_for=(Exception,)` + `retry_backoff=True`
- S3 операции через `S3Service` (имеет tenacity retry)
- Frontend: только функциональные компоненты и хуки, lazy loading для страниц
- Тесты: **243 backend-теста** (pytest), **23 frontend-теста** (vitest). Критические потоки полностью покрыты: auth/RBAC, packing math, order lifecycle E2E, IDOR isolation, S3 retry, Celery tasks, rate limits, token refresh. Запуск: `python -m pytest tests/ -v --tb=short` / `npm test -- --run`
- Линтер: `ruff check` (backend), `eslint` + `tsc --noEmit` (frontend)
- В nginx обязательно `client_max_body_size`
- Секреты только в .env, никогда в коде/коммитах

## Конфигурация

Все настройки через переменные окружения (`.env`). Шаблон — `.env.example`. Backend загружает через pydantic-settings (`app/core/config.py`). В production запускается model_validator, проверяющий обязательные переменные. Frontend использует `VITE_*` переменные (build-time). Sentry: `SENTRY_DSN` (backend), `VITE_SENTRY_DSN` (frontend).
