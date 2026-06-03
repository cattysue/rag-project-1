import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch
import services.embeddings as emb_module


@pytest.fixture(autouse=True)
def reset_client():
    emb_module._client = None
    yield
    emb_module._client = None


def _make_mock_response(n: int = 1, value: float = 0.1) -> MagicMock:
    response = MagicMock()
    response.data = [MagicMock(embedding=[value] * 1536) for _ in range(n)]
    return response


# ── EMBEDDING_MODEL 상수 ──────────────────────────────────────────────────

def test_embedding_model_constant_is_defined():
    from services.embeddings import EMBEDDING_MODEL
    assert EMBEDDING_MODEL == "text-embedding-3-small"


# ── get_embeddings() 배치 함수 ────────────────────────────────────────────

def test_get_embeddings_returns_correct_count(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with patch("services.embeddings.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.embeddings.create.return_value = _make_mock_response(3)
        from services.embeddings import get_embeddings
        result = get_embeddings(["텍스트1", "텍스트2", "텍스트3"])
    assert len(result) == 3
    assert all(len(v) == 1536 for v in result)


def test_get_embeddings_calls_api_once(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with patch("services.embeddings.OpenAI") as MockOpenAI:
        mock_create = MockOpenAI.return_value.embeddings.create
        mock_create.return_value = _make_mock_response(2)
        from services.embeddings import get_embeddings
        get_embeddings(["a", "b"])
        assert mock_create.call_count == 1


def test_get_embeddings_raises_on_empty_response(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    empty_response = MagicMock()
    empty_response.data = []
    with patch("services.embeddings.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.embeddings.create.return_value = empty_response
        from services.embeddings import get_embeddings
        with pytest.raises(ValueError, match="비어있습니다"):
            get_embeddings(["텍스트"])


# ── get_embedding() 단일 편의 함수 ───────────────────────────────────────

def test_get_embedding_returns_1536_floats(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    with patch("services.embeddings.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.embeddings.create.return_value = _make_mock_response()
        from services.embeddings import get_embedding
        result = get_embedding("제1조에 관한 질문")
    assert len(result) == 1536
    assert isinstance(result[0], float)


def test_get_embedding_uses_correct_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    with patch("services.embeddings.OpenAI") as MockOpenAI:
        mock_create = MockOpenAI.return_value.embeddings.create
        mock_create.return_value = _make_mock_response()
        from services.embeddings import get_embedding, EMBEDDING_MODEL
        get_embedding("테스트")
        call_kwargs = mock_create.call_args
        assert call_kwargs.kwargs["model"] == EMBEDDING_MODEL
        assert call_kwargs.kwargs["input"] == ["테스트"]


def test_get_embedding_raises_on_missing_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from services.embeddings import get_embedding
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        get_embedding("테스트")


def test_get_embedding_client_cached(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    with patch("services.embeddings.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.embeddings.create.return_value = _make_mock_response()
        from services.embeddings import get_embedding
        get_embedding("첫 번째")
        get_embedding("두 번째")
        assert MockOpenAI.call_count == 1


# ── replace_documents() ───────────────────────────────────────────────────

def test_replace_documents_validates_length():
    from db.database import replace_documents
    with pytest.raises(ValueError, match="길이가 다릅니다"):
        replace_documents([{"chunk_text": "a"}], [])


def test_replace_documents_deletes_then_inserts():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    @contextmanager
    def fake_get_connection():
        yield mock_conn

    chunks = [{"chunk_text": "제1조", "article_number": "제1조", "article_title": "목적", "page_number": 1}]
    embeddings = [[0.5] * 1536]

    with patch("db.database.get_connection", fake_get_connection), \
         patch("db.database.extras.execute_values") as mock_ev:
        from db.database import replace_documents
        replace_documents(chunks, embeddings)

    # DELETE 먼저 호출됨
    first_call_sql = mock_cursor.execute.call_args_list[0][0][0].strip()
    assert "DELETE" in first_call_sql
    # execute_values로 INSERT 호출됨
    mock_ev.assert_called_once()
    mock_conn.commit.assert_called_once()


def test_replace_documents_is_atomic_on_error():
    """INSERT 실패 시 DELETE도 롤백되어야 함 (단일 트랜잭션)"""
    closed = []
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    @contextmanager
    def fake_get_connection():
        try:
            yield mock_conn
        except Exception:
            mock_conn.rollback()
            raise
        finally:
            closed.append(True)

    with patch("db.database.get_connection", fake_get_connection), \
         patch("db.database.extras.execute_values", side_effect=RuntimeError("insert fail")):
        from db.database import replace_documents
        with pytest.raises(RuntimeError):
            replace_documents(
                [{"chunk_text": "a", "article_number": None, "article_title": None, "page_number": 1}],
                [[0.1] * 1536],
            )

    mock_conn.commit.assert_not_called()
    mock_conn.rollback.assert_called_once()
    assert closed
