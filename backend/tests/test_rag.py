"""Tests for RAG: build_rag_context_async return shape, STATIC_BASE, retrieval, marketplace and section filter, intent."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models.document_chunk import DocumentChunk
from app.services import rag
from app.services.rag_intent import (
    FIXED_RESPONSE_INTENTS,
    SECTION_INTENTS,
    detect_rag_intent,
)


@pytest.mark.asyncio
async def test_build_rag_context_async_returns_tuple_when_no_api_key():
    """When OPENAI_API_KEY is missing, returns (None, user_message)."""
    mock_db = MagicMock()
    with patch("app.services.rag.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = ""
        rag_system, user_message = await rag.build_rag_context_async(mock_db, "Hello")
    assert rag_system is None
    assert user_message == "Hello"


def test_static_base_no_identity_duplication():
    """STATIC_BASE does not duplicate main system prompt identity."""
    assert "статусы заявок" in rag.STATIC_BASE or "На приемке" in rag.STATIC_BASE
    assert "браке" in rag.STATIC_BASE or "фото" in rag.STATIC_BASE


def test_build_rag_context_sync_fallback():
    """build_rag_context returns empty string when no API key."""
    with patch("app.services.rag.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = ""
        assert rag.build_rag_context("test") == ""


# ----- Marketplace filter (понимание пользователя: ВБ vs Ozon) -----


def test_marketplace_filter_wb():
    """Сообщение про ВБ даёт фильтр wb для выбора релевантных чанков."""
    assert rag._marketplace_filter_from_message("как упаковать на ВБ?") == "wb"
    assert rag._marketplace_filter_from_message("требования Wildberries") == "wb"
    assert rag._marketplace_filter_from_message("на вайлдберриз") == "wb"


def test_marketplace_filter_ozon():
    """Сообщение про Ozon даёт фильтр ozon."""
    assert rag._marketplace_filter_from_message("упаковка на Озоне") == "ozon"
    assert rag._marketplace_filter_from_message("ozon требования") == "ozon"


def test_marketplace_filter_none():
    """Без упоминания маркетплейса фильтр не применяется."""
    assert rag._marketplace_filter_from_message("как упаковать зеркало?") is None
    assert rag._marketplace_filter_from_message("") is None


# ----- Retrieval: при наличии чанков возвращается контекст -----


@pytest.mark.asyncio
async def test_build_rag_context_async_returns_none_when_no_chunks():
    """Когда в БД нет чанков, возвращается (None, message)."""
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 0
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.rag.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "sk-test"
        with patch("app.services.rag.get_embedding", new_callable=AsyncMock, return_value=[0.1] * 1536):
            rag_system, user_message = await rag.build_rag_context_async(mock_db, "как упаковать обувь?")
    assert rag_system is None
    assert user_message == "как упаковать обувь?"


@pytest.mark.asyncio
async def test_build_rag_context_async_returns_none_when_embedding_fails():
    """Когда get_embedding возвращает None, контекст не подставляется."""
    mock_db = MagicMock()
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 1
    mock_db.execute = AsyncMock(return_value=mock_count_result)

    with patch("app.services.rag.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "sk-test"
        with patch("app.services.rag.get_embedding", new_callable=AsyncMock, return_value=None):
            rag_system, user_message = await rag.build_rag_context_async(mock_db, "вопрос")
    assert rag_system is None
    assert user_message == "вопрос"


@pytest.mark.asyncio
async def test_build_rag_context_async_returns_context_when_chunks_mocked():
    """При подставленных чанках в ответе есть контекст из документации."""
    chunk1 = DocumentChunk(
        id=1,
        content="Обувь упаковать в коробку. Крышку зафиксировать скотчем или резинкой.",
        source_file="wb_packaging.txt",
        chunk_index=0,
        embedding=None,
        created_at=None,
        document_type="txt",
        version=1,
        section="wb_common",
    )
    chunk2 = DocumentChunk(
        id=2,
        content="Зеркала: пузырчатая плёнка, пенопласт, коробка 5-слойного картона.",
        source_file="Как_правильно_упаковать_разные_виды_товаров.docx",
        chunk_index=1,
        embedding=None,
        created_at=None,
        document_type="docx",
        version=1,
        section="zerkala",
    )

    mock_db = MagicMock()
    call_count = [0]

    class FakeCountResult:
        def scalar_one(self):
            return 2

    class FakeChunksResult:
        def scalars(self):
            return self

        def all(self):
            return [chunk1, chunk2]

    async def mock_execute(query):
        call_count[0] += 1
        if call_count[0] == 1:
            return FakeCountResult()
        return FakeChunksResult()

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    with patch("app.services.rag.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "sk-test"
        mock_settings.RAG_CHUNKS_LIMIT = 5
        with patch("app.services.rag.get_embedding", new_callable=AsyncMock, return_value=[0.1] * 1536):
            # Сообщение без явного интента раздела (обувь/зеркала), чтобы мок вернул оба чанка
            rag_system, user_message = await rag.build_rag_context_async(
                mock_db, "как упаковать на ВБ?"
            )

    assert rag_system is not None
    assert "Контекст из документации" in rag_system
    assert "Обувь" in rag_system or "коробку" in rag_system
    assert "Зеркала" in rag_system or "пузырчатая" in rag_system
    assert user_message == "как упаковать на ВБ?"


# ----- Intent detector -----


def test_detect_rag_intent_ozon_etiketka():
    """Ozon + этикетка/размер этикетки/58/120 -> ozon_etiketka."""
    assert detect_rag_intent("какой размер этикетки для Ozon?") == "ozon_etiketka"
    assert detect_rag_intent("этикетка Ozon FBS 58") == "ozon_etiketka"
    assert detect_rag_intent("озон этикетка размер") == "ozon_etiketka"
    assert detect_rag_intent("Ozon этикетка 120 мм") == "ozon_etiketka"
    assert detect_rag_intent("ozon 120×75 этикетка") == "ozon_etiketka"


def test_detect_rag_intent_ozon_krasnyj_skotch():
    """Ozon + красный скотч -> ozon_krasnyj_skotch."""
    assert detect_rag_intent("можно красный скотч на Ozon?") == "ozon_krasnyj_skotch"
    assert detect_rag_intent("скотч красный озон") == "ozon_krasnyj_skotch"


def test_detect_rag_intent_obuv():
    """WB или без маркетплейса + обувь (и синонимы) -> obuv."""
    assert detect_rag_intent("как упаковать обувь на ВБ?") == "obuv"
    assert detect_rag_intent("обувь Wildberries") == "obuv"
    assert detect_rag_intent("упаковка обуви") == "obuv"
    assert detect_rag_intent("кроссовки вб") == "obuv"
    assert detect_rag_intent("тапочки для WB") == "obuv"
    assert detect_rag_intent("сандалии на ВБ") == "obuv"


def test_detect_rag_intent_zerkala():
    """зеркал / трюмо -> zerkala."""
    assert detect_rag_intent("зеркало на Wildberries") == "zerkala"
    assert detect_rag_intent("как упаковать зеркала для ВБ") == "zerkala"
    assert detect_rag_intent("трюмо вб") == "zerkala"


def test_detect_rag_intent_posuda():
    """посуда и синонимы -> posuda."""
    assert detect_rag_intent("посуда для ВБ") == "posuda"
    assert detect_rag_intent("упаковать посуду на WB") == "posuda"
    assert detect_rag_intent("тарелки для вб") == "posuda"
    assert detect_rag_intent("кастрюли на Wildberries") == "posuda"
    assert detect_rag_intent("сковорода вб") == "posuda"


def test_detect_rag_intent_gabarity_wb():
    """габарит/лимит/короб (WB) -> gabarity_wb."""
    assert detect_rag_intent("габариты короба для WB") == "gabarity_wb"
    assert detect_rag_intent("лимиты по коробу ВБ") == "gabarity_wb"


def test_detect_rag_intent_strejch_skotch_wb():
    """стрейч/скотч + WB -> strejch_skotch_wb."""
    assert detect_rag_intent("можно стрейч на ВБ?") == "strejch_skotch_wb"
    assert detect_rag_intent("скотч и стрейч Wildberries") == "strejch_skotch_wb"


def test_detect_rag_intent_none():
    """Без ключевых слов интента -> None."""
    assert detect_rag_intent("какие у меня заявки?") is None
    assert detect_rag_intent("") is None
    assert detect_rag_intent("   ") is None


def test_fixed_response_intents():
    """Фиксированный ответ без LLM для этикетки и красного скотча Ozon."""
    assert "ozon_etiketka" in FIXED_RESPONSE_INTENTS
    assert "ozon_krasnyj_skotch" in FIXED_RESPONSE_INTENTS


def test_section_intents():
    """Section filter intents for WB DOCX."""
    assert "obuv" in SECTION_INTENTS
    assert "zerkala" in SECTION_INTENTS
    assert "posuda" in SECTION_INTENTS


def test_hybrid_intent_keywords():
    """Гибридный поиск: ключевые слова по интенту для obuv/zerkala/posuda."""
    assert "obuv" in rag.HYBRID_INTENT_KEYWORDS
    assert "zerkala" in rag.HYBRID_INTENT_KEYWORDS
    assert "posuda" in rag.HYBRID_INTENT_KEYWORDS
    assert "силикагель" in rag.HYBRID_INTENT_KEYWORDS["obuv"]
    assert "уголк" in rag.HYBRID_INTENT_KEYWORDS["zerkala"]
    assert "2 слоя" in rag.HYBRID_INTENT_KEYWORDS["posuda"]
