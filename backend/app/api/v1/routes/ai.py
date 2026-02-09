"""AI endpoints."""
from fastapi import APIRouter, HTTPException, status

from app.schemas.ai import AIChatRequest, AIChatResponse
from app.services.openai_service import OpenAIService
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()


@router.post("/chat", response_model=AIChatResponse)
async def chat(payload: AIChatRequest) -> AIChatResponse:
    """Chat with AI assistant."""
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI сервис не настроен")
    try:
        service = OpenAIService()
        answer = await service.chat(payload.message)
        return AIChatResponse(answer=answer)
    except Exception as exc:
        logger.exception("ai_chat_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI сервис временно недоступен",
        ) from exc
