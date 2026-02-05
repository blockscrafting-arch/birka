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
    AI_SYSTEM_INSTRUCTION = (
        "Ты помощник фулфилмента Бирка. На вопросы о заявках, товарах, остатках, браке, отгрузках, "
        "прайсе или реквизитах компании всегда вызывай соответствующие функции (tools) и отвечай "
        "только на основе полученных данных. Не придумывай номера заявок и не используй заглушки вроде [номер заявки].\n\n"
        "При вопросах об остатках («какой у меня остаток», «сколько у меня», «что на складе») ВСЕГДА вызывай get_stock_summary и показывай полную картину: "
        "остаток на складе (total_stock_quantity), в заявках — плановое (orders_total_planned), принято (orders_total_received), упаковано (orders_total_packed), брак (total_defect_quantity). "
        "Если пользователь не уточнил — показывай ВСЮ эту информацию, не угадывай.\n\n"
        "При вопросах о заявках показывай все три количества по заявкам: плановое, фактическое (принято), упаковано.\n\n"
        "При вопросах об упаковке (как упаковывать, требования к упаковке): если маркетплейс не указан — либо уточни "
        "для какого МП нужна информация (WB или Ozon), либо дай ответ для ОБОИХ маркетплейсов отдельно (для WB — так, для Ozon — так), "
        "так как требования у них разные."
    )
    openai_messages = [{"role": "system", "content": AI_SYSTEM_INSTRUCTION}]
    openai_messages.extend([{"role": m.role, "content": m.text} for m in history_rows])
    prompt = await build_rag_context_async(db, payload.message) or payload.message
    openai_messages.append({"role": "user", "content": prompt})

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
