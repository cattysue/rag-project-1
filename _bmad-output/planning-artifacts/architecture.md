---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-06-03'
inputDocuments:
  - '_bmad-output/planning-artifacts/prds/prd-rag-project-1-2026-06-03/prd.md'
workflowType: 'architecture'
project_name: 'rag-project-1'
user_name: 'Catty'
date: '2026-06-03'
---

# Architecture Decision Document
## K고 학업성적관리규정 RAG 챗봇 "규정이"

_이 문서는 단계별 협업 발견을 통해 점진적으로 구축됩니다. 각 아키텍처 결정을 함께 논의하며 섹션을 추가합니다._

---

## 프로젝트 컨텍스트 분석

### 요구사항 개요

**기능 요구사항:**
- FR-1 (질문-답변): 한국어 자연어 입력 → 벡터 검색 → AI 답변 + 출처 조항 표시. 유사도 임계값 기반 환각 방지. 세션 내 대화 맥락 유지.
- FR-2 (문서 관리): 관리자 전용 페이지(비밀번호 보호), PDF 업로드 → 자동 임베딩 처리 → 상태 표시. 파일 교체 가능.
- FR-3 (웹 인터페이스): 로그인 없이 링크만으로 접속. 반응형 디자인(PC·모바일 모두 지원).

**비기능 요구사항:**
- 성능: 답변 10초 이내, 동시 사용자 최대 20명
- 가용성: Railway 24/7 배포
- 보안: 관리자 비밀번호, 환경변수 기반 API 키 관리, HTTPS
- 검색 품질: 배포 전 샘플 질문 20개, 정확도 80% 이상 검증

**규모 및 복잡도:**
- 주요 도메인: 풀스택 웹 + AI/ML RAG 파이프라인
- 복잡도 수준: 낮음~중간 (내부 도구, 소규모)
- 예상 아키텍처 컴포넌트: 6~7개

### 기술 제약 및 의존성

이미 확정된 기술 스택:
- 백엔드: FastAPI (Python)
- 데이터베이스: PostgreSQL + pgvector
- 프론트엔드: Next.js (React, 반응형)
- AI: OpenAI GPT-4o + text-embedding-3-small
- 배포: Railway

### 횡단 관심사

- **한국어 법규 텍스트 처리**: 조항 번호 구조를 고려한 PDF 청킹 전략
- **비동기 임베딩 처리**: PDF 업로드 후 처리 상태 관리
- **환경변수 기반 설정**: API 키, 관리자 비밀번호 등 민감 정보
- **에러 처리**: OpenAI API 실패, PDF 파싱 오류 등 경계 상황

---

## 스타터 템플릿 평가

### 주요 기술 도메인

풀스택 웹 + AI/ML RAG 파이프라인 (기술 스택 PRD에서 이미 확정)

### 선택된 초기화 방식

**프론트엔드 — Next.js:**
```bash
npx create-next-app@latest frontend
# TypeScript: Yes / ESLint: Yes / Tailwind CSS: Yes / src/: Yes / App Router: Yes
```
선택 이유: 반응형 디자인 구현에 Tailwind CSS가 최적. App Router는 Next.js 최신 표준.

**백엔드 — FastAPI (Python):**
```bash
mkdir backend && cd backend
python -m venv venv
pip install fastapi uvicorn python-multipart openai pgvector psycopg2-binary python-dotenv
```
폴더 구조: `routers/` (chat, admin), `services/` (rag, embeddings, pdf), `db/`

**데이터베이스 — Docker + PostgreSQL + pgvector:**
```bash
docker-compose up -d
```

**참고:** 프로젝트 초기화(위 명령어 실행)는 첫 번째 구현 스토리가 된다.

---

## 핵심 아키텍처 결정

### 결정 우선순위 분석

**구현 차단 핵심 결정:**
- RAG 파이프라인 설계 (조항 단위 청킹 → 벡터 검색 → 일괄 답변)
- Railway 분리 배포 구조

**아키텍처를 형성하는 중요 결정:**
- 답변 표시: 일괄 응답 (스트리밍 없음) → 단순 POST/JSON 방식
- 청킹: 조항 단위 ("제○조" 패턴 파싱)

### 데이터 아키텍처

