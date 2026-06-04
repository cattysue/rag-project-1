---
stepsCompleted: [1, 2, 3, 4]
status: complete
inputDocuments:
  - '_bmad-output/planning-artifacts/prds/prd-rag-project-1-2026-06-03/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
---

# rag-project-1 - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for rag-project-1, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR-1.1: 사용자는 자연어(한국어)로 규정 관련 질문을 입력할 수 있다.
FR-1.2: 챗봇은 입력된 질문을 분석하여 규정 문서에서 관련 내용을 검색하고, 요약된 답변을 제공한다.
FR-1.3: 모든 답변에는 관련 출처(조항 번호, 항목명)가 명시된다. 관련 조항이 여러 개인 경우 모두 표시.
FR-1.4: 검색된 문서의 관련도가 유사도 점수 임계값 이하인 경우, AI가 "해당 내용은 규정에 명시되어 있지 않습니다"라고 안내한다. (환각 방지)
FR-1.5: 대화는 브라우저 탭이 열려 있는 동안 이전 질문·답변을 기억하여 연속 질문이 가능하다. 새로고침 시 초기화된다.
FR-2.1: 관리자는 별도의 관리 페이지에 접속하여 규정 PDF 파일을 업로드할 수 있다.
FR-2.2: 관리 페이지는 단일 비밀번호로 보호된다. 비밀번호는 서버 환경변수(.env)에서 관리한다.
FR-2.3: PDF 업로드 후 시스템은 자동으로 문서를 분석(임베딩 처리)하여 챗봇에 반영한다.
FR-2.4: 업로드 진행 상태(처리 중 / 완료 / 실패)를 관리자가 확인할 수 있다.
FR-2.5: 기존 규정 파일을 새 파일로 교체할 수 있다. (기존 벡터 전체 삭제 후 재임베딩)
FR-3.1: 링크(URL)만으로 접속 가능한 웹 채팅 화면을 제공한다. 로그인 불필요.
FR-3.2: 채팅 화면 구성: 메시지 입력창(하단 고정), 대화 내역 표시 영역, 챗봇 이름 "규정이" 표시.
FR-3.3: 답변 내 출처 조항은 구분하여 표시된다 (별도 색상 또는 인용 블록 스타일).
FR-3.4: PC 브라우저 및 모바일 브라우저 모두에서 정상 동작한다. 반응형 디자인. 별도 앱 설치 없이 링크만으로 접속 가능하다.

### NonFunctional Requirements

NFR-1: [성능] 챗봇 답변 생성 시간 10초 이내. 동시 사용자 최대 20명 수준.
NFR-2: [가용성] Railway 기반 배포로 인터넷 연결 시 24/7 접근 가능.
NFR-3: [보안] 관리자 페이지 비밀번호 접근 제한, API 키 환경변수 관리, HTTPS 통신 (Railway 기본 제공), 민감한 개인정보 처리 없음.
NFR-4: [유지보수성] PDF 교체 시 기술 지식 없이도 관리자가 직접 처리 가능. 환경변수 변경만으로 OpenAI 모델 버전 업데이트 가능.
NFR-5: [접근성] 별도 설치나 회원가입 없이 링크만으로 접속. 한국어 인터페이스.
NFR-6: [검색 품질 검증] 배포 전 샘플 질문 20개 이상 테스트, 정답 조항 정확도 80% 이상일 때 배포.

### Additional Requirements

