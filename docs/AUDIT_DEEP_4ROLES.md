# Deep Code Review & Business Audit (4 роли)

**Дата:** 2026-02-09  
**Режим:** Жёсткая проверка — уязвимости, качество кода, UX, формулировки.  
**Сверка с best practices:** Context7 (FastAPI, HTTPX, Boto3, SQLAlchemy, TanStack Query).

---

## Отчёт: таблица проблем

| Файл / Модуль | Критичность | Найденная проблема | Предлагаемое решение | Роль |
|---------------|-------------|--------------------|----------------------|------|
| `backend/app/api/v1/routes/shipping.py` (upload_supply_barcode, upload_box_barcodes) | High | Валидация только по `Content-Type`; клиент может подсунуть исполняемый файл под видом PDF/картинки. Нет проверки magic bytes. | Добавить проверку по сигнатурам (PDF: `%PDF`, JPEG/PNG/GIF/WebP по заголовкам). Ограничить типы по содержимому. | Security Auditor |
| `backend/app/api/v1/routes/orders.py` (upload_order_photo) | High | Только `content_type.startswith("image/")`; нет проверки по magic bytes. PIL `Image.open()` без лимита пикселей — риск decompression bomb (DoS). | Валидация по magic bytes для изображений; установить `Image.MAX_IMAGE_PIXELS` или проверять размер после open. | Security Auditor |
| `backend/app/api/v1/routes/products.py` (upload_product_photo) | High | Аналогично orders: только Content-Type, PIL без лимита пикселей, в ключе S3 используется несанитизированный `file.filename`. | То же: magic bytes + лимит пикселей; санитизировать имя файла в ключе (как в contract_template_service). | Security Auditor |
| `backend/app/api/v1/routes/shipping.py` (upload_*) | Med | В S3-ключ подставляется `file.filename` без санитизации — возможны path traversal или некорректные символы. | Использовать санитизацию имени (например `_sanitize_filename` из contract_template_service или uuid + расширение). | Security Auditor |
| `backend/app/api/v1/routes/services.py` (import_services) | Med | Нет проверки размера файла до `file.read()` — большой Excel может вызвать DoS по памяти. | Проверять `Content-Length` до чтения или читать с лимитом; после read проверять `len(file_bytes) <= MAX_UPLOAD_SIZE_BYTES`. | Security Auditor |
| `backend/app/services/wb_api.py`, `ozon_api.py` | Med | Новый `httpx.AsyncClient` на каждый запрос — нет переиспользования соединений (Context7 рекомендует один client с timeout и limits). | Ввести общий AsyncClient (например в lifespan или зависимость) с timeout и при необходимости Limits; не создавать client в каждом методе. | Tech Lead / Docs Compliance |
| `backend/app/services/wb_api.py`, `ozon_api.py` | Med | Широкий `except Exception` — теряются типы ошибок (HTTPStatusError, TimeoutException), сложнее мониторинг и ретраи. | Ловить `httpx.HTTPStatusError`, `httpx.TimeoutException`, `httpx.RequestError`; логировать тип; при 5xx/таймауте опционально retry. | Tech Lead / Error Handling |
| `backend/app/api/v1/routes/fbo.py` (create_fbo_supply) | Med | При WB/Ozon с box_count > 0 без API-ключей создаётся поставка со статусом draft без сообщения пользователю — «тихий» сбой. | Если marketplace in (wb, ozon) и (box_count > 0 или ozon), проверять ключи до создания; при отсутствии возвращать 400 с текстом «Укажите API-ключи WB/Ozon в настройках компании». | CEO / Product Owner |
| `backend/app/api/v1/routes/orders.py` (upload_order_photo) | Low | Сообщение об ошибке на английском: «Upload verification failed». | Заменить на: «Не удалось проверить загрузку файла. Попробуйте ещё раз.» | SMM / Brand Voice |
| `backend/app/api/v1/routes/admin.py` (download) | Low | «Template or file not found» — английский в русскоязычном продукте. | Заменить на: «Шаблон или файл не найден». | SMM / Brand Voice |
| `frontend/src/services/api.ts` | Low | Fallback при ошибке: «API error: ${response.status}» — технический текст может показываться пользователю при 500 без body. | Использовать нейтральное сообщение, например: «Что-то пошло не так. Попробуйте позже.» при отсутствии data.detail. | SMM / Brand Voice |
| `backend/app/api/v1/routes/fbo.py` | Low | «marketplace должен быть wb или ozon» — формулировка для разработчика. | Для API оставить; в UI не показывать сырой detail или заменить на: «Укажите маркетплейс: WB или Ozon». | UX / Wording |
| `frontend` (useShipping, useFBOSupplies) | Low | Мутации без глобального onError; ошибки обрабатываются в компонентах. Unhandled rejection маловероятен, но при отсутствии catch в UI возможен необработанный promise. | Убедиться, что все вызовы mutateAsync обёрнуты в try/catch (уже так в ShippingPage и др.); при желании — общий onError в QueryClient. | Tech Lead / Error Handling |
| `backend/app/services/s3.py` | Low | S3: put_object используется (non-chunked) — соответствует .cursorrules. HEAD check с новым AsyncClient на каждый вызов. | Без изменений по chunked; при росте нагрузки рассмотреть общий httpx client для head_check. | CEO / Cost Efficiency |
| Масштабируемость (БД, воркеры) | Med | При 10k пользователей узкие места: один инстанс приложения, пул БД по умолчанию, синхронные тяжёлые операции (LibreOffice, PIL) в потоке. | Тяжёлые операции уже вынесены в asyncio.to_thread (admin upload); рассмотреть лимит одновременных конвертаций и пул БД. | CEO / Scalability |
| RAG documents (admin) | Med | Загрузка DOCX/TXT/RTF по расширению без проверки magic bytes — бинарный файл под видом .txt может привести к ошибке парсинга. | Добавить проверку содержимого (UTF-8 для TXT, сигнатуры для DOCX/RTF) и возвращать понятную ошибку. | Security Auditor |

