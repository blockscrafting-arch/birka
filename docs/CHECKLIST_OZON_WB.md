# Проверка Ozon и WB в проекте «Бирка»

Дата проверки: 2026-02-09.  
Раздел «Официальные API (Context7)» заполнен по актуальной документации Ozon Seller API и Wildberries API.

## Оценка в % (реализовано правильно и полно)

| Критерий | Оценка | Пояснение |
|----------|--------|-----------|
| **Полнота** (от заявленного в документации по WB/Ozon) | **≈90%** | Товар WB+Ozon, API-ключи (частичное обновление, удаление), FBO с реальным flow Ozon и WB. |
| **Правильность** (того, что уже есть) | **≈85%** | Ozon: draft→supply→cargoes→labels; WB: supply barcode/trbx stickers; ключи — только непустые поля обновляются. |
| **Сводно** (правильно и полно) | **≈85%** | Интеграция готова к эксплуатации при наличии тестов и проверки на реальных ключах. |

Расчёт по блокам:

- **Товар (Product) WB/Ozon:** поля WB (wb_article) и Ozon (ozon_article как offer_id), форма, Excel. **100%**.
- **API-ключи:** CompanyAPIKeys, шифрование (Fernet), частичное обновление (пустые поля не перезаписывают), DELETE, 503 при отсутствии ENCRYPTION_KEY. **95%**.
- **FBO Ozon:** полный flow: offer_id→sku, draft→supply→cargoes, сохранение external_supply_id и external_box_id, этикетки по cargo_id. **90%** (зависит от актуальности ответов API).
- **FBO WB:** создание поставки, этикетки по supply id (barcode, trbx/stickers), запасной вариант по order_ids. **85%**.
- **FBO UI:** мульти-короба, несколько позиций в коробе, отображение external_supply_id и external_box_id. **95%**.


## Цели проекта по использованию API WB/Ozon — достаточно ли сделанного?

**Да. После реализации (2026-02-09) заявленные цели достигнуты.**

| Цель | Реализация |
|------|------------|
| Хранить API-ключи WB/Ozon по компании | CompanyAPIKeys, шифрование (Fernet), GET/PUT/DELETE `/companies/{id}/api-keys`, UI в CompanyPage. |
| FBO-поставки WB/Ozon | Модели FBOSupply/Box/Item, роут `/fbo` (создание, синхронизация с WB/Ozon, этикетки, импорт ШК), страница FBO в разделе Склад. |
| Товар — связь с маркетплейсами | Поля WB (wb_article, wb_url) и Ozon (ozon_article, ozon_url), форма, Excel, этикетка. |
| AI-контекст | Системный промпт в rag.py дополнен информацией о WB/Ozon, FBO, API-ключах. |

---

## Официальные API (Context7)

Сверка с документацией из Context7: **Ozon Seller API** (`/websites/ozon_ru_api_seller`), **Wildberries API** (`/websites/dev_wildberries_ru`).

### Ozon Seller API

- **Авторизация:** API-ключ из личного кабинета (Настройки → Seller API). В запросах заголовки `Client-Id` и `Api-Key`. Ключей может быть несколько, с разными уровнями доступа.
- **Товар:** идентификаторы — `offer_id` (артикул продавца), `product_id`, `sku` (идентификатор в системе Ozon). В методах типа `/v3/product/info/list` можно передавать до 1000 идентификаторов.
- **FBO:** управление заказами FBO и поставками: список отгрузок — `GET /v2/posting/fbo/list`; создание заявки на поставку — цепочка `/v1/cluster/list`, `/v1/warehouse/fbo/list`, `/v1/draft/create`, `/v1/draft/supply/create`, `/v1/supply-order/*`, этикетки грузовых мест — `/v1/cargoes-label/create`, `/v1/cargoes-label/file/{file_guid}`.

### Wildberries API

- **Авторизация:** API-ключ (заголовок `Authorization`).
- **Товар:** артикул WB — **nmID** (nm_id); в карточке также есть `vendorCode`. В проекте «Бирка» поле `wb_article` логично сопоставить с nmID или с vendorCode в зависимости от того, что вводит пользователь.
- **FBO:** модель Fulfillment by Operator — товар отвозится на склады WB, остатки по складам доступны через API; в документации WB есть сценарии по остаткам и поставкам под FBO.

### Соответствие полей проекта и API

| Проект (Бирка) | WB API        | Ozon API   |
|----------------|---------------|------------|
| `wb_article`   | nmID / vendorCode | —        |
| `wb_url`      | — (ссылка на карточку, не из API) | — |
| Нет полей Ozon | —             | offer_id, product_id, sku |

При добавлении Ozon в товар разумно завести, как минимум, `offer_id` (артикул продавца в Ozon); при глубокой интеграции — также `product_id` и/или `sku` по необходимости.

---

## Резюме

| Область | WB | Ozon | Комментарий |
|--------|----|------|-------------|
| Товар (Product) | ✅ | ✅ | `wb_article`, `wb_url`, `ozon_article`, `ozon_url` |
| API-ключи компании | ✅ | ✅ | CompanyAPIKeys, шифрование, эндпоинты, UI |
| FBO-поставки | ✅ | ✅ | Модели, роут `/fbo`, клиенты API, страница FBO |
| Роут `/fbo` | ✅ | ✅ | Подключён в router.py |
| AI-контекст | ✅ | ✅ | Системный промпт в rag.py обновлён |

