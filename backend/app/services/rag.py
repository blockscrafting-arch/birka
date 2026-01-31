"""Simple RAG stub for project documentation."""
from app.core.config import settings


def build_rag_context(message: str) -> str:
    """Build RAG context from static instructions."""
    if not settings.OPENAI_API_KEY:
        return ""
    base = (
        "Ты помощник фулфилмент компании Бирка. "
        "Отвечай кратко и по делу, используй статусы заявок: "
        "На приемке, Принято, Упаковка, Готово к отгрузке, Завершено. "
        "Если вопрос о браке — напомни, что фото обязательны."
    )
    return f"{base}\nВопрос клиента: {message}"
