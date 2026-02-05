# База данных (PostgreSQL)

## Управление схемой

- **Миграции:** Alembic.
- Команды: создание ревизии, применение миграций — выполняются при деплое/разработке.

## Модели (основные)

Расположение: `backend/app/db/models/`.

- **User** — пользователь (telegram_id, role: client/warehouse/admin), связь с компаниями.
- **Session** — сессия (token, user_id, expires_at) для авторизации по X-Session-Token.
- **Company** — компания (реквизиты, привязка к пользователю).
- **Order** — заявка (order_number, status, destination, planned_qty, received_qty, packed_qty и т.д.).
- **OrderItem** — позиция заявки (product_id, planned_qty, received_qty, packed_qty, defect_qty).
- **Product** — товар (name, barcode, stock_quantity, defect_quantity, company_id).
- **Service** — услуга (прайс фулфилмента).
- **OrderService** — услуги в заявке.
- **ShipmentRequest** — заявка на отгрузку.
- **Destination** — адреса доставки (склады, маркетплейсы).
- **ChatMessage** — сообщения чата с AI (user_id, company_id, role, text).
- **DocumentChunk** — чанки документов для RAG (эмбеддинги, source_file, version).

Точный список таблиц и полей — в коде моделей и миграциях Alembic.

## Безопасность

- Не логировать чувствительные данные (пароли, токены, ПДн).
- Доступ к данным компании — только для авторизованного пользователя с привязкой к этой компании или роль warehouse/admin.
