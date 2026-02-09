"""Simple RAG stub for project documentation."""
from app.core.config import settings


def build_rag_context(message: str) -> str:
    """Build RAG context from static instructions."""
    if not settings.OPENAI_API_KEY:
        return ""
    base = (
        "Ты помощник фулфилмент компании Бирка. "
        "Отвечай кратко и по делу. "
        "Статусы заявок: На приемке, Принято, Упаковка, Готово к отгрузке, Завершено. "
        "Поддерживаемые маркетплейсы: Wildberries (WB) и Ozon. "
        "FBO-поставки: создание, синхронизация, этикетки коробов, импорт ШК. "
        "Если вопрос о браке — напомни, что фото обязательны. "
        "Если спрашивают про API-ключи — объясни, что их можно задать в разделе Компании."
    )
    return f"{base}\nВопрос клиента: {message}"