- AR-1: [프로젝트 초기화] Next.js 프론트엔드: `npx create-next-app@latest frontend` (TypeScript: Yes, Tailwind CSS: Yes, App Router: Yes). FastAPI 백엔드: Python 가상환경 + `pip install fastapi uvicorn python-multipart openai pgvector psycopg2-binary python-dotenv`. Docker PostgreSQL+pgvector: `docker-compose up -d`.
- AR-2: [청킹 전략] "제○조" 정규식으로 조항 경계 감지, 조항 번호·항목명을 메타데이터로 저장. 서문·부칙 등 조항 구분 없는 영역은 단락 단위 폴백 처리.
- AR-3: [DB 스키마] documents 테이블: id(PK), chunk_text, embedding(vector 1536차원), article_number, article_title, page_number, created_at.
- AR-4: [관리자 인증] ADMIN_PASSWORD 환경변수와 요청 Authorization 헤더 값 비교 방식.
- AR-5: [API 응답 표준] POST /chat → `{"answer": "...", "sources": [{"article_number": "...", "article_title": "..."}]}`. GET /admin/status → `{"status": "processing|completed|failed"}`. 에러 → `{"detail": "..."}`.
- AR-6: [로딩 상태] 채팅: isLoading boolean → 전송 버튼 비활성화 + 스피너. 관리자 업로드: 2초 간격 폴링으로 /admin/status 조회.
- AR-7: [CORS 설정] main.py에 Railway 프론트엔드 URL을 허용 오리진으로 명시.
- AR-8: [PDF 파싱 라이브러리] pypdf 또는 pdfplumber 권장.
- AR-9: [파일 교체] 기존 벡터 데이터 전체 삭제 후 새 파일 재임베딩 순서 준수.
- AR-10: [환경변수] backend/.env: OPENAI_API_KEY, DATABASE_URL, ADMIN_PASSWORD. frontend/.env.local: NEXT_PUBLIC_API_URL.
- AR-11: [명명 규칙] DB·Python: snake_case / JS·TS: camelCase / React 컴포넌트: PascalCase / API 엔드포인트: 소문자 kebab.

### UX Design Requirements

UX 설계 문서 없음 (해당 없음 — Next.js 반응형 웹으로 처리하며, 별도 UX 스펙 파일 미작성).

### FR Coverage Map

FR-1.1: Epic 2 — 채팅 입력창 구현
FR-1.2: Epic 2 — RAG 파이프라인 (rag.py + chat.py)
FR-1.3: Epic 2 — 출처 표시 UI + API 응답
FR-1.4: Epic 2 — 환각 방지 로직 (rag.py 유사도 임계값)
FR-1.5: Epic 2 — 세션 대화 이력 (React useState)
FR-2.1: Epic 1 — 관리자 페이지 + 업로드 UI
FR-2.2: Epic 1 — Authorization 헤더 인증 (ADMIN_PASSWORD)
FR-2.3: Epic 1 — PDF 청킹 + OpenAI 임베딩 서비스
FR-2.4: Epic 1 — 폴링 기반 업로드 상태 표시
FR-2.5: Epic 1 — 기존 벡터 삭제 후 재임베딩
FR-3.1: Epic 2 — 링크 접속, 인증 없음
FR-3.2: Epic 2 — ChatWindow / ChatInput / ChatMessage 컴포넌트
FR-3.3: Epic 2 — 출처 인용 블록 스타일
FR-3.4: Epic 2 — Tailwind 반응형 브레이크포인트

## Epic List

### Epic 1: 개발 환경 및 문서 관리 시스템
관리자가 규정 PDF를 업로드하면 자동으로 임베딩 처리되어 검색 가능한 상태로 저장되는 완전한 시스템 (프로젝트 초기 환경 포함)
**FRs covered:** FR-2.1, FR-2.2, FR-2.3, FR-2.4, FR-2.5
**ARs covered:** AR-1, AR-2, AR-3, AR-4, AR-5(부분), AR-6(폴링), AR-8, AR-9, AR-10, AR-11

### Epic 2: 교사 채팅 인터페이스
교사가 웹 브라우저(PC·모바일)에서 한국어로 규정에 대해 질문하고, 출처 조항과 함께 AI 답변을 받을 수 있는 완전한 채팅 경험
**FRs covered:** FR-1.1, FR-1.2, FR-1.3, FR-1.4, FR-1.5, FR-3.1, FR-3.2, FR-3.3, FR-3.4
**ARs covered:** AR-5(전체), AR-6(스피너), AR-7

### Epic 3: Railway 배포 및 품질 검증
"규정이" 챗봇이 Railway에 배포되어 교사들이 24/7 인터넷으로 접근 가능하고, 샘플 질문 테스트를 통해 검색 품질이 검증된 상태
**NFRs covered:** NFR-2, NFR-6
**ARs covered:** AR-7(Railway CORS URL 확정)

---

## Epic 1: 개발 환경 및 문서 관리 시스템

관리자가 규정 PDF를 업로드하면 자동으로 임베딩 처리되어 검색 가능한 상태로 저장되는 완전한 시스템 (프로젝트 초기 환경 포함)

### Story 1.1: 프로젝트 초기화 및 개발 환경 구성

