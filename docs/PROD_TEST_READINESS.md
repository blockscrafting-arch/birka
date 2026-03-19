# Готовность к ограниченному прод-тесту для клиента

Перед выдачей клиенту доступа к production выполните этот чек-лист. Если пункты не выполняются — тестируйте на отдельном staging.

---

## 1. Прод-настройки и секреты

### Переменные окружения

- [ ] Файл `.env` не коммитить в git. При сомнении: `git log --all -- .env`; при утечке — [DEPLOYMENT.md](DEPLOYMENT.md), раздел «Если .env попал в git».
- [ ] Сверить `.env` с [.env.example](../.env.example) и [docs/DEPLOYMENT.md](DEPLOYMENT.md):
  - `ENVIRONMENT=production`
  - `CORS_ORIGINS` — явный список доменов (например `https://ffbirka.ru`), **не** `*`
  - `POSTGRES_DSN` — корректная строка к внешней БД (Beget Cloud Database)
  - `REDIS_DSN=redis://redis:6379/0` для docker-compose.prod (можно задать в .env; в compose для celery_worker и celery_beat уже переопределено через `environment`, см. [docker-compose.prod.yml](../docker-compose.prod.yml))
  - `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_IDS` заданы
  - `ENCRYPTION_KEY` (Fernet, сгенерирован и не в репозитории)
  - S3: `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET_NAME`, `FILE_PUBLIC_BASE_URL`
  - AI: `OPENAI_API_KEY` или `OPENROUTER_API_KEY`, `AI_PROVIDER`, `AI_MODEL`
  - При сборке фронта: `VITE_YM_COUNTER_ID` (если нужна аналитика)

### Docker и Nginx

- [ ] [docker-compose.prod.yml](../docker-compose.prod.yml) — все сервисы (backend, frontend, nginx, redis, celery_worker, celery_beat) собираются и поднимаются без ошибок.
- [ ] [docker/nginx.conf](../docker/nginx.conf): `client_max_body_size 50M` задан в блоках `server` (для загрузки файлов).
- [ ] CORS в production: в коде проверяется запрет `CORS_ORIGINS=*` при `ENVIRONMENT=production` ([backend/app/main.py](../backend/app/main.py), [backend/app/core/config.py](../backend/app/core/config.py)).

### Внешние ключи и лимиты

- [ ] Лимит загрузки: при необходимости задан `MAX_UPLOAD_SIZE_BYTES` в .env; значение не превышает nginx `client_max_body_size`.
- [ ] WB/Ozon: для теста клиента использовать тестовые API-ключи компании, не боевые без согласования.

---

## 2. Автоматика и health-check

- [ ] Backend: `cd backend && pytest tests/ -v` — тесты проходят (локально или в CI). Рекомендуется ориентироваться на зелёный статус GitHub Actions.
- [ ] Frontend: `cd frontend && npm run build` — сборка без ошибок; при необходимости `npm run lint` и `npm test`.
- [ ] CI: [.github/workflows/ci.yml](../.github/workflows/ci.yml) — зелёный статус на текущем main (или ветке деплоя).
- [ ] Health: `GET /health` возвращает `{"status": "ok", "db": "connected"}`. После деплоя: `curl -s https://ffbirka.ru/health` (в nginx проброшен `location = /health`) или через внутренний URL бэкенда (например `curl http://backend:8000/health` из хоста с доступом к контейнеру).

---

## 3. Ручной smoke по критическим сценариям

Используйте [docs/CHECKLIST_VERIFICATION.md](CHECKLIST_VERIFICATION.md) и дополнительно:

- [ ] Приёмка / упаковка / отгрузка и **печать этикеток** (PDF, читаемость ШК на целевом принтере).
- [ ] **Приёмка:** пошаговая по товарам, фото брака по числу единиц брака; частичная приёмка (осталось N) и полная (статус «Принято»).
- [ ] **Упаковка:** кнопки «Добавить товар», «Дублировать», «Удалить» по строкам; завершение заказа при полной упаковке.
- [ ] **Заявки:** импорт Excel (шаблон, загрузка), экспорт заявки в Excel и отправка в Telegram.
- [ ] **Загрузка фото браков** — файл доступен после загрузки (HEAD-проверка на бэке, см. тесты в [backend/tests/test_s3_head.py](../backend/tests/test_s3_head.py)).
- [ ] **WB/Ozon** — только тестовые ключи: создание поставки, синхронизация, импорт ШК (если сценарий включён в тест).

---

## 4. Ограниченный доступ для клиента

- [ ] Создана тестовая компания и/или пользователи с **минимальными правами** (см. [docs/CLIENT_TEST_ACCESS.md](CLIENT_TEST_ACCESS.md)).
- [ ] Проверены сценарии изоляции и авторизации: [backend/tests/test_auth.py](../backend/tests/test_auth.py), [backend/tests/test_security.py](../backend/tests/test_security.py), [backend/tests/test_companies.py](../backend/tests/test_companies.py) — тесты проходят.

---

## 5. Протокол теста

- [ ] Зафиксированы: список сценариев для клиента, тестовые данные, окно времени, контакты для репортинга (см. [docs/CLIENT_TEST_PROTOCOL.md](CLIENT_TEST_PROTOCOL.md)).
- [ ] Логирование: ошибки логируются без ПДн; при необходимости включён режим отладки только для тестовой компании.
- [ ] План отката при критических инцидентах: отзыв доступа, откат деплоя при необходимости — описан в протоколе.

---

После прохождения всех пунктов доступ в прод для клиента на тест считается допустимым.
