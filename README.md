# Бирка — Telegram Mini App

## Быстрый старт (локально)

1. Создать `.env` на основе переменных из `backend/app/core/config.py`.
2. Запустить:
   ```bash
   docker compose up --build
   ```
3. Backend: `http://localhost:8000`
4. Frontend: `http://localhost:5173`

## Деплой на Beget VPS

### Работа прямо на сервере

Если правишь код прямо на сервере (SSH, Cursor на сервере и т.п.), **git и GitHub Actions не нужны**. После правок пересобери и перезапусти контейнеры:

```bash
cd /opt/birka   # или твой каталог проекта
export BUILD_TIMESTAMP=$(date +%s)
docker compose -f docker-compose.prod.yml build --build-arg BUILD_TIMESTAMP=$BUILD_TIMESTAMP
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

Миграции БД (если менял модели):

```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

Git на сервере можно использовать только для истории и бэкапа (при желании пушить в GitHub). Деплой через Actions нужен только если разрабатываешь в другом месте и хочешь по `git push` обновлять сервер.

### Вручную (первый раз или после клонирования)

1. На VPS: установить Docker и Docker Compose, скопировать или клонировать проект в каталог (например `/opt/birka`).
2. В каталоге проекта создать `.env` (Postgres, S3, OpenAI, Telegram и т.д.).
3. Запустить (фронт пересоберётся за счёт `BUILD_TIMESTAMP`):
   ```bash
   export BUILD_TIMESTAMP=$(date +%s)
   docker compose -f docker-compose.prod.yml build --build-arg BUILD_TIMESTAMP=$BUILD_TIMESTAMP
   docker compose -f docker-compose.prod.yml up -d --force-recreate
   ```
4. Nginx проксирует `/` на frontend, `/api/` на backend. Для HTTPS настроить certbot и пути к сертификатам в `docker/nginx.conf`.

### Автодеплой через GitHub Actions

При пуше в `main` (или по кнопке «Run workflow») workflow подключается по SSH к VPS и обновляет код и контейнеры.

**Секреты репозитория (Settings → Secrets and variables → Actions):**

| Секрет | Описание |
|--------|----------|
| `SSH_HOST` | IP или домен VPS |
| `SSH_USER` | Пользователь для SSH |
| `SSH_PRIVATE_KEY` | Приватный SSH-ключ (содержимое файла, без пароля) |
| `DEPLOY_PATH` | Каталог с клоном репозитория на сервере, например `/opt/birka` |

На сервере должны быть установлены Docker, Docker Compose и Git; репозиторий уже склонирован в `DEPLOY_PATH`, `.env` создан.

В каждом деплое передаётся `BUILD_TIMESTAMP`, чтобы фронт всегда пересобирался; после поднятия контейнеров выполняется `up -d --force-recreate`.

### Почему в проде всё ещё старое приложение

1. **Проверить GitHub Actions** — вкладка Actions в репозитории: workflow **Deploy** должен был запуститься после пуша в `main`. Если он не запускался или упал с ошибкой (SSH, путь, сборка), на сервере ничего не обновилось.
2. **Кэш браузера / Telegram** — открыть сайт в режиме инкогнито или «Другая вкладка» в Telegram; при необходимости закрыть и заново открыть Mini App.
3. **На сервере вручную** — зайти по SSH и выполнить:
   ```bash
   cd "$DEPLOY_PATH"   # например /opt/birka
   git fetch origin && git status   # должен быть на main
   docker compose -f docker-compose.prod.yml ps   # контейнеры Up
   docker compose -f docker-compose.prod.yml logs frontend --tail 5
   ```
   Если код старый — `git pull` или `git reset --hard origin/main`, затем пересобрать и поднять контейнеры (см. раздел «Деплой вручную»).

## Важные настройки

- В nginx задан `client_max_body_size 20M`.
- S3 загрузка non-chunked.
- URL к файлам строится централизованно на бэке.

## 502 Bad Gateway

Если nginx отдаёт 502, он не достучался до backend или frontend. На VPS выполнить:

```bash
cd /opt/birka   # или ваш DEPLOY_PATH
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs backend --tail 50
docker compose -f docker-compose.prod.yml logs frontend --tail 20
```

- Контейнеры `backend` и `frontend` должны быть в статусе `Up`. Если `Exit` — смотреть логи.
- Частая причина падения backend: нет `.env` или неверный `POSTGRES_DSN`. Проверить наличие `.env` в каталоге проекта.
- После правок: `docker compose -f docker-compose.prod.yml up -d` и при необходимости перезапустить nginx.

## Место на диске VPS

Docker копит образы и кэш сборки. Чтобы освободить место:

```bash
# Удалить неиспользуемые образы и кэш сборки (оставить ~512MB кэша)
docker image prune -a -f
docker builder prune -f --keep-storage 512MB

# Или жёстко: всё неиспользуемое
docker system prune -a -f
```

На VPS лучше **не** использовать `build --no-cache`: обычный `build` переиспользует слои и занимает меньше места. В деплой-воркфлоу после сборки уже добавлен лёгкий prune.

## Просмотр логов

```bash
# Все логи в реальном времени
docker compose -f docker-compose.prod.yml logs -f

# Только backend
docker compose -f docker-compose.prod.yml logs -f backend

# Последние 100 строк backend
docker compose -f docker-compose.prod.yml logs --tail 100 backend

# Логи Nginx
docker compose -f docker-compose.prod.yml logs -f nginx

# Логи с временными метками
docker compose -f docker-compose.prod.yml logs -t backend
```
