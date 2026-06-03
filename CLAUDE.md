# CLAUDE.md — 학업성적관리규정 RAG 챗봇 프로젝트

## 이 파일이 무엇인가요?
CLAUDE.md는 AI 어시스턴트(Claude)가 이 프로젝트를 도울 때 항상 참고하는 **프로젝트 안내서**입니다.
새 대화를 시작할 때마다 Claude가 이 파일을 읽고, 무슨 프로젝트인지, 어떻게 도와야 하는지 파악합니다.

---

## 프로젝트 개요

**목표**: 고등학교 학업성적관리규정(PDF) 내용을 쉽게 검색할 수 있는 RAG 챗봇 만들기

**RAG란?** (Retrieval-Augmented Generation)
문서를 AI가 읽어두고, 사용자가 질문하면 관련 내용을 찾아서(Retrieval=검색) + AI가 답변 생성(Generation=생성)하는 방식입니다.
예: "1학기 성적 이의신청 기간이 언제야?" → AI가 규정 문서에서 해당 부분을 찾아 답변

---

## 기술 스택 (사용하는 도구들)

| 역할 | 도구 | 쉬운 설명 |
|------|------|-----------|
| 데이터베이스 | PostgreSQL + pgvector | 문서 내용과 벡터(숫자 형태로 변환된 의미)를 저장하는 창고 |
| DB 실행 환경 | Docker | 내 컴퓨터에 PostgreSQL을 가상으로 설치·실행하는 컨테이너 |
| 백엔드 | FastAPI (Python) | 챗봇의 두뇌 역할, 검색·AI 호출·응답 처리 |
| 웹 프론트엔드 | Next.js (React) | 웹 브라우저에서 보이는 채팅 화면 |
| 모바일 앱 | Flutter (Dart) | 스마트폰 앱 화면 |
| AI 모델 | OpenAI GPT | 질문에 답변을 생성하는 AI |
| 임베딩 | OpenAI Embeddings | 문서 내용을 숫자(벡터)로 변환하는 도구 |
| 배포 | Railway | 완성된 앱을 인터넷에 올려서 누구나 쓸 수 있게 하는 서비스 |

> **벡터(Vector)란?** 텍스트의 의미를 숫자 배열로 표현한 것. 예: "성적" = [0.2, 0.8, 0.1, ...]
> 비슷한 의미일수록 숫자들이 비슷해져서, 관련 문서를 찾는 데 씁니다.

---

## 개발 방법론: BMad Method

**BMad란?** 전문 AI 에이전트들이 단계별로 소프트웨어를 만들어주는 개발 프레임워크.
비개발자도 체계적으로 앱을 만들 수 있도록 단계를 나눠줍니다.
공식 문서: https://docs.bmad-method.org/tutorials/getting-started/

### BMad 개발 4단계

```
1단계: 분석 (Analysis)    → 무엇을 만들지 조사·구상
2단계: 계획 (Planning)    → 요구사항 문서(PRD) 작성
3단계: 설계 (Solutioning) → 기술 구조 설계, 할 일 목록(스토리) 작성
4단계: 구현 (Implementation) → 스토리 하나씩 코드로 개발
```

### BMad 주요 에이전트 (전문가 AI들)

- **Analyst (분석가)**: 조사·아이디어 정리
- **PM (제품 관리자)**: 요구사항 문서 작성
- **Architect (설계자)**: 기술 구조 설계
- **Developer (개발자)**: 실제 코드 구현
- **UX Designer (디자이너)**: 화면 디자인

> **중요**: BMad는 각 단계마다 **새 대화(fresh chat)** 에서 시작해야 합니다.
> 한 대화에서 너무 길어지면 AI 품질이 떨어지기 때문입니다.

---

## 현재 진행 단계

