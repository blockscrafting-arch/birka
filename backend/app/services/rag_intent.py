"""RAG intent detection from user message (keyword-based, no LLM)."""

# Intents that should get a fixed "no info" response without calling LLM
FIXED_RESPONSE_INTENTS = frozenset({"ozon_etiketka", "ozon_krasnyj_skotch"})

# Section filter intents for WB DOCX chunks
SECTION_INTENTS = frozenset({"obuv", "zerkala", "posuda", "gabarity_wb", "strejch_skotch_wb"})


def detect_rag_intent(message: str) -> str | None:
    """
    Detect packaging/docs intent from user message for RAG routing.
    Returns intent key or None (general packaging / no specific section).
    """
    if not message or not message.strip():
        return None
    lower = message.lower().strip()

    # Ozon: fixed-response intents (no LLM)
    if "ozon" in lower or "озон" in lower:
        if (
            "этикетк" in lower
            or ("размер" in lower and "этикетк" in lower)
            or "58" in lower
            or "120" in lower
            or ("120" in lower and "75" in lower)
        ):
            return "ozon_etiketka"
        if ("красн" in lower and "скотч" in lower) or ("скотч" in lower and "красн" in lower):
            return "ozon_krasnyj_skotch"

    # WB or no marketplace: section-specific intents (с синонимами)
    has_wb = "wb" in lower or "вб" in lower or "wildberries" in lower or "вайлдберриз" in lower
    if has_wb or not ("ozon" in lower or "озон" in lower):
        if "обув" in lower or any(x in lower for x in ("кроссовк", "туфл", "сандал", "тапочк", "ботинк", "сапог")):
            return "obuv"
        if "зеркал" in lower or "трюмо" in lower:
            return "zerkala"
        if any(x in lower for x in ("посуда", "посуду", "тарелк", "кастрюл", "сковород", "стеклянн")):
            return "posuda"
        if (
            "габарит" in lower
            or "лимит" in lower
            or ("короб" in lower and ("размер" in lower or "для" in lower or "вб" in lower or "wb" in lower))
        ):
            return "gabarity_wb"
        if ("стрейч" in lower or "скотч" in lower) and has_wb:
            return "strejch_skotch_wb"

    return None
