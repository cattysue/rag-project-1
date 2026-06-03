import os
import re
import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")


# ── schema.sql 내용 검증 ──────────────────────────────────────────────────

def test_schema_sql_exists():
    assert os.path.exists(SCHEMA_PATH)


def test_schema_sql_has_pgvector_extension():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        sql = f.read()
    assert "CREATE EXTENSION IF NOT EXISTS vector" in sql


def test_schema_sql_has_all_required_columns():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        sql = f.read()
    for token in ["chunk_text", "vector(1536)", "article_number",
                  "article_title", "page_number", "created_at"]:
        assert token in sql, f"schema.sql에 '{token}' 없음"


def test_schema_sql_embedding_not_null():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        sql = f.read()
    assert re.search(r"embedding\s+vector\(\d+\)\s+NOT NULL", sql), \
        "embedding 컬럼에 NOT NULL 제약 없음"


def test_schema_sql_is_idempotent():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        sql = f.read()
    assert sql.count("IF NOT EXISTS") >= 2


# ── get_connection() 동작 검증 ────────────────────────────────────────────

def test_get_connection_raises_on_missing_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from db.database import get_connection
    with pytest.raises(ValueError, match="DATABASE_URL"):
        with get_connection():
            pass


def test_get_connection_registers_vector(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")
    mock_conn = MagicMock()
    with patch("db.database.psycopg2.connect", return_value=mock_conn), \
         patch("db.database.register_vector") as mock_register:
        from db.database import get_connection
        with get_connection() as conn:
            mock_register.assert_called_once_with(mock_conn)
            assert conn is mock_conn
    mock_conn.close.assert_called_once()


# ── init_db() 동작 검증 ───────────────────────────────────────────────────

def test_init_db_executes_schema_and_commits():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    @contextmanager
    def fake_get_connection():
        yield mock_conn

    with patch("db.database.get_connection", fake_get_connection):
        from db.database import init_db
        init_db()

    mock_cursor.execute.assert_called_once()
    assert "CREATE" in mock_cursor.execute.call_args[0][0]
    mock_conn.commit.assert_called_once()


def test_init_db_closes_connection_on_error():
    closed = []
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = RuntimeError("simulated DB error")
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    @contextmanager
    def fake_get_connection():
        try:
            yield mock_conn
        finally:
            closed.append(True)

    with patch("db.database.get_connection", fake_get_connection):
        from db.database import init_db
        with pytest.raises(RuntimeError):
            init_db()

    assert closed, "오류 발생 후 연결 정리(finally)가 실행되지 않음"