As a 개발자,
I want 로컬 개발 환경(Next.js, FastAPI, Docker PostgreSQL)이 완전히 구성된 상태를,
So that 이후 모든 개발 작업을 바로 시작할 수 있다.

**Acceptance Criteria:**

**Given** 프로젝트 루트 디렉토리에서
**When** `docker-compose up -d`를 실행하면
**Then** PostgreSQL+pgvector 컨테이너가 정상 시작되고 포트 5432에서 접속 가능하다

**Given** Docker PostgreSQL이 실행 중일 때
**When** `cd backend && uvicorn main:app --reload`를 실행하면
**Then** FastAPI 서버가 http://localhost:8000에서 응답하고 `/docs` 페이지가 열린다

**Given** FastAPI 서버가 실행 중일 때
**When** `cd frontend && npm run dev`를 실행하면
**Then** Next.js 개발 서버가 http://localhost:3000에서 실행된다

**Given** 프로젝트가 초기화되었을 때
**When** `backend/.env.example` 파일을 확인하면
**Then** OPENAI_API_KEY, DATABASE_URL, ADMIN_PASSWORD 세 환경변수가 안내되어 있다

**Given** Next.js 앱이 백엔드로 API 요청을 보낼 때
**When** localhost:3000 → localhost:8000으로 요청이 발생하면
**Then** CORS 오류 없이 응답이 반환된다

### Story 1.2: 데이터베이스 스키마 및 pgvector 초기화

As a 시스템,
I want documents 테이블과 pgvector 확장이 데이터베이스에 초기화되어 있는 상태를,
So that 규정 청크와 임베딩 벡터를 저장하고 유사도 검색을 수행할 수 있다.

**Acceptance Criteria:**

**Given** Docker PostgreSQL이 실행 중일 때
**When** `database.py`의 초기화 함수를 실행하면
**Then** pgvector 확장이 활성화되고 documents 테이블이 생성된다

**Given** documents 테이블이 생성되었을 때
**When** 테이블 스키마를 확인하면
**Then** id(PK), chunk_text, embedding(vector(1536)), article_number, article_title, page_number, created_at 컬럼이 모두 존재한다

**Given** 테이블이 이미 존재할 때
**When** 초기화 함수를 다시 실행하면
**Then** 오류 없이 정상 완료된다 (IF NOT EXISTS로 멱등성 보장)

### Story 1.3: PDF 파싱 및 조항 단위 청킹

As a 시스템,
I want PDF 파일을 "제○조" 패턴으로 조항 단위 분리하는 기능을,
So that 각 조항이 독립적인 검색 단위가 되고 출처 조항 번호를 메타데이터로 저장할 수 있다.

**Acceptance Criteria:**

**Given** 학업성적관리규정 PDF 파일이 주어졌을 때
**When** `pdf.py`의 파싱 함수를 실행하면
**Then** "제○조" 정규식 패턴으로 조항이 분리되고 각 청크에 article_number와 article_title이 추출된다

**Given** 서문·부칙처럼 조항 구분이 없는 텍스트가 포함된 경우
**When** 파싱 함수를 실행하면
**Then** 단락 단위 폴백 처리로 해당 텍스트도 누락 없이 청크로 분리된다

**Given** 파싱이 완료되었을 때
**When** 결과 청크 목록을 확인하면
**Then** 각 항목이 chunk_text, article_number, article_title, page_number를 포함한 딕셔너리다

**Given** `test_pdf_chunking.py`를 실행했을 때
**When** 샘플 텍스트에 대한 파싱 테스트가 수행되면
**Then** 조항 번호 추출 검증 테스트가 통과된다

### Story 1.4: OpenAI 임베딩 및 벡터 저장 파이프라인

As a 시스템,
I want 파싱된 청크를 OpenAI 임베딩 API로 벡터화하여 pgvector DB에 저장하는 기능을,
So that 교사의 질문과 의미적으로 유사한 조항을 빠르게 검색할 수 있다.

**Acceptance Criteria:**

**Given** 파싱된 청크 목록이 있을 때
**When** `embeddings.py`의 임베딩 함수를 호출하면
**Then** OpenAI text-embedding-3-small 모델이 호출되고 각 청크에 대해 1536차원 벡터가 반환된다

**Given** 임베딩 벡터가 생성되었을 때
**When** `database.py`의 저장 함수를 호출하면
**Then** documents 테이블에 chunk_text, embedding, article_number, article_title, page_number가 함께 저장된다

