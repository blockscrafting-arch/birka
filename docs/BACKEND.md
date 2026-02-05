# Backend (FastAPI)

## Точка входа

- **Файл:** `backend/app/main.py`
- **API:** префикс `/api/v1`
- Приложение создаётся в `create_app()`: CORS, лимитер (slowapi), обработчики исключений, health-check `/health` (проверка БД). При старте — `sync_roles_on_startup()` (выставляет роль admin пользователям из `ADMIN_TELEGRAM_IDS`).

## Маршруты

Подключение в `backend/app/api/v1/router.py`:

| Префикс | Тег | Описание |
|---------|-----|----------|
| `/auth` | auth | Авторизация, сессии |
| `/admin` | admin | Админка |
| `/companies` | companies | Компании |
| `/destinations` | destinations | Адреса доставки |
| `/products` | products | Товары |
| `/orders` | orders | Заявки |
| `/services` | services | Услуги |
| `/shipping` | shipping | Отгрузки |
| `/warehouse` | warehouse | Склад (приёмка, упаковка) |
| `/ai` | ai | Чат с AI, история |

## Авторизация

**Файл:** `backend/app/api/v1/deps.py`

- **get_current_user:** текущий пользователь определяется по одному из заголовков:
  - **X-Session-Token** — сессия в БД (`Session`), проверка срока действия.
  - **X-Telegram-Init-Data** — проверка подписи Telegram (`validate_telegram_init_data`), парсинг пользователя (`parse_init_data_user`). Если пользователя нет в БД — создаётся (роль из `ADMIN_TELEGRAM_IDS` → admin, иначе client).
- **require_roles(*roles)** — зависимость для доступа по ролям (client, warehouse, admin).

## Конфигурация

**Файл:** `backend/app/core/config.py`

Класс `Settings` (pydantic-settings, из env и `.env`):

- **Auth:** `ADMIN_TELEGRAM_IDS`, `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`
- **БД:** `POSTGRES_DSN`
- **CORS:** `CORS_ORIGINS`
- **Загрузки:** `MAX_UPLOAD_SIZE_BYTES`
- **Dadata:** `DADATA_TOKEN`
- **S3:** `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_BUCKET_NAME`, `FILE_PUBLIC_BASE_URL`

Секреты хранить только в env, не в репозитории.

## Правила разработки

- Все публичные функции/классы/модули — с docstrings.
- Ошибки логировать через единый логгер, без ПДн в логах.
- Валидация входа через Pydantic.
- URL к файлам строить централизованно на бэке; в БД — только ключ объекта.
- После загрузки файла — HEAD-проверка доступности.
- Для S3 (Beget) — non-chunked загрузка.
