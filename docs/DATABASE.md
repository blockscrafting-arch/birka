# База данных (PostgreSQL)

## Управление схемой

- **Миграции:** Alembic.
- Команды: создание ревизии, применение миграций — выполняются при деплое/разработке.
- Для RAG (эмбеддинги) требуется расширение **pgvector** в PostgreSQL.

## Модели (основные)

Расположение: `backend/app/db/models/`.

| Модель | Файл | Описание |
|--------|------|----------|
| **User** | user.py | Пользователь (telegram_id, role: client/warehouse/admin), связь с компаниями |
| **Session** | session.py | Сессия (token, user_id, expires_at) для авторизации по X-Session-Token |
| **Company** | company.py | Компания (реквизиты, user_id) |
| **CompanyAPIKeys** | company_api_keys.py | API-ключи WB/Ozon компании (хранятся зашифрованно) — реализовано |
| **Destination** | destination.py | Адреса доставки (склады, маркетплейсы) |
| **Product** | product.py | Товар (name, barcode, wb_article, wb_url, ozon_article, ozon_url, stock_quantity, defect_quantity, company_id); ProductPhoto — фото брака |
| **Order** | order.py | Заявка (order_number, status, destination, planned_qty, received_qty, packed_qty и т.д.) |
| **OrderItem** | order.py | Позиция заявки (product_id, planned_qty, received_qty, packed_qty, defect_qty) |
| **OrderCounter** | order_counter.py | Счётчик для генерации номеров заявок (по компании) |
| **OrderPhoto** | order_photo.py | Фото к заявке (S3 key) |
| **OrderService** | order_service.py | Услуги в заявке |
| **PackingRecord** | packing_record.py | Запись упаковки (кто, когда, заказ, штрихкод и т.д.) |
| **Service** | service.py | Услуга (прайс фулфилмента: категория, название, цена, unit) |
| **ServicePriceHistory** | service_history.py | История изменения цен услуг (аудит) |
| **ShipmentRequest** | shipment_request.py | Заявка на отгрузку |
| **FBOSupply**, **FBOSupplyBox**, **FBOSupplyItem** | fbo_supply.py | FBO-поставки WB/Ozon: поставка, короба, позиции — реализовано |
| **ContractTemplate** | contract_template.py | Шаблон договора (файл в S3) |
| **ChatMessage** | chat_message.py | Сообщения чата с AI (user_id, company_id, role, text) |
| **AISettings** | ai_settings.py | Глобальные настройки AI (провайдер, модель, temperature) — одна запись (id=1) |
| **DocumentChunk** | document_chunk.py | Чанки документов для RAG (эмбеддинги, source_file, version) |
| **WarehouseEmployee** | warehouse_employee.py | Сотрудник склада (привязка user — склад для отчётов) |

Точный список полей — в коде моделей и миграциях Alembic.

## Безопасность

- Не логировать чувствительные данные (пароли, токены, ПДн).
- Доступ к данным компании — только для авторизованного пользователя с привязкой к этой компании или роль warehouse/admin.
- API-ключи маркетплейсов хранятся в БД в зашифрованном виде (Fernet, ключ в `ENCRYPTION_KEY`).