- [x] 프로젝트 아이디어 확정
- [x] 기술 스택 결정
- [x] CLAUDE.md 작성
- [x] BMad 설치 완료 (v6.8.0)
- [x] 프로젝트 폴더 구조 확정
- [x] PRD 작성 완료 → `_bmad-output/planning-artifacts/prds/prd-rag-project-1-2026-06-03/prd.md`
- [x] 기술 아키텍처 설계 완료 → `_bmad-output/planning-artifacts/architecture.md`
- [ ] **현재**: 에픽 및 스토리 작성 중 (요구사항 추출 완료, "C" 입력 후 에픽 설계 단계 진입)
- [ ] 스프린트 계획 수립
- [ ] 단계별 코드 구현

### 챗봇 이름: "규정이"
- 사용자: K고 교사 (로그인 없음)
- 관리자: 비밀번호 보호 (환경변수)
- AI: OpenAI GPT-4o + text-embedding-3-small

---

## Claude가 지켜야 할 가이드라인

### 1. 비개발자 친화적 설명
- 새로운 기술 용어가 나오면 **반드시** 쉬운 말로 설명 추가
- 예시 형식:
  - `cd` (change directory) = 폴더 이동 명령어. `cd backend`는 "backend 폴더로 이동"
  - `pwd` (print working directory) = 현재 내가 있는 폴더 위치를 보여주는 명령어
  - `git init` = 버전 관리 시작. 파일 변경 이력을 기록하기 시작하는 명령어
  - `npm install` = 필요한 패키지(부품들)를 인터넷에서 다운로드해서 설치
  - `pip install` = Python 패키지 설치 (npm과 같은 역할, Python 버전)
  - `.env` 파일 = 비밀번호·API 키 같은 민감한 정보를 저장하는 설정 파일
  - `API` = 프로그램끼리 대화하는 창구. "OpenAI API"는 OpenAI 서비스를 내 프로그램에서 쓰는 연결통로
  - `endpoint` = API에서 특정 기능을 부르는 주소. `/chat`이면 채팅 기능 주소
  - `docker run` = Docker 컨테이너(가상 환경)를 실행하는 명령어
  - `port` = 컴퓨터 내부 통신 통로 번호. `:8000`은 8000번 통로

### 2. 단계 안내 방식
- 현재 어떤 단계인지 항상 명시
- 다음에 할 일을 구체적으로 안내
- BMad 워크플로우 기준으로 진행 상황 설명

### 3. 명령어 설명 형식
명령어를 제시할 때는 항상 아래 형식으로:
```
명령어: docker-compose up -d
뜻: docker-compose.yml 파일에 정의된 서비스들을 백그라운드(-d = detached mode, 뒤에서 실행)로 시작
```

### 4. 에러 발생 시
- 에러 메시지를 쉬운 말로 해석
- 원인과 해결 방법을 단계별로 설명

---

## 프로젝트 폴더 구조 (목표)

