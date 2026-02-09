# План атаки: устранение всех замечаний AUDIT_DEEP_4ROLES

## Цель этапа
Повысить безопасность загрузок, надёжность интеграций WB/Ozon и качество пользовательских сообщений без изменения бизнес‑логики и версий зависимостей.

## Технический стек (Confirmed via Context7 and research)
- FastAPI 0.115.8 — серверная валидация содержимого и лимиты.
- HTTPX 0.27.2 — общий AsyncClient, timeouts/limits, HTTPStatusError/Timeout.
- Boto3 1.35.25 — put_object (non-chunked).
- SQLAlchemy 2.0.36 — pooled engine.
- TanStack Query 5.59.0 — onError/try-catch на mutation.
- Pillow 10.4.0 — Image.verify(), лимит пикселей.

## Пошаговый план (Execution Checklist)
- [ ] Step 1: Зафиксировать план в `.cursor/plan.md`
  - *Context:* Синхронизировать утверждённый план в проектный файл.
  - *Files:* `.cursor/plan.md`
  - *Validation:* Файл существует, структура соответствует секциям.

- [ ] Step 2: Общий HTTPX клиент для внешних API
  - *Context:* Один AsyncClient с timeout/limits, закрытие в lifespan.
  - *Files:* `backend/app/main.py`, `backend/app/core/*`, `wb_api.py`, `ozon_api.py`, `s3.py`.
  - *Validation:* health check, запросы к WB/Ozon и HEAD S3 без ошибок.

- [ ] Step 3: Библиотека валидации файлов и санитизация имён
  - *Context:* Единый helper magic bytes + безопасное имя файла.
  - *Files:* `backend/app/services/files.py` или `upload_validation.py`, `shipping.py`, `orders.py`, `products.py`.
  - *Validation:* Отклонение файлов с неверной сигнатурой.

- [ ] Step 4: Безопасная обработка изображений
  - *Context:* Лимит пикселей, verify/load (Pillow).
  - *Files:* `orders.py`, `products.py`.
  - *Validation:* Большое изображение → 400; обычные фото проходят.

- [ ] Step 5: Валидация документов RAG
  - *Context:* Сигнатуры DOCX/RTF, UTF-8 для TXT.
  - *Files:* `admin.py`, `document_processor.py`, helper из Step 3.
  - *Validation:* Неверный файл → 400; валидные проходят.

- [ ] Step 6: Корректная проверка ключей WB/Ozon при создании FBO
  - *Context:* При WB/Ozon и авто-создании без ключей — 400.
  - *Files:* `fbo.py`.
  - *Validation:* Без ключей → 400; с ключами → external_supply_id.

- [ ] Step 7: Лимит размера для импорта услуг
  - *Context:* DoS-защита для import_services.
  - *Files:* `services.py`.
  - *Validation:* Большой файл → 413/400.

- [ ] Step 8: UX/Copy исправления
  - *Context:* Русские тексты, нейтральный fallback вместо «API error: N».
  - *Files:* `orders.py`, `admin.py`, `frontend/src/services/api.ts`.
  - *Validation:* Ошибки на русском; fallback нейтральный.

- [ ] Step 9: Тесты и контроль качества
  - *Context:* Тесты загрузок и сценариев.
  - *Files:* `backend/tests/*`.
  - *Validation:* pytest по upload/валидации.

## Риски и нюансы
- Проверка сигнатур может отклонять нестандартные файлы (Excel, WebP).
- Санитизация имён меняет ключи S3 только для новых загрузок.
- HTTPX клиент нужно корректно закрывать в lifespan.
- Лимит пикселей Pillow — подобрать разумный порог.
- Версии зависимостей не обновляем.
