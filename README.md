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

1. Установить Docker + Docker Compose на VPS.
2. Скопировать проект на сервер.
3. Заполнить `.env` (Postgres, S3, OpenAI).
4. Запустить:
   ```bash
   docker compose -f docker-compose.prod.yml up --build -d
   ```
5. Убедиться, что `nginx` проксирует `/api/` на backend.

## Важные настройки

- В nginx задан `client_max_body_size 20M`.
- S3 загрузка non-chunked.
- URL к файлам строится централизованно на бэке.
