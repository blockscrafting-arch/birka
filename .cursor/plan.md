# План устранения аудита (поэтапно)

## Цель этапа

Снизить риски безопасности и деградации производительности, обеспечить масштабирование и предсказуемый UX перед ростом нагрузки.

## Технический стек (Confirmed via Context7 and research)

Примечание: Context7 недоступен в текущем окружении, поэтому версии и best practices сверены через открытые источники. При подтверждении плана выполню повторную валидацию через Context7.

- FastAPI — актуальная версия 0.128.5 (PyPI, февраль 2026)
- SQLAlchemy — ветка 2.0.x (актуальная документация 2.0/2.1)
- Redis-py — async API `redis.asyncio` (redis-py 5.x)
- S3 SDK — рекомендован aioboto3 для async‑I/O
- OpenAI Python SDK — рекомендован `AsyncOpenAI` для async‑I/O
- LibreOffice headless — best practice: изоляция/песочница
- Nginx — долгий кэш для hashed‑ассетов, минимальный для `index.html`
- Yandex Metrika — CSP allowlist для `mc.yandex.ru` и Webvisor доменов
- Telegram WebApp — server‑side HMAC валидация initData

## Пошаговый план (Execution Checklist)

- Step 1: Изоляция конвертаций документов (LibreOffice)
  - *Context:* Убрать риск RCE/DoS при обработке RTF/DOCX, вынести конвертацию из web‑процесса.
  - *Files:* [backend/app/services/contract_template_service.py](backend/app/services/contract_template_service.py), [backend/app/api/v1/routes/companies.py](backend/app/api/v1/routes/companies.py), Docker/worker config.
  - *Validation:* Загрузить RTF/DOCX → успешная конвертация; проверить, что воркер изолирован (UID, лимиты, no‑network).
  - *Context7 Check:* LibreOffice headless security + Celery worker security.
- Step 2: Убрать блокирующие I/O из async‑эндпоинтов (S3)
  - *Context:* `boto3` синхронный, блокирует event loop при 10k пользователей.
  - *Files:* [backend/app/services/s3.py](backend/app/services/s3.py), upload‑эндпоинты в [backend/app/api/v1/routes/](backend/app/api/v1/routes/).
  - *Validation:* Нагрузочный тест (параллельные загрузки), p95 latency не деградирует.
  - *Context7 Check:* aioboto3 usage patterns + async client lifecycle.
- Step 3: Асинхронный OpenAI и батчинг эмбеддингов
  - *Context:* В `rag.py` используется синхронный клиент, что блокирует event loop.
  - *Files:* [backend/app/services/rag.py](backend/app/services/rag.py).
  - *Validation:* Параллельные запросы не блокируют API; лог latency стабильный.
  - *Context7 Check:* OpenAI Python SDK async (`AsyncOpenAI`).
- Step 4: Single‑instance scheduler
  - *Context:* `run_shipment_scheduler` запускается в каждом воркере Uvicorn.
  - *Files:* [backend/app/services/shipment_scheduler.py](backend/app/services/shipment_scheduler.py), [backend/app/main.py](backend/app/main.py).
  - *Validation:* В режиме нескольких воркеров выполняется один scheduler (distributed lock/отдельный процесс).
  - *Context7 Check:* best practices single‑instance scheduler для FastAPI.
- Step 5: Пагинация админ‑пользователей
  - *Context:* `/admin/users` отдает весь список без лимитов → деградация при росте.
  - *Files:* [backend/app/api/v1/routes/admin.py](backend/app/api/v1/routes/admin.py), [frontend/src/pages/admin/UsersPage.tsx](frontend/src/pages/admin/UsersPage.tsx), hooks в `frontend/src/hooks/`.
  - *Validation:* Запрос с `page/limit` возвращает правильные страницы; UI показывает пагинацию.
- Step 6: UX‑feedback для ошибок и оффлайна
  - *Context:* Нет явной оффлайн‑индикации, часть ошибок на EN.
  - *Files:* [frontend/src/services/api.ts](frontend/src/services/api.ts) + UI компоненты.
  - *Validation:* Имитация offline → явное сообщение + retry; ошибки всегда на RU.
- Step 7: CSP и Метрика
  - *Context:* CSP должен разрешать домены Метрики и Webvisor согласно CSP‑гайдам.
  - *Files:* [docker/nginx.conf](docker/nginx.conf), [frontend/src/analytics.ts](frontend/src/analytics.ts).
  - *Validation:* Метрика грузится без CSP‑ошибок в консоли, Webvisor работает.
  - *Context7 Check:* CSP‑рекомендации Яндекс.Метрики.
- Step 8: Синхронизация плана
  - *Context:* По требованию — сохранить финальный план в `.cursor/plan.md`.
  - *Files:* [.cursor/plan.md](.cursor/plan.md).
  - *Validation:* Файл соответствует утверждённому плану.

## Риски и нюансы

- LibreOffice конвертация небезопасна без песочницы — критический риск.
- aioboto3 и AsyncOpenAI требуют корректного lifecycle (закрытие клиентов, таймауты).
- Redis‑lock для scheduler должен быть отказоустойчивым (TTL + renew).
- CSP для Метрики требует расширенных доменов Webvisor (возможны блокировки без точного allowlist).
- Пагинация может потребовать индексы по `created_at`/`telegram_id`.

---

Примечание: после утверждения плана я обновлю `.cursor/plan.md` этим содержимым и только затем приступлю к реализации.
