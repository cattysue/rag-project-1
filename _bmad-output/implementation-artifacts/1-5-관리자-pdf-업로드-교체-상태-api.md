# Story 1.5: 관리자 PDF 업로드·교체·상태 API

Status: review

## Story

As a 관리자,
I want PDF 업로드·교체·처리 상태 조회 백엔드 API를,
so that 새 규정 파일을 시스템에 적용하고 처리 완료 여부를 API로 확인할 수 있다.

## Acceptance Criteria

1. **Given** 올바른 ADMIN_PASSWORD가 Authorization 헤더에 포함된 요청일 때 **When** `POST /admin/upload`에 PDF 파일을 업로드하면 **Then** `{"status": "processing"}` 응답을 즉시 반환하고 백그라운드에서 임베딩 처리가 시작된다
2. **Given** 잘못된 비밀번호가 Authorization 헤더에 포함된 요청일 때 **When** `POST /admin/upload`를 호출하면 **Then** HTTP 401과 `{"detail": "Unauthorized"}`가 반환된다
3. **Given** PDF 처리가 진행 중이거나 완료·실패한 상태일 때 **When** `GET /admin/status`를 호출하면 **Then** `{"status": "processing"}` 또는 `"completed"` 또는 `"failed"` 중 하나가 반환된다
4. **Given** 기존 문서가 데이터베이스에 존재하는 상태에서 **When** 새 PDF 파일로 업로드하면 **Then** 기존 documents 테이블의 모든 행을 먼저 삭제한 후 새 파일의 청크를 임베딩하여 저장한다
5. **Given** PDF가 아닌 파일 형식이 업로드된 경우 **When** `POST /admin/upload`를 호출하면 **Then** HTTP 400과 오류 메시지가 반환된다

## Tasks / Subtasks