**PDF 청킹 전략: 조항 단위**
- "제○조" 정규식으로 조항 경계 감지, 조항별 독립 청크 저장
- 조항 번호·항목명을 메타데이터로 함께 저장 → 출처 표시에 직접 활용
- 폴백: 서문·부칙 등 조항 구분 없는 영역은 단락 단위 처리

**pgvector 스키마:**
```
documents 테이블:
  id (PK), chunk_text, embedding (vector 1536차원),
  article_number, article_title, page_number, created_at
```

### 인증 및 보안

- 일반 사용자: 인증 없음 (링크 접속)
- 관리자: ADMIN_PASSWORD 환경변수와 요청 헤더 비교
- 민감 정보 전체: 환경변수 관리 (OPENAI_API_KEY, DATABASE_URL, ADMIN_PASSWORD)
- HTTPS: Railway 기본 제공

### API 및 통신 패턴

- 설계: REST API, FastAPI 자동 문서(/docs) 활용
- 답변: 일괄 응답 (POST /chat → 완성된 JSON 반환, 스트리밍 없음)
- 주요 엔드포인트:
  - `POST /chat` — 질문 → 답변 + 출처 조항 반환
  - `POST /admin/upload` — PDF 업로드 (Authorization 헤더)
  - `GET /admin/status` — 임베딩 처리 상태 조회

### 프론트엔드 아키텍처

- 상태 관리: React useState (소규모, Redux 불필요)
- 대화 이력: 브라우저 메모리만 (새로고침 시 초기화)
- 반응형: Tailwind CSS 브레이크포인트

### 인프라 및 배포

- **구조: 분리형** — `backend/`와 `frontend/` 각각 독립 폴더
- Railway 배포: 백엔드 서비스(FastAPI) + 프론트엔드 서비스(Next.js) + PostgreSQL 플러그인
- 로컬 개발: Docker로 PostgreSQL만 실행, 나머지 직접 실행

**구현 순서:**
1. DB 스키마 + Docker 설정
2. PDF 파싱·청킹·임베딩 파이프라인
3. 벡터 검색 + 답변 생성 API
4. 관리자 업로드 API
5. Next.js 채팅 UI
6. Railway 배포

---

## 구현 패턴 및 일관성 규칙

### 명명 규칙

| 영역 | 규칙 | 예시 |
|------|------|------|
| DB 테이블·컬럼 | snake_case | `documents`, `chunk_text`, `article_number` |
| Python 함수·변수 | snake_case | `get_similar_chunks()`, `process_pdf()` |
| JS/TS 변수 | camelCase | `isLoading`, `chatMessages` |
| React 컴포넌트 | PascalCase | `ChatMessage`, `AdminUpload` |
| API 엔드포인트 | 소문자 kebab | `/chat`, `/admin/upload`, `/admin/status` |

### API 응답 형식 (표준)

```json
// POST /chat 성공
{ "answer": "제3조 제2항에 따르면...", "sources": [{ "article_number": "제3조", "article_title": "성적 이의신청" }] }

// 에러 (FastAPI 기본)
{ "detail": "에러 메시지" }

// GET /admin/status
{ "status": "processing" }  // processing | completed | failed
```

### 에러 처리 패턴

- **백엔드**: `raise HTTPException(status_code=XXX, detail="영문 메시지")`
- **프론트엔드**: catch 블록에서 한국어 안내 메시지 표시

### 로딩 상태 패턴

- 채팅: `isLoading` boolean → 전송 버튼 비활성화 + 스피너
- 관리자 업로드: 2초 간격 폴링으로 `/admin/status` 조회

### AI 에이전트 필수 준수 사항

1. DB·Python은 snake_case / JS·TS는 camelCase 엄수
2. API 에러는 반드시 `{ "detail": "..." }` 형식 통일
3. 환경변수는 `.env` 파일에만 — 코드에 하드코딩 절대 금지
4. 한국어 메시지는 프론트엔드 전담, 백엔드는 영문 로그

---

## 프로젝트 구조 및 경계

### FR → 디렉토리 매핑

| 기능 그룹 | 위치 |
|-----------|------|
| FR-1 (질문-답변) | `backend/routers/chat.py`, `backend/services/rag.py` |
| FR-2 (문서 관리) | `backend/routers/admin.py`, `backend/services/pdf.py`, `backend/services/embeddings.py` |
| FR-3 (웹 UI) | `frontend/src/app/`, `frontend/src/components/` |

### 완성된 프로젝트 디렉토리 구조

