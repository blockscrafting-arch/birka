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
3. Запустить:
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
