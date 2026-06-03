# Story 1.2: 데이터베이스 스키마 및 pgvector 초기화

Status: review

## Story

As a 시스템,
I want documents 테이블과 pgvector 확장이 데이터베이스에 초기화되어 있는 상태를,
so that 규정 청크와 임베딩 벡터를 저장하고 유사도 검색을 수행할 수 있다.

## Acceptance Criteria

1. **Given** Docker PostgreSQL이 실행 중일 때 **When** `database.py`의 초기화 함수를 실행하면 **Then** pgvector 확장이 활성화되고 `documents` 테이블이 생성된다
2. **Given** `documents` 테이블이 생성되었을 때 **When** 테이블 스키마를 확인하면 **Then** `id(PK)`, `chunk_text`, `embedding(vector(1536))`, `article_number`, `article_title`, `page_number`, `created_at` 컬럼이 모두 존재한다
3. **Given** 테이블이 이미 존재할 때 **When** 초기화 함수를 다시 실행하면 **Then** 오류 없이 정상 완료된다 (IF NOT EXISTS로 멱등성 보장)

## Tasks / Subtasks

- [x] Task 1: `backend/db/schema.sql` 작성 (AC: #1, #2, #3)
  - [x] `CREATE EXTENSION IF NOT EXISTS vector;` 추가
  - [x] `documents` 테이블 DDL 작성 (7개 컬럼, IF NOT EXISTS)
  - [x] 코사인 유사도 검색용 인덱스 생성문 추가 (IF NOT EXISTS)

- [x] Task 2: `backend/db/database.py` 작성 (AC: #1, #2, #3)
  - [x] `get_connection()` 함수 구현 (psycopg2 + pgvector register)
  - [x] `init_db()` 함수 구현 (schema.sql 읽어서 실행)
  - [x] `DATABASE_URL` 환경변수 로드 (`python-dotenv` 사용)

- [x] Task 3: `backend/main.py` 수정 — 앱 시작 시 DB 초기화 연결 (AC: #1)
  - [x] FastAPI lifespan 이벤트에 `init_db()` 호출 추가

- [x] Task 4: 검증 (AC: #1, #2, #3)
  - [x] pytest 11 passed (schema.sql 내용 검증, mock DB로 init_db 동작 검증)
  - [x] IF NOT EXISTS 2개 이상 확인 (멱등성 테스트 통과)
  - [x] 오류 발생 시에도 conn.close() 호출 확인 (finally 블록 테스트 통과)

## Dev Notes

### 이전 스토리(1.1)에서 구축된 기반 — 반드시 활용

Story 1.1이 이미 완료되어 아래 환경이 갖춰져 있음:
- `docker-compose.yml`: `pgvector/pgvector:pg15` 이미지 사용 → **pgvector 확장 이미 컨테이너에 포함**, 별도 설치 불필요
- `backend/.env`: `DATABASE_URL=postgresql://raguser:ragpass@localhost:5432/ragdb` 설정됨
- `backend/db/__init__.py`: 빈 파일로 생성됨 → 패키지 인식 가능 상태
- `requirements.txt`: `pgvector==0.3.5`, `psycopg2-binary==2.9.10`, `python-dotenv==1.0.1` 이미 설치됨
- `backend/main.py`: FastAPI 앱 기본 구조 존재 → Task 3에서 수정 필요

### 이 스토리에서 생성/수정되는 파일

```
backend/
├── main.py                 ← UPDATE: lifespan 이벤트 추가
└── db/
    ├── __init__.py         ← 기존 유지 (수정 없음)
    ├── database.py         ← NEW
    └── schema.sql          ← NEW
```

### backend/db/schema.sql 전체 내용

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id          SERIAL PRIMARY KEY,
    chunk_text  TEXT NOT NULL,
    embedding   vector(1536),
    article_number  VARCHAR(50),
    article_title   VARCHAR(200),
    page_number     INTEGER,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS documents_embedding_idx
    ON documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

> **인덱스 참고:** `ivfflat`는 대용량 데이터에 효과적. 초기 데이터 0건일 때 인덱스를 먼저 생성해도 동작하지만, `VACUUM ANALYZE` 후 효율이 향상됨. 학교 규정 문서 규모(수십~수백 청크)에서는 인덱스 없이도 충분히 빠름 — 인덱스는 미래 확장 대비.

### backend/db/database.py 전체 구현

```python
import os
import psycopg2
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    register_vector(conn)
    return conn


def init_db():
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()
    finally:
        conn.close()
```

**주요 설계 결정:**
- `get_connection()`: 이후 모든 DB 접근(Story 1.4 임베딩 저장, Story 2.1 벡터 검색)에서 이 함수를 재사용. 중복 커넥션 로직 작성 금지.
- `register_vector(conn)`: pgvector Python 패키지가 `vector` 타입을 psycopg2가 이해할 수 있도록 등록. **빠뜨리면 벡터 저장/조회 시 타입 오류 발생** — 반드시 포함.
- `schema.sql` 경로: `os.path.dirname(__file__)`으로 `database.py`와 같은 폴더의 `schema.sql`을 참조 — 실행 위치에 무관하게 안전.

### backend/main.py 수정 내용 (기존 코드 변경)

Story 1.1에서 만든 `main.py`에 lifespan 이벤트 추가:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="규정이 API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}
```

> **변경점:** `@asynccontextmanager lifespan` 패턴은 FastAPI 0.93+ 공식 권장 방식 (`@app.on_event("startup")`은 deprecated). `requirements.txt`의 `fastapi==0.115.5`에서 완전 지원됨.

### 명명 규칙 준수 (아키텍처 필수)

| 항목 | 적용 |
|------|------|
| 테이블명 | `documents` (snake_case) |
| 컬럼명 | `chunk_text`, `article_number`, `article_title`, `page_number`, `created_at` (snake_case) |
| Python 함수 | `get_connection()`, `init_db()` (snake_case) |

### 검증 방법

```bash
# 1. Docker 컨테이너 실행 확인
docker-compose up -d
docker ps  # db 컨테이너 Up 상태 확인

# 2. FastAPI 서버 시작 — lifespan에서 init_db() 자동 호출
cd backend
venv\Scripts\activate  # Windows
uvicorn main:app --reload
# 터미널에 오류 없이 "Application startup complete" 출력되어야 함

# 3. 테이블 스키마 확인 (psql 직접 접속)
docker exec -it <컨테이너_이름> psql -U raguser -d ragdb
\d documents  # 컬럼 목록 확인
\q

# 4. 멱등성 확인 — 서버를 껐다 켜도 오류 없음
# Ctrl+C로 서버 중단 후 uvicorn main:app --reload 재실행
# "Application startup complete" 다시 출력되어야 함
```

> **컨테이너 이름 확인:** `docker ps` 결과의 NAMES 컬럼 참고 (보통 `rag-project-1-db-1` 형태)

### 후속 스토리와의 연결 (미리 알아두기)

- **Story 1.4** (임베딩 저장): `get_connection()`으로 커넥션 가져와 `documents` 테이블에 INSERT
- **Story 2.1** (벡터 검색): `get_connection()`으로 커넥션 가져와 코사인 유사도 쿼리 실행
- **Story 1.5** (관리자 업로드): `DELETE FROM documents` 후 재임베딩 시 이 스키마 사용

→ `get_connection()`과 `init_db()` 함수 시그니처를 변경하지 말 것 (후속 스토리 의존성 있음)

### Project Structure Notes

- `database.py`는 `backend/db/` 폴더 안에 위치 — `backend/` 루트에 두지 말 것
- `schema.sql`도 `backend/db/` 폴더 안에 위치 — `database.py`와 같은 폴더여야 경로 참조 정상 동작
- `main.py`에서 `from db.database import init_db` import 시 `backend/` 폴더를 기준으로 실행해야 함 (uvicorn을 `backend/` 폴더 안에서 실행)

### References

- DB 스키마 명세: [Source: _bmad-output/planning-artifacts/architecture.md#데이터-아키텍처]
- AR-3 (DB 스키마): [Source: _bmad-output/planning-artifacts/epics.md#additional-requirements]
- AR-11 (명명 규칙): [Source: _bmad-output/planning-artifacts/epics.md#additional-requirements]
- 이전 스토리 환경 기반: [Source: _bmad-output/implementation-artifacts/1-1-프로젝트-초기화-및-개발-환경-구성.md]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

- patch("db.database") 오류 → database.py 없을 때 AttributeError 발생 (정상 RED 확인)
- test_main.py에 `no_db_init` autouse fixture 추가 — lifespan이 실제 DB 연결 시도하지 않도록 처리

### Completion Notes List

- schema.sql: 7개 컬럼, IF NOT EXISTS, ivfflat 인덱스 포함
- database.py: get_connection() + init_db(), register_vector() 필수 포함
- main.py: lifespan(asynccontextmanager) 패턴으로 앱 시작 시 init_db() 자동 호출
- test_main.py: autouse mock fixture로 DB 없이 기존 테스트 유지
- pytest 11 passed (backend/ 및 프로젝트 루트 양쪽)
- AC #1~#3의 실제 DB 연동 검증은 docker-compose up -d 후 uvicorn 실행으로 수동 확인 가능

### File List

- `backend/db/schema.sql` (NEW)
- `backend/db/database.py` (NEW)
- `backend/main.py` (UPDATED: lifespan + init_db import 추가)
- `backend/tests/test_db.py` (NEW)
- `backend/tests/test_main.py` (UPDATED: no_db_init fixture 추가)
