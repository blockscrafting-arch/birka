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
echo "=== 2.5. Бэкап БД перед миграциями ==="
mkdir -p "$ROOT/backups"
# shellcheck source=/dev/null
source "$ROOT/.env"
PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump \
  -h "${POSTGRES_HOST:-localhost}" \
  -U "${POSTGRES_USER:-birka}" \
  "${POSTGRES_DB:-birka}" \
  | gzip > "$ROOT/backups/pre-migration-$(date +%Y%m%d_%H%M%S).sql.gz" \
  && echo "Бэкап сохранён в backups/" \
  || echo "ПРЕДУПРЕЖДЕНИЕ: pg_dump завершился с ошибкой (pg_dump может не быть установлен локально)"

echo ""
echo "=== 3. Миграции БД ==="
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

echo ""
echo "=== 4. Health check ==="
for i in 1 2 3 4 5; do
  if curl -sf http://localhost/health > /dev/null 2>&1; then
    echo "Сервис здоров."
    break
  fi
  if [ "$i" -eq 5 ]; then
    echo "ОШИБКА: health check не прошёл после 5 попыток!"
    exit 1
  fi
  echo "Ожидание... (попытка $i/5)"
  sleep 5
done

echo ""
echo "=== Готово. Проверка: docker compose -f docker-compose.prod.yml ps ==="
docker compose -f docker-compose.prod.yml ps
