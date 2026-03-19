#!/bin/bash
# Деплой на production (из корня репозитория).
# Использование: ./scripts/deploy-prod.sh
# Или из корня: bash scripts/deploy-prod.sh

set -e
cd "$(dirname "$0")/.."
ROOT="$PWD"

echo "=== Корень проекта: $ROOT ==="
if [ ! -f "docker-compose.prod.yml" ]; then
  echo "Ошибка: docker-compose.prod.yml не найден. Запускайте из корня: cd /opt/birka && bash scripts/deploy-prod.sh"
  exit 1
fi

echo ""
echo "=== 1. Сборка образов (это может занять несколько минут) ==="
docker compose -f docker-compose.prod.yml build --no-cache

echo ""
echo "=== 2. Запуск контейнеров ==="
docker compose -f docker-compose.prod.yml up -d --remove-orphans

echo ""
echo "=== 3. Миграции БД ==="
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

echo ""
echo "=== Готово. Проверка: docker compose -f docker-compose.prod.yml ps ==="
docker compose -f docker-compose.prod.yml ps