---

## Итоговая оценка готовности

**Оценка: 72%**

- **Архитектура и безопасность:** Контроль доступа и шифрование ключей на месте; валидация загрузок частичная (шаблоны — хорошо, фото/ШК — только Content-Type, без magic bytes и лимита изображений). Риск RCE низкий при текущих типах, но подмена типа файла и DoS по картинкам — реальны.
- **Соответствие best practices:** FastAPI и S3 используются корректно; HTTPX — без переиспользования client; ошибки в API-клиентах обрабатываются широко. Документация (Context7) рекомендует один client с timeout и явную обработку HTTPStatusError/Timeout.
- **Бизнес и масштаб:** Логика WB/Ozon и FBO соответствует целям; при отсутствии ключей возможен «тихий» draft. Масштаб на 10k пользователей потребует внимания к пулу БД и тяжёлым операциям.
- **UX и тексты:** Большинство сообщений на русском и по делу; есть английские фразы («Upload verification failed», «Template or file not found», fallback «API error: N»). Потоки создания отгрузки и FBO понятны; обратная связь при ошибках есть.

---

## ТОП‑3 приоритетных задач

1. **Валидация загрузок файлов (безопасность)**  
   Для всех эндпоинтов загрузки (фото заказа/товара, ШК поставки/коробов): проверка по magic bytes, а не только по Content-Type; для изображений — лимит размера/пикселей (PIL) против decompression bomb. Санитизация имени файла в S3-ключе.

2. **Сервисы WB/Ozon: один HTTP‑клиент и явные ошибки**  
   Переиспользовать один `httpx.AsyncClient` (timeout, при необходимости limits) вместо создания в каждом запросе; различать и логировать HTTPStatusError, TimeoutException, RequestError; при необходимости — retry по 5xx/таймауту.

3. **Единообразие сообщений и UX при ошибках**  
   Заменить английские тексты на русские («Upload verification failed» → «Не удалось проверить загрузку файла…», «Template or file not found» → «Шаблон или файл не найден»). В api.ts при отсутствии `data.detail` показывать нейтральное сообщение вместо «API error: N». В FBO: при создании поставки WB/Ozon с box_count > 0 без ключей возвращать 400 с явной просьбой указать API-ключи.