**Given** OPENAI_API_KEY가 잘못 설정된 경우
**When** 임베딩 함수를 호출하면
**Then** 예외가 발생하고 상위 호출자에게 명확한 오류 메시지가 전달된다

### Story 1.5: 관리자 PDF 업로드·교체·상태 API

As a 관리자,
I want PDF 업로드·교체·처리 상태 조회 백엔드 API를,
So that 새 규정 파일을 시스템에 적용하고 처리 완료 여부를 API로 확인할 수 있다.

**Acceptance Criteria:**

**Given** 올바른 ADMIN_PASSWORD가 Authorization 헤더에 포함된 요청일 때
**When** `POST /admin/upload`에 PDF 파일을 업로드하면
**Then** `{"status": "processing"}` 응답을 즉시 반환하고 백그라운드에서 임베딩 처리가 시작된다

**Given** 잘못된 비밀번호가 Authorization 헤더에 포함된 요청일 때
**When** `POST /admin/upload`를 호출하면
**Then** HTTP 401과 `{"detail": "Unauthorized"}`가 반환된다

**Given** PDF 처리가 진행 중이거나 완료·실패한 상태일 때
**When** `GET /admin/status`를 호출하면
**Then** `{"status": "processing"}` 또는 `"completed"` 또는 `"failed"` 중 하나가 반환된다

**Given** 기존 문서가 데이터베이스에 존재하는 상태에서
**When** 새 PDF 파일로 업로드하면
**Then** 기존 documents 테이블의 모든 행을 먼저 삭제한 후 새 파일의 청크를 임베딩하여 저장한다

**Given** PDF가 아닌 파일 형식이 업로드된 경우
**When** `POST /admin/upload`를 호출하면
**Then** HTTP 400과 오류 메시지가 반환된다

### Story 1.6: 관리자 웹 페이지 (PDF 업로드 UI)

As a 관리자,
I want 웹 브라우저에서 비밀번호를 입력하고 규정 PDF를 업로드·교체할 수 있는 화면을,
So that 기술적 지식 없이도 새 규정 파일을 간편하게 시스템에 반영할 수 있다.

**Acceptance Criteria:**

**Given** `/admin` 페이지에 접속했을 때
**When** 비밀번호 입력창이 표시될 때
**Then** 올바른 비밀번호 입력 시 업로드 화면으로 진입하고, 틀린 비밀번호 입력 시 오류 메시지가 표시된다

**Given** 업로드 화면에서 PDF 파일을 선택하고 업로드 버튼을 누를 때
**When** 업로드 요청이 전송되면
**Then** "처리 중" 상태가 화면에 표시되고, 2초 간격으로 `/admin/status`를 폴링하여 상태가 갱신된다

**Given** 임베딩 처리가 완료된 경우
**When** 폴링 결과가 "completed"이면
**Then** "업로드 완료" 메시지가 화면에 표시되고 폴링이 중단된다

**Given** 임베딩 처리가 실패한 경우
**When** 폴링 결과가 "failed"이면
**Then** "처리 실패" 오류 메시지가 화면에 표시된다

**Given** 기존 규정 파일이 있는 상태에서 새 PDF를 업로드하는 경우
**When** 업로드가 시작되면
**Then** "기존 규정 파일을 새 파일로 교체합니다" 안내 문구가 화면에 표시된다

---

## Epic 2: 교사 채팅 인터페이스

교사가 웹 브라우저(PC·모바일)에서 한국어로 규정에 대해 질문하고, 출처 조항과 함께 AI 답변을 받을 수 있는 완전한 채팅 경험

### Story 2.1: RAG 파이프라인 및 채팅 API (백엔드)

As a 시스템,
I want 교사의 질문을 받아 벡터 검색 후 GPT-4o 답변과 출처 조항을 반환하는 백엔드 API를,
So that 교사가 규정 관련 질문을 하면 정확한 출처와 함께 요약 답변을 받을 수 있다.

**Acceptance Criteria:**

**Given** 유효한 한국어 질문이 `POST /chat`으로 전송되었을 때
**When** `rag.py`가 pgvector 코사인 유사도 검색을 실행하면
**Then** 상위 유사 청크가 반환되고 GPT-4o 호출에 컨텍스트로 전달된다

