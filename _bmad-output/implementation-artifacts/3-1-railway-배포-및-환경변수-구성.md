# Story 3.1: Railway 배포 및 환경변수 구성

Status: done

## Story

As a 담당자 및 교사,
I want "규정이" 챗봇이 Railway 클라우드에 배포되어 인터넷으로 접속 가능한 상태를,
so that 학교 어디서든 링크 하나로 24시간 규정이를 이용할 수 있다.

## Acceptance Criteria

1. **Given** Railway 계정이 준비된 상태에서 **When** Railway에 배포 설정을 완료하면 **Then** 백엔드(FastAPI), 프론트엔드(Next.js), PostgreSQL 플러그인 세 서비스가 Railway에 생성된다
2. **Given** Railway 서비스가 생성되었을 때 **When** 환경변수를 Railway 대시보드에 설정하면 **Then** 백엔드에 OPENAI_API_KEY, DATABASE_URL, ADMIN_PASSWORD, ALLOWED_ORIGINS가, 프론트엔드에 NEXT_PUBLIC_API_URL(백엔드 Railway URL)이 설정된다
3. **Given** Railway 프론트엔드 URL이 확정되었을 때 **When** 백엔드 `ALLOWED_ORIGINS` 환경변수를 업데이트하면 **Then** Railway 프론트엔드 URL이 허용 오리진에 적용되고 재배포된다
4. **Given** 배포가 완료된 상태에서 **When** Railway 프론트엔드 URL로 접속하면 **Then** "규정이" 채팅 페이지가 정상 로드되고 질문 입력이 가능하다
5. **Given** 배포가 완료된 상태에서 **When** `/admin` 경로로 접속하면 **Then** 관리자 업로드 페이지가 정상 로드되고 비밀번호 입력창이 표시된다

## Tasks / Subtasks

> **이 스토리는 코드 변경(Task 1)과 Railway 대시보드 수동 작업(Task 2~6)으로 나뉩니다.**
> Task 1은 Dev Agent가 처리하고, Task 2~6은 Catty가 Railway 웹사이트에서 직접 진행합니다.
> Task 2~6의 상세 절차는 Dev Notes → "Railway 배포 단계별 절차"를 참고하세요.

- [x] Task 1: 코드 변경 — Railway 배포 준비 파일 생성·수정 (AC: 전제조건)
  - [x] `backend/Procfile` 생성 — Railway가 FastAPI 서버를 시작하는 명령어 파일
  - [x] `frontend/package.json` start 스크립트를 `"next start -p $PORT"`로 수정 — Railway가 제공하는 포트 번호 사용
  - [x] `backend/.env.example`에 `ALLOWED_ORIGINS` 항목 추가 — 환경변수 문서화

