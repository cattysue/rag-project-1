# Story 1.4: OpenAI 임베딩 및 벡터 저장 파이프라인

Status: review

## Story

As a 시스템,
I want 파싱된 청크를 OpenAI 임베딩 API로 벡터화하여 pgvector DB에 저장하는 기능을,
so that 교사의 질문과 의미적으로 유사한 조항을 빠르게 검색할 수 있다.

## Acceptance Criteria

1. **Given** 파싱된 청크 목록이 있을 때 **When** `embeddings.py`의 임베딩 함수를 호출하면 **Then** OpenAI `text-embedding-3-small` 모델이 호출되고 각 청크에 대해 1536차원 벡터가 반환된다
2. **Given** 임베딩 벡터가 생성되었을 때 **When** `database.py`의 저장 함수를 호출하면 **Then** `documents` 테이블에 `chunk_text`, `embedding`, `article_number`, `article_title`, `page_number`가 함께 저장된다
3. **Given** `OPENAI_API_KEY`가 잘못 설정된 경우 **When** 임베딩 함수를 호출하면 **Then** 예외가 발생하고 상위 호출자에게 명확한 오류 메시지가 전달된다

## Tasks / Subtasks

- [x] Task 1: `backend/services/embeddings.py` 작성 (AC: #1, #3)
  - [x] `_get_client()` 구현 (OPENAI_API_KEY lazy 로드, 없으면 ValueError)
  - [x] `get_embedding(text: str) -> list[float]` 구현 (text-embedding-3-small)

- [x] Task 2: `backend/db/database.py` 수정 — `save_chunks()` 추가 (AC: #2)
  - [x] `save_chunks(chunks, embeddings)` 구현 (get_connection 컨텍스트 매니저 사용)

- [x] Task 3: `backend/tests/test_embeddings.py` 작성 (AC: #1, #3)
  - [x] OpenAI 클라이언트 모킹으로 1536차원 반환 검증
  - [x] API 키 없을 때 ValueError 발생 검증
  - [x] `save_chunks()` 동작 검증 (test_embeddings.py에 포함)

- [x] Task 4: 전체 테스트 실행 — 37 passed (기존 30 + 신규 7), 0 failures

## Dev Notes

### 이전 스토리에서 확립된 패턴 — 반드시 준수

**코드리뷰를 통해 확립된 핵심 규칙:**
- `load_dotenv()` 호출 금지 — `embeddings.py`에서 절대 호출 금지. `main.py` 전담.
- 환경변수 lazy 로드 패턴 (`database.py`의 `get_connection()` 참고):
  ```python
  # 잘못된 방식 (모듈 임포트 시 고정)
  API_KEY = os.getenv("OPENAI_API_KEY")  # ← 금지

  # 올바른 방식 (호출 시 읽기)
  def _get_client():
      key = os.getenv("OPENAI_API_KEY")
      if not key:
          raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다")
      ...
  ```
- `get_connection()` 은 `@contextmanager` → `with get_connection() as conn:` 패턴 사용
- `save_chunks()` 에서 `load_dotenv()` 호출 금지 — database.py도 동일 규칙

### 이 스토리에서 생성/수정되는 파일

```
backend/
├── services/
│   └── embeddings.py       ← NEW
├── db/
│   └── database.py         ← UPDATE: save_chunks() 추가
└── tests/
    └── test_embeddings.py  ← NEW
```

> `test_db.py`에 `save_chunks` 테스트를 추가하거나 별도 파일 사용 — 둘 다 가능.

### backend/services/embeddings.py 전체 구현

```python
import os
from openai import OpenAI

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다")
        _client = OpenAI(api_key=api_key)
    return _client


def get_embedding(text: str) -> list[float]:
    client = _get_client()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding
```

**설계 결정:**
- `_client`를 모듈 수준에서 캐싱 — API 키를 매 호출마다 환경변수에서 읽지 않고 최초 1회만 초기화
- `openai==1.54.4` (1.x API 스타일): `client.embeddings.create()` — `openai.Embedding.create()` (구버전 0.x 스타일) 사용 금지
- 반환 타입: `list[float]` (pgvector에 psycopg2로 저장 시 이 형태 그대로 전달)
- `text-embedding-3-small` → 출력 차원 1536 (schema.sql의 `vector(1536)` 과 일치)

### backend/db/database.py 수정 내용

기존 코드에 `save_chunks()` 함수 추가 (기존 코드 수정 없음):

```python
def save_chunks(chunks: list[dict], embeddings: list[list[float]]) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            for chunk, embedding in zip(chunks, embeddings):
                cur.execute(
                    """
                    INSERT INTO documents
                        (chunk_text, embedding, article_number, article_title, page_number)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        chunk["chunk_text"],
                        embedding,
                        chunk.get("article_number"),
                        chunk.get("article_title"),
                        chunk.get("page_number"),
                    ),
                )
        conn.commit()
```

**설계 결정:**
- `chunks`와 `embeddings`를 별도 리스트로 받음 — 서비스 계층(임베딩)과 저장 계층(DB) 분리
- `zip(chunks, embeddings)` — 순서가 일치해야 함 (호출자 책임)
- `chunk.get("article_number")` — None이면 NULL로 저장 (서문·부칙 처리)
- `embedding`은 `list[float]` — `register_vector(conn)`이 호출된 커넥션에서 pgvector 타입으로 자동 변환
- 모든 INSERT를 하나의 트랜잭션으로 처리 — 일부 실패 시 전체 롤백

### backend/tests/test_embeddings.py 전체 구현

```python
import pytest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager


# ── get_embedding() 단위 테스트 ────────────────────────────────────────────

def test_get_embedding_returns_1536_floats(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    fake_embedding = [0.1] * 1536
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=fake_embedding)]

    with patch("services.embeddings.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.embeddings.create.return_value = mock_response
        # 캐시 초기화 후 테스트
        import services.embeddings as emb
        emb._client = None
        from services.embeddings import get_embedding
        result = get_embedding("제1조에 관한 질문")

    assert len(result) == 1536
    assert all(isinstance(v, float) for v in result)


def test_get_embedding_calls_correct_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    fake_embedding = [0.0] * 1536
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=fake_embedding)]

    with patch("services.embeddings.OpenAI") as MockOpenAI:
        mock_client = MockOpenAI.return_value
        mock_client.embeddings.create.return_value = mock_response
        import services.embeddings as emb
        emb._client = None
        from services.embeddings import get_embedding
        get_embedding("테스트")
        call_kwargs = mock_client.embeddings.create.call_args
        assert call_kwargs.kwargs["model"] == "text-embedding-3-small"


def test_get_embedding_raises_on_missing_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import services.embeddings as emb
    emb._client = None
    from services.embeddings import get_embedding
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        get_embedding("테스트")


# ── save_chunks() 단위 테스트 ─────────────────────────────────────────────

def test_save_chunks_inserts_all_rows():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    @contextmanager
    def fake_get_connection():
        yield mock_conn

    chunks = [
        {"chunk_text": "제1조 내용", "article_number": "제1조", "article_title": "목적", "page_number": 1},
        {"chunk_text": "서문 내용", "article_number": None, "article_title": None, "page_number": 1},
    ]
    embeddings = [[0.1] * 1536, [0.2] * 1536]

    with patch("db.database.get_connection", fake_get_connection):
        from db.database import save_chunks
        save_chunks(chunks, embeddings)

    assert mock_cursor.execute.call_count == 2
    mock_conn.commit.assert_called_once()


def test_save_chunks_commits_or_rolls_back_on_error():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = [None, RuntimeError("DB error")]
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    closed = []

    @contextmanager
    def fake_get_connection():
        try:
            yield mock_conn
        finally:
            closed.append(True)

    chunks = [
        {"chunk_text": "청크1", "article_number": "제1조", "article_title": None, "page_number": 1},
        {"chunk_text": "청크2", "article_number": "제2조", "article_title": None, "page_number": 1},
    ]
    embeddings = [[0.1] * 1536, [0.2] * 1536]

    with patch("db.database.get_connection", fake_get_connection):
        from db.database import save_chunks
        with pytest.raises(RuntimeError):
            save_chunks(chunks, embeddings)

    assert closed, "오류 발생 후 커넥션이 닫히지 않음"
```

### 테스트 시 _client 캐시 초기화 주의사항

`_get_client()`는 `_client` 전역 변수를 캐싱합니다. 테스트 간 격리를 위해 각 테스트에서:
```python
import services.embeddings as emb
emb._client = None  # 캐시 초기화
```
이 패턴을 반드시 사용하세요. `autouse` fixture로 처리해도 됩니다.

### Story 1.5와의 연결 (미리 알아두기)

Story 1.5 (관리자 PDF 업로드 API)에서:
```python
# 예시 흐름 (Story 1.5에서 구현)
chunks = parse_pdf(file_bytes)
embeddings = [get_embedding(c["chunk_text"]) for c in chunks]
clear_documents()   # ← Story 1.5에서 database.py에 추가 예정
save_chunks(chunks, embeddings)
```

→ `get_embedding()`, `save_chunks()` 함수 시그니처를 변경하지 말 것.

### 명명 규칙

| 항목 | 규칙 | 예시 |
|------|------|------|
| 파일명 | snake_case | `embeddings.py` |
| 함수명 | snake_case | `get_embedding()`, `save_chunks()` |
| 내부 함수 | `_` 접두어 | `_get_client()` |

### References

- OpenAI 임베딩 모델: [Source: _bmad-output/planning-artifacts/architecture.md#핵심-아키텍처-결정]
- DB 스키마: [Source: _bmad-output/planning-artifacts/architecture.md#데이터-아키텍처]
- AR-5 (API 응답): [Source: _bmad-output/planning-artifacts/epics.md#additional-requirements]
- get_connection() 패턴: [Source: _bmad-output/implementation-artifacts/1-2-데이터베이스-스키마-및-pgvector-초기화.md]
- lazy env 패턴: [Source: 1-2 코드리뷰 — DATABASE_URL 교훈 적용]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

- openai 패키지 미설치 → `pip install openai==1.54.4` 후 정상 동작
- autouse fixture로 `_client` 캐시 초기화 — 테스트 간 격리 보장

### Completion Notes List

- embeddings.py: _get_client() lazy 초기화 + 캐싱, get_embedding() openai 1.x API
- database.py: save_chunks() 추가 — 단일 트랜잭션으로 모든 청크 INSERT
- test_embeddings.py: 7개 테스트 (1536차원 검증, 모델명 검증, API 키 오류, 캐싱, save_chunks)
- pytest 37 passed (기존 30 회귀 포함)

### File List

- `backend/services/embeddings.py` (NEW)
- `backend/db/database.py` (UPDATED: save_chunks() 추가)
- `backend/tests/test_embeddings.py` (NEW)
