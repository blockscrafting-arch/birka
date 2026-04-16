# Действия после анализа логов (OOM и безопасность)

## 1. Ограничить память у контейнеров (главное)

**Статус:** лимиты уже заданы в `docker-compose.prod.yml` (redis 256M, backend 512M, celery_worker 512M, celery_beat 128M, frontend 256M, nginx 128M) под сервер 3/4 (4 ГБ RAM). После `docker compose up` проверьте применение: `docker stats --no-stream`; если лимиты не применились (standalone Compose может игнорировать `deploy`), используйте `docker compose --compatibility` или см. документацию Docker.

Чтобы задать или изменить лимиты вручную:

```yaml
# Пример для сервисов — добавьте deploy.resources в каждый сервис:

  backend:
    # ... существующая конфигурация ...
    deploy:
      resources:
        limits:
          memory: 512M

  frontend:
    deploy:
      resources:
        limits:
          memory: 256M

  redis:
    deploy:
      resources:
        limits:
          memory: 256M

  celery_worker:
    deploy:
      resources:
        limits:
          memory: 512M

  celery_beat:
    deploy:
      resources:
        limits:
          memory: 128M

  nginx:
    deploy:
      resources:
        limits:
          memory: 128M
```

Лимиты можно подстроить под реальную нагрузку и объём RAM на VPS. Сборка фронта (`docker compose build`) по-прежнему идёт на хосте — Node при сборке может жрать много памяти; см. п. 2.

## 2. Сборка фронта без OOM

При `docker compose build` этап `npm run build` запускает Node и может потреблять много RAM. Варианты:

- **Собирать по одному образу** и не поднимать тяжёлые сервисы во время сборки:
  ```bash
  docker compose -f docker-compose.prod.yml build frontend --no-cache
  ```
- **Ограничить память Node при сборке** — в `docker/Dockerfile.frontend` перед `RUN npm run build` добавить:
  ```dockerfile
  ENV NODE_OPTIONS="--max-old-space-size=1024"
  ```
  (1024 МБ на процесс сборки; уменьшите, если на VPS меньше 2 ГБ RAM.)

## 3. Redis и overcommit (уже в DEPLOYMENT.md)

Если в логах Redis есть «Memory overcommit must be enabled»:

```bash
sudo sysctl vm.overcommit_memory=1
echo "vm.overcommit_memory = 1" | sudo tee -a /etc/sysctl.conf
```

## 4. SSH: отключить вход по паролю для root

Чтобы уменьшить риск подбора пароля (в логах были успешные входы по паролю с 151.245.139.110):

1. Убедитесь, что вход по ключу с вашего IP работает.
2. В `/etc/ssh/sshd_config` выставить:
   ```
   PasswordAuthentication no
   PermitRootLogin prohibit-password
   ```
3. Перезапустить SSH: `sudo systemctl reload ssh` или `sudo systemctl reload sshd` (на Debian/Ubuntu чаще `ssh`; проверить: `systemctl list-unit-files --type=service | grep -E '^ssh'`).

Проверку делайте из уже открытой сессии, чтобы не потерять доступ.

## 5. Мониторинг памяти

- Раз в день смотреть OOM в журнале:
  ```bash
  journalctl -k -b | grep -i "out of memory"
  ```
- Или за последние сутки:
  ```bash
  journalctl -k --since "24 hours ago" | grep -i "killed process"
  ```

## 6. Файрвол (ufw)

Открыты только 22, 80, 443; остальное закрыто.

1. Проверить: `which ufw`; при отсутствии — `sudo apt-get install -y ufw`.
2. Задать правила (обязательно **до** `ufw enable`):  
   `sudo ufw default deny incoming`  
   `sudo ufw default allow outgoing`  
   `sudo ufw allow 22/tcp comment 'SSH'`  
   `sudo ufw allow 80/tcp comment 'HTTP'`  
   `sudo ufw allow 443/tcp comment 'HTTPS'`
3. Включить: `sudo ufw enable` (ответить `y`). Убедиться, что текущая SSH-сессия не оборвалась.
4. Проверка: `sudo ufw status` — 22, 80, 443 allowed.

## 7. Что уже в порядке

- **fail2ban** включён для sshd — брутфорс режется.
- Успешные SSH-входы только с ваших IP (151.245.139.110 и др.).
- Лимиты памяти в docker-compose.prod.yml внедрены (п. 1).

Итого: при необходимости ограничьте память Node при сборке фронта (п. 2). SSH (п. 4) и ufw (п. 6) — по желанию для усиления безопасности.

## 8. RUNBOOK: откат при проблемах

- **SSH:** восстановить конфиг из бэкапа и перезагрузить демон:  
  `sudo cp /etc/ssh/sshd_config.bak.YYYYMMDD /etc/ssh/sshd_config && sudo systemctl reload ssh` (или `reload sshd`).
- **Файрвол:** временно отключить: `sudo ufw disable`.
- **Контейнеры:** остановить стек: `cd /opt/birka && docker compose -f docker-compose.prod.yml down`. При необходимости откатить образы на предыдущие теги и снова поднять.
