"""AI endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.schemas.ai import AIChatRequest, AIChatResponse
from app.services.openai_service import OpenAIService

router = APIRouter()


@router.post("/chat", response_model=AIChatResponse)
async def chat(
    payload: AIChatRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> AIChatResponse:
    """Chat with AI assistant (RAG when document_chunks populated)."""
    service = OpenAIService()
    answer = await service.chat(payload.message, db=db)
    return AIChatResponse(answer=answer)