```
rag-project-1/
├── docker-compose.yml
├── .gitignore
├── README.md
│
├── backend/
│   ├── main.py                     ← FastAPI 앱 진입점, CORS 설정
│   ├── requirements.txt
│   ├── .env
│   ├── .env.example
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── chat.py                 ← POST /chat
│   │   └── admin.py                ← POST /admin/upload, GET /admin/status
│   ├── services/
│   │   ├── __init__.py
│   │   ├── rag.py                  ← 벡터 검색 + GPT 답변 생성
│   │   ├── embeddings.py           ← OpenAI 임베딩 호출
│   │   └── pdf.py                  ← PDF 파싱 + 조항 단위 청킹
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py             ← PostgreSQL 연결, pgvector 초기화
│   │   └── schema.sql              ← documents 테이블 DDL
│   └── tests/
│       ├── test_chat.py
│       ├── test_admin.py
│       └── test_pdf_chunking.py
│
└── frontend/
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.js
    ├── tsconfig.json
    ├── .env.local
    ├── .env.example
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   ├── page.tsx            ← 채팅 메인 페이지
        │   ├── globals.css
        │   └── admin/
        │       └── page.tsx        ← 관리자 업로드 페이지
        ├── components/
        │   ├── chat/
        │   │   ├── ChatWindow.tsx
        │   │   ├── ChatMessage.tsx ← 출처 조항 표시 포함
        │   │   └── ChatInput.tsx
        │   └── admin/
        │       └── FileUpload.tsx
        └── lib/
            ├── api.ts              ← 백엔드 API 호출 함수
            └── types.ts            ← TypeScript 타입 정의
```

### 데이터 흐름

```
교사 질문
  → ChatInput.tsx → lib/api.ts (POST /chat)
  → backend/routers/chat.py
  → backend/services/rag.py (pgvector 유사도 검색 → GPT-4o 호출)
  → { answer, sources } 반환
  → ChatMessage.tsx (출처 조항 강조 표시)

관리자 PDF 업로드
  → FileUpload.tsx → lib/api.ts (POST /admin/upload)
  → backend/routers/admin.py
  → backend/services/pdf.py (조항 단위 청킹)
  → backend/services/embeddings.py (OpenAI 임베딩)
  → db/database.py (pgvector 저장)
  → { status: completed }
```

### 환경변수 목록

**backend/.env:**
```
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://user:pass@localhost:5432/ragdb
ADMIN_PASSWORD=your-secure-password
```

**frontend/.env.local:**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 아키텍처 검증 결과

### 일관성 검증 ✅
모든 기술 호환성 확인. 명명 규칙·API 응답 형식 전 영역 통일.

### 요구사항 커버리지 ✅
FR 14개 항목 전체, NFR 6개 항목 전체 아키텍처 지원 확인.

### 아키텍처 완성도 체크리스트 (16/16)
- [x] 프로젝트 컨텍스트 분석 완료
- [x] 규모·복잡도 평가 (낮음~중간, 20명)
- [x] 기술 제약 식별
- [x] 횡단 관심사 매핑
- [x] 핵심 결정 문서화
- [x] 기술 스택 전체 명세
- [x] 통합 패턴 정의
- [x] 성능 고려사항 반영
- [x] 명명 규칙 수립
- [x] 구조 패턴 정의
- [x] 통신 패턴 명세
- [x] 프로세스 패턴 문서화
- [x] 완전한 디렉토리 구조
- [x] 컴포넌트 경계 수립
- [x] 통합 지점 매핑
- [x] FR → 구조 매핑 완료

**전체 상태: READY FOR IMPLEMENTATION**

### 마이너 갭 (구현 시 주의)
- `main.py` CORS 설정에 Railway 프론트엔드 URL 허용 오리진 명시
- PDF 파싱 라이브러리: `pypdf` 또는 `pdfplumber` 권장
- FR-2.5 파일 교체: 기존 벡터 전체 삭제 후 재임베딩 순서 준수

### 구현 핸드오프 — 첫 실행 순서
```bash
# 1. Docker PostgreSQL 시작
docker-compose up -d

# 2. 백엔드 환경 구성
cd backend && python -m venv venv
pip install fastapi uvicorn python-multipart openai pgvector psycopg2-binary python-dotenv

# 3. 프론트엔드 초기화
npx create-next-app@latest frontend
# (TypeScript: Yes / Tailwind: Yes / App Router: Yes)
```
