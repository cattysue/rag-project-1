# Story 2.1: RAG 파이프라인 및 채팅 API (백엔드)

Status: review

## Story

As a 시스템,
I want 교사의 질문을 받아 벡터 검색 후 GPT-4o 답변과 출처 조항을 반환하는 백엔드 API를,
so that 교사가 규정 관련 질문을 하면 정확한 출처와 함께 요약 답변을 받을 수 있다.

## Acceptance Criteria

1. **Given** 유효한 한국어 질문이 `POST /chat`으로 전송되었을 때 **When** `rag.py`가 pgvector 코사인 유사도 검색을 실행하면 **Then** 상위 유사 청크가 반환되고 GPT-4o 호출에 컨텍스트로 전달된다
2. **Given** GPT-4o 답변이 생성되었을 때 **When** `POST /chat` 응답이 반환되면 **Then** `{"answer": "제○조에 따르면...", "sources": [{"article_number": "제○조", "article_title": "..."}]}` 형식의 JSON이 반환된다
3. **Given** 질문 내용이 규정과 관련 없어 유사도 점수가 임계값 이하인 경우 **When** RAG 검색 결과를 평가하면 **Then** GPT가 내용을 생성하지 않고 `{"answer": "해당 내용은 규정에 명시되어 있지 않습니다", "sources": []}` 가 반환된다
4. **Given** `POST /chat`이 정상적으로 동작할 때 **When** 이전 대화 내역을 `messages` 배열로 함께 전송하면 **Then** GPT-4o가 이전 맥락을 고려한 연속 답변을 생성한다
5. **Given** `test_chat.py`를 실행했을 때 **When** 샘플 질문에 대한 API 응답 테스트가 수행되면 **Then** 응답 JSON 구조와 sources 필드 존재 여부 검증 테스트가 통과된다

## Tasks / Subtasks