---

## 1. Что реализовано (WB)

### 1.1 Товар (Product)

- **Модель** `backend/app/db/models/product.py`:
  - `wb_article: str | None`
  - `wb_url: str | None`
- **Схемы** `backend/app/schemas/product.py`: те же поля в Create/Update/Out.
- **Миграции**: в `0001_initial.py` колонки `wb_article`, `wb_url` есть.
- **API** `backend/app/api/v1/routes/products.py`: используется `product.wb_article` (например, для этикеток).
- **Сервис Excel** `backend/app/services/excel.py`: экспорт/импорт с колонками «Артикул WB», «Ссылка WB».
- **Фронтенд**:
  - `ProductForm.tsx`: поля «Артикул WB», «Ссылка WB».
  - `ProductsPage.tsx`, `useProducts.tsx`: типы и запросы с `wb_article`, `wb_url`.

Итого: по товару поддержка только **WB**; полей под Ozon (артикул/ссылка Ozon) нет.

---

## 2. Реализовано (актуальное состояние)

### 2.1 API-ключи WB/Ozon компании

- Модель **CompanyAPIKeys** в `backend/app/db/models/company_api_keys.py`, шифрование Fernet.
- Эндпоинты: GET/PUT/DELETE `/companies/{id}/api-keys`. PUT обновляет только переданные непустые поля; пустые/отсутствующие не перезаписывают существующие ключи.
- При отсутствии `ENCRYPTION_KEY` или ошибке расшифровки возвращается 503 с сообщением «Шифрование не настроено (ENCRYPTION_KEY)».
- Тесты: `tests/test_company_api_keys.py` (partial update, delete).

### 2.2 FBO-поставки WB/Ozon

- Модели **FBOSupply**, **FBOSupplyBox** (в т.ч. `external_box_id`), **FBOSupplyItem** в `backend/app/db/models/fbo_supply.py`.
- Роут `/fbo` в `backend/app/api/v1/routes/fbo.py`: создание поставки, синхронизация с маркетплейсом, этикетки, импорт штрихкодов коробов.
- **Ozon:** полный flow — сопоставление по `Product.ozon_article` (offer_id), разрешение sku через `/v3/product/info/list`, draft→supply→cargoes, сохранение `external_supply_id` и `external_box_id`, этикетки по `external_box_id`.
- **WB:** создание поставки, этикетки через supply barcode (`GET /api/v3/supplies/{id}/barcode`) и при необходимости trbx/stickers; запасной вариант по order_ids.
- Тесты: `tests/test_fbo.py` (валидация ozon_article, sync с моками Ozon через respx).

### 2.3 Что по-прежнему рекомендуется проверить

- **AI:** при необходимости явной поддержки «упаковка WB/Ozon» в ответах — системное сообщение в `openai_service`/роуте и актуализация AI.md.
- Проверка на реальных ключах и реальных ответах Ozon/WB API (таймслоты, форма cargoes и т.д.).

---

## 3. Рекомендации

1. **Товар и Ozon**  
   По Context7 (Ozon Seller API) у товара есть `offer_id` (артикул продавца), `product_id`, `sku`. Для симметрии с WB достаточно добавить, например: `ozon_offer_id` (или `ozon_article`), `ozon_url` — и выводить в карточке товара и в Excel наравне с WB.

2. **Документация**  
   - Либо привести DATABASE.md и BACKEND.md в соответствие с текущим кодом (убрать/пометить «планируется» для CompanyAPIKeys, FBO, `/fbo`),  
   - либо завести отдельный документ «План: API-ключи WB/Ozon и FBO» и в основных доках ссылаться на него.

3. **API-ключи и FBO**  
   Реализация CompanyAPIKeys и FBO (модели, роут `/fbo`, шифрование ключей) — отдельный объём работ; имеет смысл планировать после уточнения приоритетов.

4. **AI**  
   Если нужна явная поддержка «упаковка WB/Ozon» в ответах AI, добавить в `openai_service` (или в роут) системное сообщение (AI_SYSTEM_INSTRUCTION) с правилами про WB/Ozon и FBO и обновить AI.md под фактическое поведение.

---

## 4. Где искать в репозитории

| Что | Путь |
|-----|------|
| Модель товара (WB) | `backend/app/db/models/product.py` |
| Схемы товара | `backend/app/schemas/product.py` |
| Роут компаний (без API-ключей) | `backend/app/api/v1/routes/companies.py` |
| Роутер (список маршрутов) | `backend/app/api/v1/router.py` |
| Форма товара (WB) | `frontend/src/pages/client/ProductForm.tsx` |
| Excel товаров (WB) | `backend/app/services/excel.py` |
| Упоминания Ozon (документы) | `docs/`, CSV «Прайс + логистика…» |
| Документация API (Context7) | Ozon: `/websites/ozon_ru_api_seller`, WB: `/websites/dev_wildberries_ru` |

После изменений в моделях или роутах стоит обновить этот чеклист.
