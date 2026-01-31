"""AI endpoints."""
from fastapi import APIRouter

from app.schemas.ai import AIChatRequest, AIChatResponse
from app.services.openai_service import OpenAIService

router = APIRouter()


@router.post("/chat", response_model=AIChatResponse)
async def chat(payload: AIChatRequest) -> AIChatResponse:
    """Chat with AI assistant."""
    service = OpenAIService()
    answer = await service.chat(payload.message)
    return AIChatResponse(answer=answer)
