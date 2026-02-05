"""AI endpoints: chat with history persisted in DB."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.db.models.ai_settings import AISettings
from app.db.models.chat_message import ChatMessage
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.ai import AIChatHistoryOut, AIChatRequest, AIChatResponse, ChatMessageOut
from app.services.openai_service import OpenAIService
from app.services.rag import build_rag_context_async

router = APIRouter()

HISTORY_LIMIT = 50


@router.get("/history", response_model=AIChatHistoryOut)
async def get_history(
    company_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIChatHistoryOut:
    """Return last HISTORY_LIMIT messages for the current user (and company if specified)."""
    q = (
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id)
        .where((ChatMessage.company_id == company_id) if company_id is not None else (ChatMessage.company_id.is_(None)))
        .order_by(ChatMessage.created_at.desc())
        .limit(HISTORY_LIMIT)
    )
    result = await db.execute(q)
    rows = list(result.scalars().all())
    rows.reverse()  # chronological order for client
    messages = [ChatMessageOut(role=m.role, text=m.text) for m in rows]
    return AIChatHistoryOut(messages=messages)


@router.delete("/history")
async def delete_history(
    company_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Clear chat history for the current user (and company if specified)."""
    stmt = delete(ChatMessage).where(ChatMessage.user_id == current_user.id)
    if company_id is not None:
        stmt = stmt.where(ChatMessage.company_id == company_id)
    else:
        stmt = stmt.where(ChatMessage.company_id.is_(None))
    await db.execute(stmt)
    await db.commit()
    return {"status": "ok"}


@router.post("/chat", response_model=AIChatResponse)
async def chat(
    payload: AIChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIChatResponse:
    """Chat with AI assistant. History loaded from and saved to DB; RAG when document_chunks populated."""
    ai_row = await db.get(AISettings, 1)
    if ai_row:
        service = OpenAIService(
            provider=ai_row.provider,
            model=ai_row.model,
            temperature=float(ai_row.temperature),
        )
    else:
        service = OpenAIService(
            provider=settings.AI_PROVIDER,
            model=settings.AI_MODEL,
        )

    # Load history from DB (same user + company_id), last HISTORY_LIMIT in chronological order
    q = (
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id)
        .where(
            (ChatMessage.company_id == payload.company_id)
            if payload.company_id is not None
            else (ChatMessage.company_id.is_(None))
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(HISTORY_LIMIT)
    )
    result = await db.execute(q)
    history_rows = list(result.scalars().all())
    history_rows.reverse()

    # Build OpenAI messages: system instruction + history + new user message with RAG context
    AI_SYSTEM_INSTRUCTION = """Ты — AI-помощник фулфилмент-компании «Бирка». Твоя задача — помогать клиентам с вопросами о заявках, товарах, остатках, браке, отгрузках, ценах и документах.

## Правила работы

### Использование функций (tools)
- На вопросы о данных (заявки, товары, остатки, прайс, реквизиты) ВСЕГДА вызывай соответствующую функцию.
- Отвечай ТОЛЬКО на основе полученных данных. Не выдумывай номера заявок, количества или другую информацию.
- Если функция вернула ошибку (поле "error" в ответе) — объясни её пользователю понятным языком. Если указано «Не указана компания» — направь выбрать компанию в приложении.

### Об остатках и складе
- При вопросах об остатках («сколько у меня», «что на складе») вызови get_stock_summary.
- Показывай: количество товаров, остаток на складе (total_stock_quantity), по заявкам — плановое (orders_total_planned), принято (orders_total_received), упаковано (orders_total_packed), брак (total_defect_quantity).
- Если есть брак — упомяни, что можно посмотреть детали и фото.

### О заявках
- При вопросах о заявках показывай: плановое количество, принято, упаковано.
- Статусы заявок: На приемке → Принято → Упаковка → Готово к отгрузке → Завершено.

### Об упаковке (WB / Ozon)
- Если маркетплейс не указан — уточни или дай информацию для обоих (требования разные).

### О браке
- При вопросах о браке напомни, что фото обязательны для фиксации.

## Формат ответов
- Отвечай кратко, по делу — это Telegram Mini App.
- Используй markdown для списков и выделения важного.
- Обращайся на «вы».
- Не используй эмодзи.
- Отвечай только на русском языке.

## Ограничения
- Не отвечай на вопросы, не связанные с фулфилментом, складом или услугами «Бирки».
- Если вопрос не по теме — вежливо перенаправь: «Я помогаю с вопросами о заявках, товарах и услугах фулфилмента. Чем могу помочь?»
"""
    openai_messages = [{"role": "system", "content": AI_SYSTEM_INSTRUCTION}]
    rag_system, user_content = await build_rag_context_async(db, payload.message)
    if rag_system:
        openai_messages.append({"role": "system", "content": rag_system})
    openai_messages.extend([{"role": m.role, "content": m.text} for m in history_rows])
    openai_messages.append({"role": "user", "content": user_content})

    answer = await service.chat(openai_messages, db=db, user=current_user, company_id=payload.company_id)

    # Persist user message and assistant reply
    user_msg = ChatMessage(
        user_id=current_user.id,
        company_id=payload.company_id,
        role="user",
        text=payload.message,
    )
    assistant_msg = ChatMessage(
        user_id=current_user.id,
        company_id=payload.company_id,
        role="assistant",
        text=answer,
    )
    db.add(user_msg)
    db.add(assistant_msg)
    await db.commit()

    return AIChatResponse(answer=answer)