**Given** GPT-4o 답변이 생성되었을 때
**When** `POST /chat` 응답이 반환되면
**Then** `{"answer": "제○조에 따르면...", "sources": [{"article_number": "제○조", "article_title": "..."}]}` 형식의 JSON이 반환된다

**Given** 질문 내용이 규정과 관련 없어 유사도 점수가 임계값 이하인 경우
**When** RAG 검색 결과를 평가하면
**Then** GPT가 내용을 생성하지 않고 "해당 내용은 규정에 명시되어 있지 않습니다"라는 답변이 반환된다

**Given** `POST /chat`이 정상적으로 동작할 때
**When** 이전 대화 내역을 `messages` 배열로 함께 전송하면
**Then** GPT-4o가 이전 맥락을 고려한 연속 답변을 생성한다

**Given** `test_chat.py`를 실행했을 때
**When** 샘플 질문에 대한 API 응답 테스트가 수행되면
**Then** 응답 JSON 구조와 sources 필드 존재 여부 검증 테스트가 통과된다

### Story 2.2: 채팅 웹 UI — 기본 구조 및 메시지 표시

As a 교사,
I want 링크로 바로 접속하여 "규정이"에게 질문을 입력하고 답변을 대화 형식으로 볼 수 있는 웹 화면을,
So that PDF를 열지 않고도 규정 내용을 빠르게 확인할 수 있다.

**Acceptance Criteria:**

**Given** 교사가 웹 링크로 채팅 페이지에 접속했을 때
**When** 메인 페이지(`/`)가 로드되면
**Then** 챗봇 이름 "규정이"가 표시되고, 대화 내역 영역과 하단 고정 입력창이 보인다

**Given** 교사가 질문을 입력하고 전송 버튼을 누르거나 Enter를 누른 경우
**When** API 응답을 기다리는 동안
**Then** 전송 버튼이 비활성화되고 로딩 스피너가 표시되어 처리 중임을 알 수 있다

**Given** 챗봇 답변이 도착했을 때
**When** 대화 내역 영역이 업데이트되면
**Then** 교사 질문(오른쪽)과 챗봇 답변(왼쪽)이 말풍선으로 구분되어 표시된다

**Given** 대화가 여러 번 이어졌을 때
**When** 새로운 메시지가 추가되면
**Then** 대화 내역이 자동으로 최신 메시지로 스크롤된다

**Given** 브라우저 탭이 열려 있는 동안
**When** 교사가 후속 질문을 전송하면
**Then** 이전 대화 내역이 유지된 상태에서 연속 질문·답변이 가능하다
**And** 페이지를 새로고침하면 대화 내역이 초기화된다

### Story 2.3: 출처 조항 표시 및 반응형 디자인

As a 교사,
I want 챗봇 답변 아래에 근거가 된 조항 번호가 구분되어 표시되고, 스마트폰에서도 정상적으로 사용할 수 있는 화면을,
So that 답변의 신뢰성을 바로 확인하고 어디서든 규정을 조회할 수 있다.

**Acceptance Criteria:**

**Given** 챗봇 답변에 `sources` 배열이 포함되어 있을 때
**When** `ChatMessage.tsx`가 답변을 렌더링하면
**Then** 답변 텍스트 아래에 출처 조항(article_number, article_title)이 인용 블록 스타일로 구분되어 표시된다

**Given** 출처 조항이 여러 개인 경우
**When** 답변이 표시되면
**Then** 관련된 모든 조항이 나열되어 표시된다

**Given** 유사도 임계값 이하로 "규정에 명시되어 있지 않습니다" 답변이 반환된 경우
**When** 해당 메시지가 표시되면
**Then** 출처 조항 없이 안내 메시지만 표시되며 시각적으로 일반 답변과 구분된다

**Given** 교사가 PC 브라우저에서 접속했을 때
**When** 채팅 화면이 로드되면
**Then** 넓은 화면에 적합한 레이아웃(최대 너비 제한, 중앙 정렬)으로 표시된다

**Given** 교사가 모바일 브라우저에서 접속했을 때
**When** 채팅 화면이 로드되면
**Then** 화면 전체 너비를 활용하며 입력창과 버튼이 손가락으로 조작하기 적합한 크기로 표시된다

---

## Epic 3: Railway 배포 및 품질 검증

