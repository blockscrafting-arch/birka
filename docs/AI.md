# AI-бот

## Эндпоинты

**Файл маршрутов:** `backend/app/api/v1/routes/ai.py`

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/ai/history` | История чата (query: `company_id` опционально). Последние 50 сообщений. |
| DELETE | `/api/v1/ai/history` | Очистка истории для текущего пользователя и опционально company_id. |
| POST | `/api/v1/ai/chat` | Отправка сообщения. Тело: `message`, `company_id` (опционально). Ответ и сохранение в БД (ChatMessage). |

## Сервис OpenAI

**Файл:** `backend/app/services/openai_service.py`

- Класс **OpenAIService**, метод **chat(messages, db, user, company_id)**.
- Если переданы `db` и `user` — включается режим **tools** (function calling): модель может вызывать функции, результаты подставляются в диалог, до 10 раундов.
- Модель: **gpt-4o-mini**.

## Инструменты (tools)

**Файл:** `backend/app/services/ai_tools.py`

- **TOOLS** — список описаний функций для OpenAI (name, description, parameters).
- **execute_tool(name, arguments, db, user, company_id)** — выполнение с проверкой доступа к компании (`_ensure_company`: client — только свои компании, warehouse/admin — по company_id).

Список инструментов:

| Имя | Описание |
|-----|----------|
| get_orders | Список заявок (опционально фильтр по статусу). |
| get_order_details | Детали заявки по номеру (позиции, услуги). |
| get_products | Список товаров с остатками и браком. |
| get_product_details | Детали товара по штрихкоду или названию. |
| get_stock_summary | Сводка по остаткам и браку. |
| get_shipment_requests | Заявки на отгрузку. |
| get_services_price | Прайс услуг (опционально по категории). |
| get_company_info | Реквизиты компании. |
| get_destinations | Адреса доставки. |

Лимиты (MAX_ORDERS, MAX_PRODUCTS и т.д.) заданы в модуле, чтобы не переполнять контекст ответа.

## RAG

**Файл:** `backend/app/services/rag.py`

- Статическая инструкция + при наличии — документы из БД (**DocumentChunk**), эмбеддинги (OpenAI text-embedding-3-small).
- В роуте перед вызовом OpenAI пользовательское сообщение обогащается контекстом: **build_rag_context_async(db, payload.message)**.

## Системный промпт

В роуте задаётся инструкция: помощник фулфилмента Бирка; по заявкам, товарам, остаткам, браку, отгрузкам, прайсу, реквизитам — всегда вызывать соответствующие функции и отвечать только по полученным данным; не придумывать номера заявок и не использовать заглушки.
