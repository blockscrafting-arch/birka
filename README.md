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

### Вручную

1. На VPS: установить Docker и Docker Compose, клонировать репозиторий в каталог деплоя (например `/opt/birka`).
2. В каталоге проекта создать `.env` (Postgres, S3, OpenAI, Telegram и т.д.).
3. Запустить (без `--no-cache`, чтобы не забивать диск):
   ```bash
   docker compose -f docker-compose.prod.yml up --build -d
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