- [x] Task 1: `backend/db/schema.sql` HNSW 인덱스 추가 (AC: #1)
  - [x] 기존 파일 끝에 HNSW 인덱스 DDL 추가 (아래 Dev Notes 참조)
  - [x] 인덱스: `vector_cosine_ops`, m=16, ef_construction=64

- [x] Task 2: `backend/services/rag.py` 신규 생성 (AC: #1, #2, #3, #4)
  - [x] `EMBEDDING_MODEL` 상수를 `embeddings.py`에서 import (재선언 금지)
  - [x] `SIMILARITY_THRESHOLD = 0.5` 모듈 상수 정의 (코사인 거리 기준)
  - [x] `TOP_K = 5` 모듈 상수 정의
  - [x] `search_similar_chunks(query_embedding: list[float]) -> list[dict]` 구현
    - pgvector `<=>` 연산자로 코사인 거리 계산, ORDER BY distance ASC LIMIT TOP_K
    - distance < SIMILARITY_THRESHOLD 인 결과만 반환
    - 반환 형식: `[{"chunk_text": ..., "article_number": ..., "article_title": ..., "distance": ...}]`
  - [x] `get_chat_answer(question: str, messages: list[dict]) -> dict` 구현
    - `get_embedding(question)` 으로 질문 벡터화 (embeddings.py 재사용)
    - `search_similar_chunks()` 호출
    - 결과 없으면 GPT 호출 없이 즉시 `{"answer": "해당 내용은 규정에 명시되어 있지 않습니다", "sources": []}` 반환
    - 결과 있으면 GPT-4o 호출 (아래 시스템 프롬프트·메시지 구성 참조)
    - 반환: `{"answer": str, "sources": list[dict]}`

- [x] Task 3: `backend/routers/chat.py` 신규 생성 (AC: #2, #4)
  - [x] Pydantic 모델: `Message(role, content)`, `ChatRequest(question, messages=[])`, `ChatResponse(answer, sources)`, `Source(article_number, article_title)`
  - [x] `router = APIRouter()` (prefix 없음)
  - [x] `POST /chat` 엔드포인트: `ChatRequest` → `rag.get_chat_answer()` 호출 → `ChatResponse` 반환
  - [x] 인증 불필요 (교사 공개 API)

- [x] Task 4: `backend/main.py` 업데이트 (AC: #2)
  - [x] `from routers import chat` 추가
  - [x] `app.include_router(chat.router)` 추가 (admin 라우터 아래)

- [x] Task 5: `backend/tests/test_chat.py` 신규 생성 (AC: #5)
  - [x] `POST /chat` 성공 시 응답에 `answer` (str) + `sources` (list) 필드 존재 검증
  - [x] `sources` 각 항목에 `article_number`, `article_title` 필드 존재 검증
  - [x] 유사 청크 없음(빈 리스트) 시 `"해당 내용은 규정에 명시되어 있지 않습니다"` 답변 반환 검증
  - [x] FastAPI `TestClient` + `unittest.mock.patch` 사용 (실제 DB/OpenAI 호출 없음)

## Dev Notes

### 파일별 작업 요약

| 파일 | 상태 | 주요 변경 |
|------|------|-----------|
| `backend/db/schema.sql` | **UPDATE** | HNSW 인덱스 한 줄 추가 |
| `backend/services/rag.py` | **NEW** | 벡터 검색 + GPT-4o 답변 생성 |
| `backend/routers/chat.py` | **NEW** | POST /chat 엔드포인트 |
| `backend/main.py` | **UPDATE** | chat 라우터 등록 2줄 |
| `backend/tests/test_chat.py` | **NEW** | 응답 구조 검증 테스트 |

### Task 1: schema.sql HNSW 인덱스

현재 schema.sql에는 인덱스가 없어 pgvector가 전체 테이블 순차 스캔을 수행합니다. HNSW 인덱스 추가 필수:

```sql
-- 기존 schema.sql 끝에 추가
CREATE INDEX IF NOT EXISTS idx_documents_embedding_hnsw
ON documents USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

- `vector_cosine_ops`: 코사인 거리(`<=>` 연산자)에 최적화
- `m = 16`: 그래프 연결 수 (기본값, 정확도/속도 균형)
- `ef_construction = 64`: 인덱스 구축 품질 (기본값)

> **왜 HNSW?** Hierarchical Navigable Small World 알고리즘. 벡터 검색을 순차 탐색(O(n)) 대신 근사 최근접 이웃 탐색(O(log n))으로 수행해 문서 수가 늘어도 빠른 응답 보장.

### Task 2: rag.py 구현 가이드

**반드시 embeddings.py에서 EMBEDDING_MODEL import:**
```python
from services.embeddings import get_embedding, EMBEDDING_MODEL
```
`EMBEDDING_MODEL`을 rag.py에 별도 선언하면 안 됩니다 — 저장 시(embeddings.py)와 검색 시(rag.py) 모델이 반드시 동일해야 합니다.

**pgvector 코사인 거리 검색:**
```python
# database.py의 get_connection() 재사용 — 별도 연결 생성 금지
from db.database import get_connection

def search_similar_chunks(query_embedding: list[float]) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT chunk_text, article_number, article_title,
                       embedding <=> %s::vector AS distance
                FROM documents
                ORDER BY distance ASC
                LIMIT %s
            """, (query_embedding, TOP_K))
            rows = cur.fetchall()
    return [
        {
            "chunk_text": row[0],
            "article_number": row[1],
            "article_title": row[2],
            "distance": float(row[3]),
        }
        for row in rows
        if row[3] < SIMILARITY_THRESHOLD
    ]
```

**`<=>` 연산자**: pgvector 코사인 거리 (0=동일, 1=무관계, 2=반대).
`SIMILARITY_THRESHOLD = 0.5` 이상이면 관련 조항 없음으로 판단합니다.

**GPT-4o 호출 구성:**
```python
import os
from openai import OpenAI

_gpt_client: OpenAI | None = None

def _get_gpt_client() -> OpenAI:
    global _gpt_client
    if _gpt_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다")
        _gpt_client = OpenAI(api_key=api_key)
    return _gpt_client

GPT_MODEL = "gpt-4o"

SYSTEM_PROMPT = """당신은 K고등학교 학업성적관리규정 전문 도우미 "규정이"입니다.
아래 [관련 조항] 내용만 근거로 교사의 질문에 답변하세요.
- 조항 번호와 항목명을 명시하여 출처를 밝혀 주세요.
- 제공된 조항에 답이 없으면 반드시 "해당 내용은 규정에 명시되어 있지 않습니다"라고만 답하세요.
- 추측하거나 외부 지식을 사용하지 마세요."""
```

**GPT 메시지 구성 (대화 맥락 포함):**
```python
def _build_messages(question: str, chunks: list[dict], history: list[dict]) -> list[dict]:
    context = "\n\n".join(
        f"[{c['article_number']} {c['article_title']}]\n{c['chunk_text']}"
        for c in chunks
        if c.get("article_number")
    )
    system_with_context = f"{SYSTEM_PROMPT}\n\n[관련 조항]\n{context}"
    messages = [{"role": "system", "content": system_with_context}]
    # 이전 대화 이력 추가 (role: user/assistant)
    messages.extend(history)
    messages.append({"role": "user", "content": question})
    return messages
```

**sources 중복 제거:** 같은 article_number가 여러 청크에 걸쳐 나올 수 있으므로 sources에서 중복 제거:
```python
seen = set()
sources = []
for chunk in chunks:
    key = chunk.get("article_number")
    if key and key not in seen:
        seen.add(key)
        sources.append({
            "article_number": chunk["article_number"],
            "article_title": chunk.get("article_title"),
        })
```

### Task 3: chat.py 라우터 구현 가이드

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services import rag

router = APIRouter()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    question: str
    messages: list[Message] = []

class Source(BaseModel):
    article_number: str | None
    article_title: str | None

class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    history = [m.model_dump() for m in req.messages]
    result = rag.get_chat_answer(req.question, history)
    return ChatResponse(
        answer=result["answer"],
        sources=[Source(**s) for s in result["sources"]],
    )
```

- `response_model=ChatResponse`: FastAPI가 자동으로 응답 직렬화 + `/docs` 자동 문서화
- prefix 없음 → `POST /chat` 경로 (admin은 `/admin` prefix 있지만 chat은 최상위)

### Task 4: main.py 업데이트

기존 파일에서 2줄만 추가:
```python
# 기존
from routers import admin

# 추가
from routers import chat   # ← 이 줄 추가

# 기존
app.include_router(admin.router)

# 추가
app.include_router(chat.router)   # ← 이 줄 추가
```

### Task 5: test_chat.py 구현 가이드

```python
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

MOCK_ANSWER = {
    "answer": "제3조에 따르면 성적 이의신청 기간은 성적 통보 후 5일 이내입니다.",
    "sources": [{"article_number": "제3조", "article_title": "성적 이의신청"}],
}

MOCK_EMPTY_ANSWER = {
    "answer": "해당 내용은 규정에 명시되어 있지 않습니다",
    "sources": [],
}

def test_chat_response_structure():
    with patch("routers.chat.rag.get_chat_answer", return_value=MOCK_ANSWER):
        res = client.post("/chat", json={"question": "성적 이의신청 기간이 언제야?"})
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)

def test_chat_sources_have_required_fields():
    with patch("routers.chat.rag.get_chat_answer", return_value=MOCK_ANSWER):
        res = client.post("/chat", json={"question": "이의신청"})
    data = res.json()
    for source in data["sources"]:
        assert "article_number" in source
        assert "article_title" in source

def test_chat_no_relevant_content():
    with patch("routers.chat.rag.get_chat_answer", return_value=MOCK_EMPTY_ANSWER):
        res = client.post("/chat", json={"question": "오늘 날씨 어때?"})
    data = res.json()
    assert "규정에 명시되어 있지 않습니다" in data["answer"]
    assert data["sources"] == []
```

> **TestClient 사용 시 주의**: `main.py` lifespan에서 `ADMIN_PASSWORD` 환경변수를 검사합니다.
> TestClient 생성 전 환경변수를 설정하거나, conftest.py에서 `os.environ["ADMIN_PASSWORD"] = "test"` 처리 필요.

### 데이터 흐름 (이 스토리의 책임 범위)

```
POST /chat {"question": "...", "messages": [...]}
  → chat.py (ChatRequest 역직렬화)
  → rag.get_chat_answer(question, history)
    → embeddings.get_embedding(question)   [임베딩 재사용]
    → search_similar_chunks(query_embedding)
      → database.get_connection() + pgvector <=> 검색
    → chunks 없으면 즉시 반환 (GPT 미호출)
    → chunks 있으면 GPT-4o chat.completions.create()
  → ChatResponse {"answer": "...", "sources": [...]}
```

### 현재 코드베이스에서 재사용해야 할 패턴

| 패턴 | 위치 | 이 스토리 적용 방법 |
|------|------|---------------------|
| OpenAI 클라이언트 싱글턴 | `embeddings.py:7-17` | rag.py에서 동일한 `_client: T | None = None` 패턴 |
| DB 연결 컨텍스트 매니저 | `database.py:10-23` | `from db.database import get_connection` 그대로 사용 |
| EMBEDDING_MODEL 상수 | `embeddings.py:5` | `from services.embeddings import EMBEDDING_MODEL` |
| `get_embedding()` 함수 | `embeddings.py:34-36` | import 후 그대로 호출, 재구현 금지 |

### API 응답 형식 (Architecture 문서 AR-5 준수)

```json
// 정상 응답
{
  "answer": "제3조 제2항에 따르면...",
  "sources": [
    {"article_number": "제3조", "article_title": "성적 이의신청"}
  ]
}

// 관련 조항 없음
{
  "answer": "해당 내용은 규정에 명시되어 있지 않습니다",
  "sources": []
}
```

### 명명 규칙 준수 (Architecture 문서 AR-11)

- Python 함수/변수: `snake_case` — `get_chat_answer`, `search_similar_chunks`, `query_embedding`
- API 엔드포인트: 소문자 → `/chat`
- Pydantic 모델 클래스: PascalCase → `ChatRequest`, `ChatResponse`, `Source`, `Message`

### 환경변수 체크

이 스토리에서 새로 쓰는 환경변수 없음. 기존 변수 재사용:
- `OPENAI_API_KEY` — GPT-4o 및 임베딩 호출 (이미 embeddings.py에서 검증)
- `DATABASE_URL` — pgvector 검색 (이미 database.py에서 검증)

### 에러 처리 패턴 (Architecture 문서 준수)

```python
# 백엔드 에러: FastAPI HTTPException 사용
raise HTTPException(status_code=500, detail="RAG pipeline error")
# 응답: {"detail": "..."} 형식 자동 준수
```

DB가 비어있는 경우(문서 없음): `search_similar_chunks()`가 빈 리스트 반환 → "해당 내용은 규정에 명시되어 있지 않습니다" 정상 반환. 예외 발생 없음.

### References

- POST /chat 응답 형식: [Source: _bmad-output/planning-artifacts/epics.md#additional-requirements AR-5]
- EMBEDDING_MODEL 상수 위치: [Source: backend/services/embeddings.py:5]
- get_connection() 패턴: [Source: backend/db/database.py:10-23]
- ADMIN_PASSWORD lifespan 검사: [Source: backend/main.py:18-21]
- pgvector HNSW 인덱스: [Source: _bmad-output/planning-artifacts/architecture.md — 마이너 갭 섹션]
- GPT-4o 모델명: [Source: _bmad-output/planning-artifacts/architecture.md — AI: OpenAI GPT-4o]
- 코사인 유사도 검색 (`<=>`): [Source: _bmad-output/planning-artifacts/architecture.md — pgvector 스키마]
- 환각 방지 (유사도 임계값): [Source: _bmad-output/planning-artifacts/epics.md FR-1.4]
- 세션 대화 이력: [Source: _bmad-output/planning-artifacts/epics.md FR-1.5]
- test_chat.py TestClient 패턴: [Source: FastAPI 공식 문서 Testing — https://fastapi.tiangolo.com/tutorial/testing/]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `test_chat.py` 최초 작성 시 `scope="module"` fixture + context manager 방식 사용 → 전체 테스트 실행 시 `psycopg2.OperationalError` 발생. 원인: `test_admin.py`가 먼저 실행되어 `main` 모듈 캐시에 실제 DATABASE_URL이 로드된 상태에서 TestClient가 lifespan을 재시작하려 했기 때문. 해결: test_admin.py 패턴(`autouse` fixture + 모듈 레벨 `TestClient(app)`)으로 통일.

### Completion Notes List

- `backend/db/schema.sql`: HNSW 인덱스(`vector_cosine_ops`, m=16, ef_construction=64) 추가 — 순차 스캔 → 근사 최근접 이웃 검색으로 성능 개선
- `backend/services/rag.py` 신규 생성: `search_similar_chunks()` (pgvector `<=>` 코사인 거리, SIMILARITY_THRESHOLD=0.5), `get_chat_answer()` (임계값 이하 시 GPT 미호출 환각 방지, 이전 대화 이력 포함 GPT-4o 호출, 출처 중복 제거)
- `backend/routers/chat.py` 신규 생성: Pydantic 모델 4개(Message, ChatRequest, Source, ChatResponse), `POST /chat` 엔드포인트 (인증 없음)
- `backend/main.py` 업데이트: chat 라우터 import + include 2줄 추가
- `backend/tests/test_chat.py` 신규 생성: 5개 테스트 (응답 구조, sources 필드, 관련 조항 없음, 대화 이력 전달, 빈 질문) — 전체 65개 테스트 모두 통과

### File List

- `backend/db/schema.sql` (수정)
- `backend/services/rag.py` (신규)
- `backend/routers/chat.py` (신규)
- `backend/main.py` (수정)
- `backend/tests/test_chat.py` (신규)

### Change Log

- 2026-06-04: Story 2.1 구현 완료 — RAG 파이프라인(rag.py), POST /chat 엔드포인트(chat.py), HNSW 인덱스(schema.sql), 테스트 5개(test_chat.py)