```
rag-project-1/                     ← 프로젝트 루트(최상위 폴더)
├── CLAUDE.md                      ← 이 파일 (Claude 안내서)
├── docker-compose.yml             ← PostgreSQL+pgvector 로컬 실행 설정
├── .gitignore                     ← Git에 올리지 않을 파일 목록
├── README.md                      ← 프로젝트 소개 문서
│
├── backend/                       ← FastAPI 백엔드
│   ├── main.py                    ← FastAPI 앱 진입점, CORS 설정
│   ├── requirements.txt           ← Python 패키지 목록
│   ├── .env                       ← 환경변수 (git 제외)
│   ├── .env.example               ← 환경변수 샘플 (git 포함)
│   │
│   ├── routers/                   ← API 엔드포인트 (외부 요청 창구)
│   │   ├── __init__.py
│   │   ├── chat.py                ← POST /chat (질문-답변)
│   │   └── admin.py               ← POST /admin/upload, GET /admin/status
│   │
│   ├── services/                  ← 핵심 비즈니스 로직 (두뇌)
│   │   ├── __init__.py
│   │   ├── rag.py                 ← 벡터 검색 + GPT 답변 생성
│   │   ├── embeddings.py          ← OpenAI 임베딩 호출
│   │   └── pdf.py                 ← PDF 파싱 + 조항 단위 청킹
│   │
│   ├── db/                        ← 데이터베이스 관련
│   │   ├── __init__.py
│   │   ├── database.py            ← PostgreSQL 연결, pgvector 초기화
│   │   └── schema.sql             ← documents 테이블 DDL (구조 정의)
│   │
│   └── tests/                     ← 백엔드 자동 테스트
│       ├── test_chat.py
│       ├── test_admin.py
│       └── test_pdf_chunking.py   ← 조항 파싱 검증
│
└── frontend/                      ← Next.js 웹 프론트엔드
    ├── package.json               ← JS 패키지 목록 및 프로젝트 설정
    ├── next.config.js             ← Next.js 설정
    ├── tailwind.config.js         ← Tailwind CSS 설정 (UI 스타일링 도구)
    ├── tsconfig.json              ← TypeScript 설정
    ├── .env.local                 ← 환경변수 (NEXT_PUBLIC_API_URL 등)
    ├── .env.example
    │
    └── src/
        ├── app/                   ← Next.js App Router (페이지 구조)
        │   ├── layout.tsx         ← 공통 레이아웃 (모든 페이지 공유)
        │   ├── page.tsx           ← 채팅 메인 페이지 (/)
        │   ├── globals.css        ← 전역 CSS 스타일
        │   └── admin/
        │       └── page.tsx       ← 관리자 PDF 업로드 페이지 (/admin)
        │
        ├── components/            ← 재사용 가능한 UI 조각들
        │   ├── chat/
        │   │   ├── ChatWindow.tsx ← 대화 영역 전체
        │   │   ├── ChatMessage.tsx← 메시지 말풍선 + 출처 표시
        │   │   └── ChatInput.tsx  ← 입력창 + 전송 버튼
        │   └── admin/
        │       └── FileUpload.tsx ← PDF 업로드 + 상태 표시
        │
        └── lib/
            ├── api.ts             ← 백엔드 API 호출 함수 모음
            └── types.ts           ← TypeScript 타입 정의
```

### 데이터 흐름 (정보가 이동하는 경로)

```
사용자 질문 입력
  → frontend/lib/api.ts           (질문을 백엔드로 전송)
  → backend/routers/chat.py       (요청 수신)
  → backend/services/rag.py       (벡터 검색 + GPT 호출)
  → backend/db/database.py        (pgvector로 유사 조항 검색)
  → 답변 + 출처 조항 반환
  → frontend/components/chat/ChatMessage.tsx  (화면에 표시)
```

---

## 환경 변수 (민감 정보 관리)

> **.env 파일**이란? API 키, 비밀번호 같은 민감한 정보를 코드에 직접 쓰지 않고
> 별도 파일에 보관하는 방식. 이 파일은 절대 GitHub에 올리면 안 됩니다.

나중에 필요한 환경 변수들:
- `OPENAI_API_KEY` = OpenAI GPT 사용 권한 키
- `DATABASE_URL` = PostgreSQL 접속 주소
- `SECRET_KEY` = 보안용 비밀 키

---

## 자주 쓰는 명령어 모음 (나중에 채워질 예정)

```bash
# Docker PostgreSQL 시작
docker-compose up -d

# 백엔드 실행
cd backend && uvicorn main:app --reload

# 프론트엔드 실행
cd frontend && npm run dev
```

---

## 참고 자료

- BMad Method 공식 문서: https://docs.bmad-method.org/tutorials/getting-started/
- OpenAI API 문서: https://platform.openai.com/docs
- FastAPI 공식 문서: https://fastapi.tiangolo.com
- pgvector (PostgreSQL 벡터 확장): https://github.com/pgvector/pgvector
- Railway 배포 서비스: https://railway.app
