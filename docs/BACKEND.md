# Backend (FastAPI)

## Точка входа

- **Файл:** `backend/app/main.py`
- **API:** префикс `/api/v1`
- Приложение создаётся в `create_app()`: CORS, лимитер (slowapi), обработчики исключений, health-check `/health` (проверка БД).
- **Старт (lifespan):**
  - `sync_roles_on_startup()` — выставляет роль admin пользователям из `ADMIN_TELEGRAM_IDS`; роль warehouse задаётся только вручную в админке.
  - Запуск фоновой задачи **shipment scheduler** — периодическая проверка просроченных отгрузок (интервал задаётся `SHIPMENT_SCHEDULER_INTERVAL_SECONDS`).

## Маршруты

Подключение в `backend/app/api/v1/router.py`:

| Префикс | Тег | Описание |
|---------|-----|----------|
| `/auth` | auth | Авторизация, сессии (telegram, logout, me) |
| `/admin` | admin | Админка: пользователи, шаблоны договоров, документы, RAG, AI-настройки |
| `/companies` | companies | Компании, API-ключи WB/Ozon, договоры |
| `/destinations` | destinations | Адреса доставки |
| `/products` | products | Товары, импорт/экспорт, этикетки, фото брака |
| `/orders` | orders | Заявки, позиции, фото, записи упаковки, экспорт приёмки |
| `/services` | services | Услуги (прайс), категории, расчёт, история цен, импорт/экспорт, PDF |
| `/shipping` | shipping | Заявки на отгрузку, статусы, штрихкоды поставок |
| `/fbo` | fbo | FBO-поставки WB/Ozon: создание, синхронизация, этикетки коробов, импорт ШК |
| `/warehouse` | warehouse | Приёмка, упаковка, валидация ШК, завершение заказа, экспорт FBO |
| `/ai` | ai | Чат с AI, история сообщений |

### Дополнительные эндпоинты

- **DELETE /api/v1/companies/{company_id}** — удаление компании. Доступно только владельцу. Возвращает 400, если у компании есть заявки не в статусе «Завершено».
- **GET /api/v1/orders/import/template** — скачивание пустого шаблона Excel для импорта заявки (колонки: Название, Количество и др.).
- **POST /api/v1/orders/import** — импорт заявки из Excel (`company_id` в query, файл в body). Обязательные столбцы: Название, Количество. Товары ищутся по баркоду или создаются новые.
- **GET /api/v1/orders/{order_id}/export** — экспорт товаров заявки в Excel.
- **POST /api/v1/orders/{order_id}/export/send** — отправка файла экспорта заявки в Telegram чат с ботом.
- **POST /api/v1/warehouse/receiving/complete** — завершение приёмки. Если обработаны не все товары заявки, возвращает `{"status": "partial", "received", "defects", "remaining"}` и статус заявки не меняется. При приёмке всех товаров — статус «Принято», уведомление в Telegram. Для брака требуется не меньше фото, чем единиц брака по каждому товару.
- **Экспорт товаров (products):** колонки без «Название компании»; добавлена колонка «Остаток».

## Авторизация

**Файл:** `backend/app/api/v1/deps.py`

- **get_current_user:** текущий пользователь определяется по одному из заголовков:
  - **X-Session-Token** — сессия в БД (`Session`), проверка срока действия.
  - **X-Telegram-Init-Data** — проверка подписи Telegram (`validate_telegram_init_data`), парсинг пользователя (`parse_init_data_user`). Если пользователя нет в БД — создаётся (роль из `ADMIN_TELEGRAM_IDS` → admin, иначе client).
- **require_roles(*roles)** — зависимость для доступа по ролям (client, warehouse, admin).

## Конфигурация

**Файл:** `backend/app/core/config.py`

Класс `Settings` (pydantic-settings, из env и `.env`):

- **Auth:** `ADMIN_TELEGRAM_IDS`, `TELEGRAM_BOT_TOKEN`
- **AI:** `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `AI_PROVIDER` (openai | openrouter), `AI_MODEL` (например gpt-4o-mini или openai/gpt-4o для OpenRouter)
- **БД:** `POSTGRES_DSN`
- **Redis:** `REDIS_DSN` (опционально) — для кэша и Celery (worker, beat). В production с docker-compose задать `redis://redis:6379/0`; в [docker-compose.prod.yml](../docker-compose.prod.yml) для celery_worker и celery_beat переменная переопределена через `environment`, чтобы не зависеть от .env. При пустом REDIS_DSN в логах Celery выводится предупреждение и используется fallback localhost (для локальной разработки).
- **Shipment scheduler:** `SHIPMENT_SCHEDULER_INTERVAL_SECONDS` (интервал проверки просроченных отгрузок, по умолчанию 600)
- **CORS:** `CORS_ORIGINS`
- **Загрузки:** `MAX_UPLOAD_SIZE_BYTES`
- **Шифрование API-ключей:** `ENCRYPTION_KEY` (Fernet, base64 url-safe)
- **Dadata:** `DADATA_TOKEN`
- **S3:** `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_BUCKET_NAME`, `FILE_PUBLIC_BASE_URL`

Секреты хранить только в env, не в репозитории.

## Даты и время

Для колонок БД без timezone (`DateTime()` без `timezone=True`) храним UTC в виде naive datetime. В коде при записи в такие поля использовать `datetime.now(timezone.utc).replace(tzinfo=None)`. Исключения: колонки с `DateTime(timezone=True)` (например document_chunks.created_at, ai_settings.updated_at) — туда передаём aware datetime.

## Логирование и ПДн

- **Не логировать персональные данные (PII):** в логах не должно быть `telegram_id`, email, телефонов, токенов, паролей и иных данных, по которым можно однозначно идентифицировать лицо (GDPR, OWASP A09).
- Допустимо при необходимости логировать только внутренние идентификаторы (например `user_id` — ID в БД) для расследования инцидентов.
- Логгер: `app.core.logging.logger` (structlog, JSON в stdout).

## Правила разработки

- Все публичные функции/классы/модули — с docstrings.
- Ошибки логировать через единый логгер, без ПДн в логах (см. раздел выше).
- Валидация входа через Pydantic.
- URL к файлам строить централизованно на бэке; в БД — только ключ объекта.
- После загрузки файла — HEAD-проверка доступности.
- Для S3 (Beget) — non-chunked загрузка.
- **Async SQLAlchemy:** не обращаться к атрибутам загруженных ORM-объектов после `await db.commit()`, если сессия создана с дефолтным `expire_on_commit=True`. После commit объекты считаются expired, обращение к атрибутам вызывает lazy load и в async приводит к `MissingGreenlet`. Сохранять нужные значения в локальные переменные до commit либо перезагружать объект через `await db.refresh(obj)` после commit.