# Frontend (React)

## Стек

- React, TypeScript, Vite, Tailwind CSS.

## Страница AI

**Файл:** `frontend/src/pages/client/AIPage.tsx`

- Чат с AI-помощником.
- **Компания:** `useActiveCompany()` — текущая выбранная компания (`companyId`).
- **История:** `useAIHistory(companyId)` — загрузка истории с сервера; при успехе — гидрация store.
- **Отправка:** `useAIChat()` — мутация POST `/api/v1/ai/chat` с `message` и `company_id`; ответ добавляется в store, инвалидируется запрос истории.
- **Очистка:** `useClearAIHistory()` — DELETE `/api/v1/ai/history`, затем очистка локального store.
- **Store:** `useAIChatStore()` — сообщения по ключу компании (`getMessages`, `addMessage`, `setMessages`, `clearMessages`).
- UI: список сообщений (user / assistant), ReactMarkdown для ответов, кнопка «Скопировать», прокрутка вниз, кнопка «Очистить историю», тосты.

## Запросы к API

- Эндпоинты под префиксом `/api/v1/`.
- Заголовки авторизации: `X-Telegram-Init-Data` или `X-Session-Token` (как настроено в API-клиенте).

## Правила

- Оптимизация и понятный UI приоритетны.
- Запросы к API — через централизованный клиент (axios/fetch) и хуки (например, React Query).