- [x] Task 1: `backend/routers/admin.py` 작성 (AC: #1, #2, #3, #4, #5)
  - [x] `POST /admin/upload` — Authorization 검증, 파일 형식 검증, 백그라운드 처리 시작
  - [x] `GET /admin/status` — 현재 처리 상태 반환
  - [x] `_process_pdf()` — 백그라운드 태스크 함수 (parse → embed → replace_documents)

- [x] Task 2: `backend/main.py` 수정 — 라우터 등록 (AC: #1~#5)
  - [x] `app.include_router(admin.router)` 추가

- [x] Task 3: `backend/tests/test_admin.py` 작성 (AC: #1~#5)
  - [x] 올바른 비밀번호로 업로드 → 200 + {"status": "processing"}
  - [x] 잘못된 비밀번호 → 401
  - [x] Authorization 헤더 없음 → 401
  - [x] PDF 아닌 파일 → 400
  - [x] GET /admin/status → 상태 반환

- [x] Task 4: 전체 테스트 실행 — 기존 44개 + 신규 모두 통과

## Dev Notes

### 이전 스토리에서 확립된 패턴 — 반드시 준수

- `load_dotenv()` 금지 — `admin.py`는 환경변수를 `os.getenv()`로만 읽음
- `replace_documents(chunks, embeddings)` 사용 — Story 1.4에서 구현된 **원자적** 교체 함수. `clear_documents()` + `save_chunks()` 개별 호출 금지 (트랜잭션 분리로 데이터 소실 위험)
- `get_embeddings(texts: list[str])` 배치 함수 사용 — Story 1.4에서 구현. `get_embedding()` 루프 호출 금지
- `EMBEDDING_MODEL` 상수는 `services.embeddings`에서 임포트 (Story 1.4)
- `parse_pdf(file_content: bytes)` — Story 1.3에서 구현

### 이 스토리에서 생성/수정되는 파일

```
backend/
├── main.py              ← UPDATE: include_router(admin.router) 추가
├── routers/
│   ├── __init__.py      ← 기존 빈 파일, 수정 없음
│   └── admin.py         ← NEW
└── tests/
    └── test_admin.py    ← NEW
```

### backend/routers/admin.py 전체 구현

```python
import os
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, UploadFile

from db.database import replace_documents
from services.embeddings import get_embeddings
from services.pdf import parse_pdf

router = APIRouter(prefix="/admin")

# 서버 내 처리 상태 (단일 관리자 사용 환경에서 인메모리로 충분)
_upload_status: dict[str, str] = {"status": "idle"}


def _check_auth(authorization: str | None) -> None:
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_password or authorization != admin_password:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _process_pdf(file_content: bytes) -> None:
    try:
        chunks = parse_pdf(file_content)
        texts = [c["chunk_text"] for c in chunks]
        embeddings = get_embeddings(texts)
        replace_documents(chunks, embeddings)
        _upload_status["status"] = "completed"
    except Exception:
        _upload_status["status"] = "failed"


@router.post("/upload")
async def upload_pdf(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
):
    _check_auth(authorization)

    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다")

    content = await file.read()
    _upload_status["status"] = "processing"
    background_tasks.add_task(_process_pdf, content)
    return {"status": "processing"}


@router.get("/status")
async def get_status():
    return _upload_status
```

### backend/main.py 수정 내용

기존 파일에 라우터 임포트 + include_router 추가:

```python
from routers import admin          # 추가
...
app.include_router(admin.router)   # add_middleware 아래에 추가
```

### 설계 결정 및 주의사항

| 항목 | 결정 | 이유 |
|------|------|------|
| 인증 방식 | Authorization 헤더 = ADMIN_PASSWORD 값 직접 비교 | AR-4 명세. Bearer 토큰 불필요 (단일 사용자) |
| 처리 방식 | FastAPI BackgroundTasks | 즉시 응답 후 비동기 처리 (AR-5) |
| 상태 추적 | 모듈 수준 dict (`_upload_status`) | 단일 관리자, 재시작 시 초기화 허용 |
| PDF 교체 | `replace_documents()` 단일 호출 | Story 1.4 원자성 보장 함수 |
| 파일 검증 | `.pdf` 확장자 확인 | content-type은 클라이언트가 위조 가능 |
| 빈 chunks | `replace_documents([], [])` 허용 | 빈 PDF도 처리 완료로 간주 (문서 초기화) |

### 테스트 작성 시 주의사항

`_process_pdf()` 는 백그라운드에서 실행됩니다. TestClient는 `with TestClient(app) as client:` 형태로 사용해야 lifespan + 백그라운드 태스크가 완료됩니다.

단, 백그라운드 태스크의 완료 타이밍을 테스트에서 기다리기 어려우므로:
- **즉시 응답 검증**: `{"status": "processing"}` 반환 확인 (동기적으로 검증 가능)
- **처리 결과 검증**: `_process_pdf`를 모킹하여 호출 여부만 확인
- `_upload_status` 딕셔너리를 직접 패치하여 상태 테스트

```python
# 백그라운드 태스크 모킹 패턴
with patch("routers.admin._process_pdf") as mock_process:
    response = client.post("/admin/upload", ...)
    assert response.status_code == 200
    mock_process.assert_called_once()
```

### backend/tests/test_admin.py 주요 구조

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app

# init_db mock (기존 test_main.py 패턴)
@pytest.fixture(autouse=True)
def no_db_init():
    with patch("main.init_db"):
        yield

client = TestClient(app)
VALID_PASSWORD = "test-password"

@pytest.fixture(autouse=True)
def set_admin_password(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", VALID_PASSWORD)


def _pdf_upload(password=VALID_PASSWORD, filename="규정.pdf"):
    return client.post(
        "/admin/upload",
        files={"file": (filename, b"%PDF-1.4 fake content", "application/pdf")},
        headers={"Authorization": password} if password else {},
    )
```

### AR-9 구현 확인

AR-9: "기존 벡터 데이터 전체 삭제 후 새 파일 재임베딩 순서 준수"

Story 1.4의 `replace_documents()` 내부:
```sql
DELETE FROM documents;   -- 먼저 전체 삭제
INSERT INTO documents ...; -- 새 데이터 저장
COMMIT;  -- 단일 트랜잭션
```
→ AR-9 요구사항을 원자적으로 충족.

### References

- AR-4 (관리자 인증): [Source: _bmad-output/planning-artifacts/epics.md#additional-requirements]
- AR-5 (API 응답 형식): [Source: _bmad-output/planning-artifacts/epics.md#additional-requirements]
- AR-6 (로딩 상태/폴링): [Source: _bmad-output/planning-artifacts/epics.md#additional-requirements]
- AR-9 (파일 교체 순서): [Source: _bmad-output/planning-artifacts/epics.md#additional-requirements]
- replace_documents() 원자성: [Source: _bmad-output/implementation-artifacts/1-4-openai-임베딩-및-벡터-저장-파이프라인.md]
- get_embeddings() 배치: [Source: _bmad-output/implementation-artifacts/1-4-openai-임베딩-및-벡터-저장-파이프라인.md]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- 초기 테스트 실행 시 `dotenv`, `openai`, `pypdf` 등 의존성 미설치 상태였음 → `pip install -r requirements.txt`로 해결

### Completion Notes List

- `backend/routers/admin.py` 신규 생성: `POST /admin/upload`, `GET /admin/status` 엔드포인트 구현
- Authorization 헤더 직접 비교 방식으로 관리자 인증 (AR-4)
- FastAPI BackgroundTasks로 즉시 응답 후 비동기 PDF 처리 (AR-5)
- `replace_documents()` 단일 호출로 기존 문서 원자적 교체 (AR-9, Story 1.4 패턴 준수)
- `_upload_status` 모듈 수준 dict로 단일 처리 상태 추적
- 13개 신규 테스트 + 기존 44개 = 57개 전체 통과

### File List

- `backend/routers/admin.py` (신규)
- `backend/main.py` (수정: `from routers import admin` + `app.include_router(admin.router)`)
- `backend/tests/test_admin.py` (신규)

### Change Log

- 2026-06-03: Story 1.5 구현 완료 — 관리자 PDF 업로드·교체·상태 API (backend/routers/admin.py, backend/tests/test_admin.py, backend/main.py 수정)
