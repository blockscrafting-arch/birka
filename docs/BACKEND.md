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
- **Shipment scheduler:** `SHIPMENT_SCHEDULER_INTERVAL_SECONDS` (интервал проверки просроченных отгрузок, по умолчанию 600)
- **CORS:** `CORS_ORIGINS`
- **Загрузки:** `MAX_UPLOAD_SIZE_BYTES`
- **Шифрование API-ключей:** `ENCRYPTION_KEY` (Fernet, base64 url-safe)
- **Dadata:** `DADATA_TOKEN`
- **S3:** `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_BUCKET_NAME`, `FILE_PUBLIC_BASE_URL`

Секреты хранить только в env, не в репозитории.

## FBO Ozon: цепочка поставки

**Файлы:** `backend/app/api/v1/routes/fbo.py`, `backend/app/services/ozon_client.py`

При синхронизации Ozon-поставки (POST `/fbo/supplies/{id}/sync`) выполняется:

1. **Сопоставление товаров:** по позициям в коробах загружаются продукты; используется `Product.ozon_article` как **offer_id**. Если у товара нет артикула Ozon — возвращается 400 с понятным текстом.
2. **Разрешение sku:** `POST /v3/product/info/list` (offer_id → sku) для формирования черновика.
3. **Черновик:** `POST /v1/draft/create` (items: sku + quantity) → `operation_id`; опрос `POST /v1/draft/create/info` до получения `draft_id`, `warehouse_id`, `timeslots`.
4. **Поставка:** `POST /v1/draft/supply/create` (draft_id, warehouse_id, timeslot) → опрос `POST /v1/supply/create/status` → `supply_id` (order_ids).
5. **Грузоместа:** `POST /v1/cargoes/create` (supply_id, cargoes: по коробам items с offer_id и quantity); опрос `POST /v2/cargoes/create/info` → список `cargo_id`.
6. **Сохранение:** в БД записываются `external_supply_id` и по каждому коробу `external_box_id` (cargo_id).
7. **Этикетки:** GET `/fbo/supplies/{id}/labels` отдаёт PDF по `POST /v1/cargoes-label/create` и последующей загрузке файла по `file_guid`.

## FBO WB: поставки и этикетки

**Файлы:** `backend/app/api/v1/routes/fbo.py`, `backend/app/services/wb_client.py`

- **Создание поставки:** `POST /api/v3/supplies` (name) → в БД сохраняется `external_supply_id` (id поставки WB).
- **Этикетки:** в первую очередь запрашивается штрихкод поставки `GET /api/v3/supplies/{supplyId}/barcode` (PNG/SVG); при недоступности — стикеры коробов `POST /api/v3/supplies/{supplyId}/trbx/stickers`; запасной вариант — стикеры заказов FBS по `order_ids` из штрихкодов коробов (`POST /api/v3/orders/stickers`).

## Правила разработки

- Все публичные функции/классы/модули — с docstrings.
- Ошибки логировать через единый логгер, без ПДн в логах.
- Валидация входа через Pydantic.
- URL к файлам строить централизованно на бэке; в БД — только ключ объекта.
- После загрузки файла — HEAD-проверка доступности.
- Для S3 (Beget) — non-chunked загрузка.
