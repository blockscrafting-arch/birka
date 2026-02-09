# Frontend (React)

## Стек

- React, TypeScript, Vite, Tailwind CSS.
- Роутинг: React Router. Запросы к API — через централизованный клиент (`frontend/src/services/api.ts`) и хуки (React Query и др.).

## Авторизация

- При загрузке приложения при наличии `webApp.initData` выполняется POST `/api/v1/auth/telegram` с `init_data`; в ответе — `session_token`, сохраняется в `localStorage` под ключом `birka_session_token`.
- Далее запросы к API отправляются с заголовком `X-Session-Token` (или `X-Telegram-Init-Data` по настройкам клиента).
- Текущий пользователь загружается через контекст `UserContext` / `useUser()`.

## Роуты и страницы

**Файл:** `frontend/src/App.tsx`

- `/` → редирект на `/client/company`
- **Клиент:** `/client/company`, `/client/products`, `/client/orders`, `/client/orders/:orderId`, `/client/ai`, `/client/pricing`, `/client/shipping`
- **Склад** (доступ при роли warehouse/admin): `/warehouse/print`, `/warehouse/receiving`, `/warehouse/packing`, `/warehouse/scanner`, `/warehouse/shipping`
- **Админка** (доступ при роли admin): `/admin`, `/admin/users`, `/admin/destinations`, `/admin/templates`, `/admin/services`, `/admin/documents`, `/admin/ai-settings`

## Навигация (TabBar)

**Файл:** `frontend/src/components/layout/TabBar.tsx`

- **Верхний уровень:** Клиент | Склад | Админка (склад и админка видны по ролям).
- **Клиент:** Компании, Товары, Заявки, Отгрузка, Прайс, AI-помощник.
- **Склад:** Приёмка, Упаковка, Отгрузка, Печать, Сканер.
- **Админка:** Пользователи, Адреса, Шаблоны, Прайс, Документы, AI.
- Внизу отображается индикатор фоновой загрузки файлов (UploadManager).

## Страницы (кратко)

| Путь | Компонент | Назначение |
|------|-----------|------------|
| /client/company | CompanyPage | Компании пользователя, реквизиты, API-ключи |
| /client/products | ProductsPage | Список товаров, остатки, брак |
| /client/orders | OrdersPage | Список заявок |
| /client/orders/:id | OrderDetail | Детали заявки, позиции, фото |
| /client/ai | AIPage | Чат с AI, история, очистка |
| /client/pricing | PricingPage | Прайс услуг |
| /client/shipping | ShippingPage | Заявки на отгрузку |
| /warehouse/receiving | ReceivingPage | Приёмка заказов |
| /warehouse/packing | PackingPage | Упаковка |
| /warehouse/shipping | WarehouseShippingPage | Отгрузка (склад) |
| /warehouse/print | PrintPage | Печать этикеток |
| /warehouse/scanner | ScannerPage | Сканер штрихкодов |
| /admin | AdminPage | Обзор админки |
| /admin/users | UsersPage | Пользователи, роли |
| /admin/destinations | DestinationsPage | Адреса доставки |
| /admin/templates | ContractTemplatesPage | Шаблоны договоров |
| /admin/services | ServicesPage | Услуги (прайс) |
| /admin/documents | DocumentsPage | Документы, RAG |
| /admin/ai-settings | AISettingsPage | Настройки AI (провайдер, модель) |

## Хуки и хранилища

- **useUser**, **useActiveCompany**, **useCompanies**, **useOrders**, **useOrderItems**, **useOrderPhotos**, **useProducts**, **useProductDefectPhotos**, **useServices**, **useShipping**, **useDestinations**, **useFBOSupplies**, **useCompanyAPIKeys**, **useContractTemplates**, **useWarehouse**, **useScanFeedback**, **useAI**, **useAdmin**, **useTelegram**
- **aiChatStore** — сообщения чата AI по компании; **uploadStore** — очередь загрузок.

## Компоненты

- **layout:** Header, Page, TabBar
- **shared:** BarcodeScanner, CompanySelect, OrderCard, PhotoGallery, PhotoUpload, UploadManager
- **ui:** Button, Input, Loader, Modal, Pagination, ProgressBar, Select, Skeleton, StatusBadge, Toast

## Страница AI (AIPage)

- Чат с AI-помощником. Компания — `useActiveCompany()`; история — `useAIHistory(companyId)` с гидрацией store; отправка — `useAIChat()` (POST `/api/v1/ai/chat`); очистка — `useClearAIHistory()` (DELETE `/api/v1/ai/history`). Store: `useAIChatStore()` — сообщения по ключу компании. UI: список сообщений (user/assistant), ReactMarkdown, кнопки «Скопировать» и «Очистить историю», тосты.

## Правила

- Оптимизация и понятный UI приоритетны.
- Запросы к API — через централизованный клиент и хуки (React Query и т.п.).
