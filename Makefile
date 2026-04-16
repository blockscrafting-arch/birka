# Команды для проверки готовности к прод-тесту (см. docs/PROD_TEST_READINESS.md)

.PHONY: test-backend test-frontend build-frontend health check-readiness

# Backend: тесты (требует venv с зависимостями или запуск в Docker)
test-backend:
	cd backend && python3 -m pytest tests/ -v --tb=short

# Frontend: линт и тесты
test-frontend:
	cd frontend && npm run lint && npm test -- --run

# Frontend: сборка (как в CI)
build-frontend:
	cd frontend && npm run build

# Health-check бэкенда (URL по умолчанию — локальный; для прода задайте BASE_URL)
BASE_URL ?= http://localhost:8000
health:
	@echo "Проверка $(BASE_URL)/health ..."
	@curl -sf "$(BASE_URL)/health" | head -1

# Краткая проверка: тесты бэка + сборка фронта (ориентир — CI)
check-readiness: test-backend build-frontend
	@echo "Backend тесты и frontend сборка завершены. Проверьте health и чек-лист в docs/PROD_TEST_READINESS.md"
