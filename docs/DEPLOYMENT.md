# Развёртывание

## Инфраструктура

- **VPS Beget**, Nginx (reverse proxy), Docker (при использовании контейнеров).
- Frontend — статика (сборка Vite); отдача через Nginx или из контейнера.
- Backend — FastAPI (uvicorn/gunicorn) за Nginx.

## Секреты и конфигурация

- Все секреты и чувствительные параметры — в **переменных окружения** (env), не в репозитории.
- **Файл `.env` не коммитить в git.** Он указан в `.gitignore`. При клонировании репозитория копировать только `.env.example` в `.env` и заполнять значения локально. На общих или публичных машинах не хранить реальный `.env` в корне репо.
- **Проверка истории:** при сомнении выполнить `git log --all -- .env`. Если в выводе есть коммиты — файл когда-то попадал в репозиторий; тогда считать ключи скомпрометированными и выполнить действия из раздела ниже «Если .env попал в git».
- Примеры переменных: `POSTGRES_DSN`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `AI_PROVIDER`, `AI_MODEL`, `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_IDS`, `S3_*`, `DADATA_TOKEN`, `ENCRYPTION_KEY`, `SHIPMENT_SCHEDULER_INTERVAL_SECONDS` (интервал проверки просроченных отгрузок, по умолчанию 600 сек). Опционально: `DOCS_RAG_PATH` — путь к папке с RAG-документами (по умолчанию `/app/docs/rag`). Fernet для API-ключей: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
- **Production:** задать `ENVIRONMENT=production`, `CORS_ORIGINS` — явный список доменов (например `https://ffbirka.ru`), `REDIS_DSN=redis://redis:6379/0` при использовании docker-compose.prod (Redis, Celery worker/beat). REDIS_DSN можно задать в `.env` либо переопределить в самом compose (секция `environment` у сервисов celery_worker и celery_beat), чтобы не зависеть от дубликатов в .env. Для сборки фронта с аналитикой передать `VITE_YM_COUNTER_ID` (номер счётчика Яндекс.Метрики).

### Если .env попал в git

Если проверка `git log --all -- .env` показала, что файл когда-либо коммитился, считать все перечисленные ниже ключи скомпрометированными и **обязательно ротировать**:

- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBAPP_SECRET`
- `OPENAI_API_KEY`, `OPENROUTER_API_KEY`
- `S3_ACCESS_KEY`, `S3_SECRET_KEY`
- `DADATA_TOKEN`
- `ENCRYPTION_KEY` (после смены — перешифровать API-ключи компаний в БД, см. подраздел «Ротация ENCRYPTION_KEY» ниже)

После ротации при необходимости удалить файл из истории (например, `git filter-repo --path .env --invert-paths`), сделав бэкап репо и уведомив разработчиков. Для публичных репозиториев запросить удаление кэшированных версий у хостинга (GitHub/GitLab sensitive data removal).

### Ротация ENCRYPTION_KEY

При смене ключа шифрования нужно перешифровать уже сохранённые API-ключи в БД:

1. Сгенерировать новый ключ: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
2. Задать в окружении `OLD_ENCRYPTION_KEY` (текущий) и `NEW_ENCRYPTION_KEY` (новый).
3. Выполнить скрипт: `cd backend && python -m scripts.rotate_encryption_key` (или через Docker: `docker compose -f docker-compose.prod.yml exec backend python -m scripts.rotate_encryption_key`).
4. Заменить в .env значение `ENCRYPTION_KEY` на новый ключ и перезапустить приложение.

Подробности — в docstring скрипта `backend/scripts/rotate_encryption_key.py`.

## Nginx

- Для маршрутов загрузки файлов обязательно задать **client_max_body_size** (соответствовать лимиту бэкенда, например 10 MB).

## База данных

- Перед запуском приложения применить миграции Alembic к PostgreSQL.
- Миграция `0008_document_chunks` требует расширения **pgvector** в PostgreSQL (RAG/эмбеддинги). Убедитесь, что ваша БД его поддерживает (Beget Cloud Database или образ с установленным pgvector). Локально с обычным `postgres:15` миграция упадёт — используйте образ с pgvector или БД без этой миграции, если RAG не нужен.

## Команды деплоя (из корня репозитория)

Все команды выполнять из **корня проекта** (`/opt/birka` или ваш путь к репозиторию), не из `frontend/` или `backend/`.

```bash
# 1. Перейти в корень проекта
cd /opt/birka

# 2. Подтянуть код
git pull origin main

# 3. Сборка фронтенда (опционально, если не используете Docker для фронта)
cd frontend && npm run build && cd ..

# 4. Собрать и запустить контейнеры
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d --remove-orphans

# 5. Применить миграции БД
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

Флаг `--remove-orphans` убирает контейнеры, которых нет в текущем compose-файле (например, `db` и `redis` из dev — на проде используется внешняя БД). Если предупреждение «Found orphan containers» не мешает, можно не использовать флаг.

**Важно:** после `git pull` обязательно выполнять `build --no-cache` и `up -d`, чтобы контейнеры (backend, celery_worker, celery_beat) поднялись с новым кодом и актуальной конфигурацией из compose (в т.ч. REDIS_DSN для Celery).

Если бэкенд **не в Docker** (запуск напрямую на VPS):

```bash
cd /opt/birka/backend
alembic upgrade head
```

## Ручная проверка после деплоя

- **Логи Celery:** `docker compose -f docker-compose.prod.yml logs celery_worker --tail 50` — в выводе должна быть строка `Connected to redis://redis:6379/0` и `celery@... ready.` Если видите `Connection refused` к localhost:6379 — пересоберите и перезапустите контейнеры (см. команды деплоя выше).
- **Завершение заказа:** убедиться, что `POST /api/v1/warehouse/order/{id}/complete` (с заголовками warehouse или admin) возвращает 200 и заказ переходит в статус «Завершено» (проверка по API или через UI).
- Рекомендуется также выполнить:

- **Печать этикеток** — проверка на целевом принтере (формат, читаемость ШК).
- **Сканер** — на реальном устройстве: камера, звук/вибрация при сканировании, страницы приёмки/упаковки и отдельная страница сканера.
- **WB/Ozon** — создание поставки, синхронизация и импорт ШК с реальными API-ключами компании.

## Рекомендации по ОС (опционально)

- **Redis:** при предупреждении в логах «Memory overcommit must be enabled» на хосте выполнить `sysctl vm.overcommit_memory=1`. Для постоянной настройки добавить в `/etc/sysctl.conf` строку `vm.overcommit_memory = 1`, затем `sysctl -p` или перезагрузка. Без этого при нехватке памяти Redis может вести себя нестабильно (background save, репликация).