- [x] Task 2: (수동) Railway 프로젝트·서비스 생성 (AC: #1)
  - [x] railway.app 계정 생성 및 로그인
  - [x] 새 프로젝트 생성 → 백엔드 서비스 추가 (GitHub 연결, Root Directory: `backend`)
  - [x] 프론트엔드 서비스 추가 (같은 repo, Root Directory: `frontend`)
  - [x] PostgreSQL 플러그인 추가 → 백엔드 서비스에 연결

- [x] Task 3: (수동) 환경변수 설정 (AC: #2)
  - [x] 백엔드 서비스에 `OPENAI_API_KEY`, `ADMIN_PASSWORD` 입력 (DATABASE_URL은 PostgreSQL 연결 시 자동 주입)
  - [x] 백엔드 서비스 URL 확인 → 프론트엔드 서비스에 `NEXT_PUBLIC_API_URL` 입력

- [x] Task 4: (수동) 배포 실행 및 URL 확인 (AC: #1, #2 완료 전제)
  - [x] 백엔드·프론트엔드 서비스 배포 트리거 (GitHub push 또는 Railway 대시보드 "Deploy" 버튼)
  - [x] 배포 로그 확인 → 오류 없음 확인
  - [x] 프론트엔드 서비스 URL 확인

- [x] Task 5: (수동) CORS 업데이트 — 프론트엔드 URL을 백엔드 환경변수에 추가 (AC: #3)
  - [x] 확인된 프론트엔드 URL을 백엔드 `ALLOWED_ORIGINS` 환경변수에 입력
  - [x] 백엔드 서비스 재배포 트리거

- [x] Task 6: (수동) 최종 접속 검증 (AC: #4, #5)
  - [x] 프론트엔드 URL로 접속 → "규정이" 채팅 화면 정상 로드 확인
  - [x] `/admin` 경로 접속 → 관리자 비밀번호 입력창 정상 표시 확인
  - [x] 샘플 질문 1개 입력 → 답변·출처 정상 반환 확인 (PDF 업로드 선행 필요)

## Dev Notes

### 용어 먼저 이해하기

- **Railway** = 클라우드 호스팅 서비스. "내 컴퓨터에서 실행되던 앱을 인터넷 서버로 옮겨주는 서비스"
- **서비스(Service)** = Railway 안에서 독립적으로 실행되는 하나의 앱 단위. 백엔드·프론트엔드·DB가 각각 서비스
- **플러그인(Plugin)** = Railway에서 PostgreSQL처럼 외부 서비스를 추가하는 방식
- **환경변수(Environment Variable)** = `.env` 파일에 있던 비밀 정보들을 Railway 서버에 설정하는 것
- **Root Directory** = 하나의 GitHub 저장소에 백엔드·프론트엔드가 함께 있을 때, "이 서비스는 어느 폴더에서 시작하나요?"를 지정하는 설정
- **`$PORT`** = Railway 서버가 "이 포트 번호로 들어오는 요청을 받으세요"라고 앱에 알려주는 숫자. 로컬에서는 8000·3000 고정이었지만, Railway에서는 자동으로 지정됨

---

### Task 1 상세: 코드 변경 내용

#### 1-A. `backend/Procfile` (신규 생성)

**위치:** `rag-project-1/backend/Procfile` (확장자 없음, 파일명 그대로)

**내용:**
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

**설명:**
- `Procfile`은 Railway가 "이 앱을 어떻게 시작하나요?"를 읽는 설정 파일
- `--host 0.0.0.0` = 외부 인터넷에서 접속 허용 (로컬 개발 시 생략했던 옵션)
- `--port $PORT` = Railway가 지정한 포트 번호 사용
- `--reload` 옵션 절대 넣지 않기 (로컬 개발 전용 옵션, 프로덕션에서 성능 저하·불안정 야기)

#### 1-B. `frontend/package.json` — start 스크립트 수정

**현재 코드:**
```json
"start": "next start",
```

**변경 후:**
```json
"start": "next start -p $PORT",
```

**설명:**
- Railway는 앱이 `$PORT`로 지정된 포트에서 응답하기를 기대
- `-p $PORT`를 명시하지 않으면 Next.js가 기본 3000 포트에서 시작하여 Railway가 연결하지 못함
- `$PORT`는 Railway Linux 환경의 환경변수 참조 문법 (Windows `%PORT%`와 다름, package.json 스크립트는 Railway 서버에서 실행되므로 Linux 문법 사용)

#### 1-C. `backend/.env.example` — ALLOWED_ORIGINS 항목 추가

**현재 내용:**
```
OPENAI_API_KEY=sk-your-openai-api-key-here
DATABASE_URL=postgresql://raguser:ragpass@localhost:5432/ragdb
ADMIN_PASSWORD=your-secure-admin-password
```

**변경 후:**
```
OPENAI_API_KEY=sk-your-openai-api-key-here
DATABASE_URL=postgresql://raguser:ragpass@localhost:5432/ragdb
ADMIN_PASSWORD=your-secure-admin-password
ALLOWED_ORIGINS=http://localhost:3000
```

**설명:**
- `ALLOWED_ORIGINS`는 로컬 개발 시 기본값으로 `http://localhost:3000`이 사용됨 (`main.py:12` 참고)
- 로컬 `.env` 파일은 수정할 필요 없음 (기본값으로 작동)
- Railway 백엔드 환경변수에는 프론트엔드 Railway URL로 설정

**코드 수정 금지:**
- `backend/main.py` — CORS 설정이 이미 `ALLOWED_ORIGINS` 환경변수를 읽도록 구현됨 (`main.py:12-13`). 코드 변경 불필요
- `frontend/src/lib/api.ts` — `NEXT_PUBLIC_API_URL` 환경변수 미설정 시 경고 로직 이미 구현됨 (`api.ts:6-9`). 코드 변경 불필요

---

### Task 2~6 상세: Railway 배포 단계별 절차 (Catty 수동 진행)

> 아래 절차는 코드 변경(Task 1) 완료 후, GitHub에 변경사항이 push된 상태에서 진행합니다.

#### Step 1: Railway 가입 및 프로젝트 생성

1. [railway.app](https://railway.app) 접속 → "Start a New Project" 또는 GitHub 계정으로 가입·로그인
2. 대시보드에서 **"New Project"** 클릭

#### Step 2: 백엔드 서비스 생성

1. "Deploy from GitHub repo" 선택 → GitHub 계정 연결
2. `rag-project-1` 저장소 선택
3. **Root Directory 설정**: "Service Settings" → "Source" → Root Directory를 `backend`로 입력
4. 서비스 이름: `backend` (또는 원하는 이름)

#### Step 3: 프론트엔드 서비스 생성

1. 같은 프로젝트에서 **"+ New Service"** → "GitHub Repo" → 같은 저장소 선택
2. Root Directory를 `frontend`로 입력
3. 서비스 이름: `frontend`

#### Step 4: PostgreSQL 플러그인 추가

1. 프로젝트 화면에서 **"+ New Service"** → "Database" → "PostgreSQL" 선택
2. PostgreSQL 서비스 생성 완료 후:
3. 백엔드 서비스 클릭 → "Variables" 탭 → **"Add Variable Reference"** → PostgreSQL의 `DATABASE_URL` 선택
   - 이 단계에서 `DATABASE_URL`이 백엔드에 자동으로 연결됨 (로컬 `.env`의 값과 다름, Railway가 자동 생성)

#### Step 5: 백엔드 환경변수 설정

백엔드 서비스 → "Variables" 탭에서 아래 변수 추가:

| 변수명 | 값 | 설명 |
|--------|----|------|
| `OPENAI_API_KEY` | `sk-...` (실제 OpenAI 키) | OpenAI API 접근 키 |
| `ADMIN_PASSWORD` | (원하는 비밀번호) | 관리자 페이지 비밀번호 |
| `DATABASE_URL` | (Step 4에서 자동 연결됨) | PostgreSQL 접속 주소 |
| `ALLOWED_ORIGINS` | (이 단계에서는 일단 `http://localhost:3000`) | 나중에 프론트엔드 URL로 업데이트 |

#### Step 6: 백엔드 배포 및 URL 확인

1. 변수 저장 후 백엔드 서비스 "Deploy" 실행
2. 배포 완료 후 "Settings" → "Domains" → 백엔드 URL 확인
   - 예: `https://backend-production-xxxx.up.railway.app`
3. 이 URL을 복사해 두기 (다음 단계에서 프론트엔드에 입력)

#### Step 7: 프론트엔드 환경변수 설정 및 배포

프론트엔드 서비스 → "Variables" 탭:

| 변수명 | 값 |
|--------|-----|
| `NEXT_PUBLIC_API_URL` | `https://backend-production-xxxx.up.railway.app` (Step 6에서 복사한 URL) |

프론트엔드 "Deploy" 실행 → 완료 후 프론트엔드 URL 확인
- 예: `https://frontend-production-yyyy.up.railway.app`

#### Step 8: CORS 업데이트 (AC: #3)

1. 백엔드 서비스 → "Variables" 탭
2. `ALLOWED_ORIGINS` 값을 프론트엔드 URL로 변경:
   ```
   https://frontend-production-yyyy.up.railway.app
   ```
3. 저장 → 백엔드 자동 재배포 대기 (변수 변경 시 자동 재배포됨)

> **참고:** `main.py:12-13`에서 `ALLOWED_ORIGINS` 환경변수를 쉼표(,)로 구분하여 여러 URL 허용 가능.
> 예: `http://localhost:3000,https://frontend-production-yyyy.up.railway.app` (로컬+Railway 동시 허용)

#### Step 9: 최종 검증 (AC: #4, #5)

1. 프론트엔드 URL 접속 → "규정이" 채팅 화면 표시 확인
2. `{프론트엔드URL}/admin` 접속 → 비밀번호 입력창 표시 확인
3. 관리자 페이지에서 규정 PDF 업로드 → 임베딩 처리 완료 확인
4. 채팅 화면에서 샘플 질문 입력 → 답변 + 출처 조항 정상 반환 확인

---

### 배포 과정에서 발생할 수 있는 오류

| 오류 상황 | 원인 | 해결 방법 |
|----------|------|-----------|
| 백엔드 빌드 실패 — `No module named 'fastapi'` | `requirements.txt`를 찾지 못하거나 Root Directory 설정 오류 | Root Directory가 `backend`인지 확인 |
| 백엔드 시작 실패 — `ADMIN_PASSWORD 환경변수가 설정되지 않았습니다` | 환경변수 미입력 | Railway 백엔드 Variables에 `ADMIN_PASSWORD` 추가 |
| 프론트엔드 채팅 오류 — 요청이 백엔드로 전달 안 됨 | `NEXT_PUBLIC_API_URL` 미설정 또는 잘못된 URL | 프론트엔드 Variables에서 URL 확인 |
| CORS 오류 (브라우저 콘솔에 빨간 오류) | `ALLOWED_ORIGINS`에 프론트엔드 URL 미포함 | Step 8 절차대로 백엔드 `ALLOWED_ORIGINS` 업데이트 |
| 프론트엔드 빌드 실패 — TypeScript/ESLint 오류 | 코드 오류 | 로컬에서 `npx tsc --noEmit` 및 `npx eslint` 실행하여 오류 수정 후 재push |
| DB 연결 실패 | `DATABASE_URL` 미연결 | Step 4 절차대로 PostgreSQL `DATABASE_URL` 백엔드에 연결 |

---

### 현재 코드 상태 (변경 금지 파일)

| 파일 | 상태 | 이유 |
|------|------|------|
| `backend/main.py` | 변경 금지 | `ALLOWED_ORIGINS` 환경변수 읽기 이미 구현됨 (`main.py:12-13`) |
| `frontend/src/lib/api.ts` | 변경 금지 | `NEXT_PUBLIC_API_URL` 환경변수 사용 이미 구현됨 (`api.ts:3`) |
| `frontend/next.config.ts` | 변경 금지 | 배포에 추가 설정 불필요 (Nixpacks 자동 감지) |
| `docker-compose.yml` | 변경 금지 | 로컬 개발 전용, Railway에서는 PostgreSQL 플러그인 사용 |

---

### 이전 스토리 학습 (Story 2.3 완료 기준)

- `frontend/src/components/chat/ChatMessage.tsx`: sources 인용 블록 + amber "규정 외" 스타일 완성
- `frontend/src/components/chat/ChatInput.tsx`: `!e.nativeEvent.isComposing` IME 한국어 입력 보호 코드 있음 (삭제 금지)
- `frontend/` Next.js 빌드 상태: `npx next build` 통과 확인됨 (Story 2.3 완료 노트 기준)
- `backend/` 전체 서비스 (rag.py, embeddings.py, pdf.py, admin.py, chat.py, database.py) 구현 완료

---

### 기술 스택 참고

- **백엔드:** FastAPI 0.115.5 + Uvicorn 0.32.1 + Python (requirements.txt 기준)
- **프론트엔드:** Next.js 16.2.7 + React 19.2.4 + Tailwind CSS v4
- **DB:** PostgreSQL + pgvector (Railway 플러그인으로 제공)
- **Railway 빌드 시스템:** Nixpacks (자동 감지, Dockerfile 불필요)
  - Python: `requirements.txt` 감지 → pip install 자동 실행
  - Next.js: `package.json`의 `next` 패키지 감지 → `npm run build` 자동 실행

### References

- CORS 환경변수 구현: `backend/main.py:12-13`
- API URL 환경변수 사용: `frontend/src/lib/api.ts:3`
- 프론트엔드 빌드 스크립트: `frontend/package.json` (start 스크립트 수정 대상)
- 백엔드 패키지 목록: `backend/requirements.txt`
- 환경변수 문서: `backend/.env.example`
- 아키텍처 배포 섹션: `_bmad-output/planning-artifacts/architecture.md#인프라-및-배포`
- Epic 3 전체 내용: `_bmad-output/planning-artifacts/epics.md#epic-3`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- `backend/Procfile` 신규 생성: `web: uvicorn main:app --host 0.0.0.0 --port $PORT` — Railway Nixpacks가 Python 앱 시작 명령어를 읽는 파일. `--host 0.0.0.0`(외부 접속 허용), `--port $PORT`(Railway 자동 지정 포트) 적용. `--reload` 옵션 미포함(프로덕션 환경).
- `frontend/package.json` start 스크립트 수정: `"next start"` → `"next start -p $PORT"` — Railway 배포 환경에서 `$PORT` 환경변수로 포트 바인딩. `npx tsc --noEmit` 및 `npx eslint` 통과.
- `backend/.env.example` 업데이트: `ALLOWED_ORIGINS=http://localhost:3000` 항목 추가 — `main.py:12-13`에서 이미 해당 환경변수 읽도록 구현됨. Railway 배포 시 이 값을 Railway 프론트엔드 URL로 변경해야 함.
- ⚠️ **Task 2~6은 Catty가 Railway 대시보드에서 수동으로 진행해야 하는 단계입니다.** Dev Agent가 자동화할 수 없는 클라우드 배포 작업입니다. 스토리 Dev Notes의 "Railway 배포 단계별 절차" 참고.

### File List

- `backend/Procfile` (신규 생성)
- `frontend/package.json` (수정 — start 스크립트)
- `backend/.env.example` (수정 — ALLOWED_ORIGINS 추가)

### Change Log

- 2026-06-04: Story 3-1 코드 변경 완료 — `backend/Procfile` 신규 생성, `frontend/package.json` start 스크립트 `$PORT` 바인딩 적용, `backend/.env.example` ALLOWED_ORIGINS 문서화.
- 2026-06-04: Railway 배포 완료 (Catty 수동 진행) — 백엔드·프론트엔드·PostgreSQL 세 서비스 생성, 환경변수 설정, CORS 업데이트, 접속 검증 완료. 모든 AC 충족. 스토리 상태: review.