"규정이" 챗봇이 Railway에 배포되어 교사들이 24/7 인터넷으로 접근 가능하고, 샘플 질문 테스트를 통해 검색 품질이 검증된 상태

### Story 3.1: Railway 배포 및 환경변수 구성

As a 담당자 및 교사,
I want "규정이" 챗봇이 Railway 클라우드에 배포되어 인터넷으로 접속 가능한 상태를,
So that 학교 어디서든 링크 하나로 24시간 규정이를 이용할 수 있다.

**Acceptance Criteria:**

**Given** Railway 계정이 준비된 상태에서
**When** Railway에 배포 설정을 완료하면
**Then** 백엔드(FastAPI), 프론트엔드(Next.js), PostgreSQL 플러그인 세 서비스가 Railway에 생성된다

**Given** Railway 서비스가 생성되었을 때
**When** 환경변수를 Railway 대시보드에 설정하면
**Then** 백엔드에 OPENAI_API_KEY, DATABASE_URL, ADMIN_PASSWORD가, 프론트엔드에 NEXT_PUBLIC_API_URL(백엔드 Railway URL)이 설정된다

**Given** Railway 프론트엔드 URL이 확정되었을 때
**When** `main.py` CORS 설정을 업데이트하면
**Then** Railway 프론트엔드 URL이 허용 오리진에 추가되고 재배포된다

**Given** 배포가 완료된 상태에서
**When** Railway 프론트엔드 URL로 접속하면
**Then** "규정이" 채팅 페이지가 정상 로드되고 질문 입력이 가능하다

**Given** 배포가 완료된 상태에서
**When** `/admin` 경로로 접속하면
**Then** 관리자 업로드 페이지가 정상 로드되고 비밀번호 입력창이 표시된다

### Story 3.3: 하이브리드 검색 개선 (BM25 + 벡터)

As a 교사,
I want 비슷한 말로 질문해도 규정 조항을 정확하게 찾아주는 챗봇을,
So that "결석"이라고 물어도 "결시" 조항을 찾는 것처럼 어휘 차이와 무관하게 정확한 답변을 받을 수 있다.

**Acceptance Criteria:**

**Given** 교사가 규정 공식 용어와 다른 일상 표현으로 질문했을 때
**When** 챗봇이 검색을 수행하면
**Then** BM25 키워드 검색과 벡터 유사도 검색 결과가 RRF(Reciprocal Rank Fusion)로 합산되어 관련 조항이 반환된다

**Given** 하이브리드 검색을 적용한 상태에서
**When** Story 3.2와 동일한 25개 샘플 질문을 재테스트하면
**Then** 정확도가 Story 3.2 결과(20%)보다 향상된다

**Given** BM25 검색에 쓸 청크가 DB에 없을 때 (빈 DB)
**When** 질문이 들어오면
**Then** "해당 내용은 규정에 명시되어 있지 않습니다" 응답이 반환되고 오류가 발생하지 않는다

**Given** 하이브리드 검색 적용 후
**When** 기존 질문·답변 흐름을 테스트하면
**Then** 출처 조항 표시, 연속 질문, 환각 방지 등 기존 기능이 모두 정상 동작한다

### Story 3.2: 검색 품질 검증 및 최종 배포 승인

As a 담당자,
I want 배포된 챗봇이 실제 규정 질문에 정확하게 답변하는지 검증하는 테스트를,
So that 교사들에게 공개하기 전에 챗봇 품질이 기준 이상임을 확인할 수 있다.

**Acceptance Criteria:**

**Given** 배포 환경에서 관리자 페이지를 통해
**When** 규정 PDF 파일을 업로드하면
**Then** 임베딩 처리가 완료되고 "업로드 완료" 상태가 표시된다

**Given** 규정 파일 업로드가 완료된 상태에서
**When** 담당자가 샘플 질문 20개 이상을 챗봇에 입력하면
**Then** 각 질문에 대한 답변과 출처 조항이 기록된다

**Given** 샘플 테스트 결과를 집계했을 때
**When** 정답 조항을 올바르게 찾은 비율을 계산하면
**Then** 80% 이상인 경우 배포 품질 기준을 통과하고 교사 공개 링크가 확정된다

**Given** 정확도가 80% 미만인 경우
**When** 품질 기준 미달이 확인되면
**Then** 유사도 임계값 조정 또는 청킹 방식 수정 후 재테스트를 수행한다
