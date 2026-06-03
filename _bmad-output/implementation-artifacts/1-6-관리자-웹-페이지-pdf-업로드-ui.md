# Story 1.6: 관리자 웹 페이지 (PDF 업로드 UI)

Status: done

## Story

As a 관리자,
I want 웹 브라우저에서 비밀번호를 입력하고 규정 PDF를 업로드·교체할 수 있는 화면을,
so that 기술적 지식 없이도 새 규정 파일을 간편하게 시스템에 반영할 수 있다.

## Acceptance Criteria

1. **Given** `/admin` 페이지에 접속했을 때 **When** 비밀번호 입력창이 표시될 때 **Then** 올바른 비밀번호 입력 시 업로드 화면으로 진입하고, 틀린 비밀번호 입력 시 오류 메시지가 표시된다
2. **Given** 업로드 화면에서 PDF 파일을 선택하고 업로드 버튼을 누를 때 **When** 업로드 요청이 전송되면 **Then** "처리 중" 상태가 화면에 표시되고, 2초 간격으로 `/admin/status`를 폴링하여 상태가 갱신된다
3. **Given** 임베딩 처리가 완료된 경우 **When** 폴링 결과가 "completed"이면 **Then** "업로드 완료" 메시지가 화면에 표시되고 폴링이 중단된다
4. **Given** 임베딩 처리가 실패한 경우 **When** 폴링 결과가 "failed"이면 **Then** "처리 실패" 오류 메시지가 화면에 표시된다
5. **Given** 기존 규정 파일이 있는 상태에서 새 PDF를 업로드하는 경우 **When** 업로드가 시작되면 **Then** "기존 규정 파일을 새 파일로 교체합니다" 안내 문구가 화면에 표시된다

## Tasks / Subtasks

- [x] Task 1: `frontend/src/lib/types.ts` 작성 (AC: #1~#5)
  - [x] `UploadStatus` 타입: `"idle" | "processing" | "completed" | "failed"`
  - [x] `AdminStatus` 인터페이스: `{ status: UploadStatus }`
  - [x] `UploadResponse` 인터페이스: `{ status: string }`

- [x] Task 2: `frontend/src/lib/api.ts` 작성 (AC: #1, #2, #3, #4)
  - [x] `uploadPdf(file: File, password: string): Promise<UploadResponse>` — multipart POST to `/admin/upload`, Authorization 헤더에 비밀번호 포함
  - [x] `getAdminStatus(): Promise<AdminStatus>` — GET `/admin/status`
  - [x] 공통 baseUrl은 `process.env.NEXT_PUBLIC_API_URL` 사용

- [x] Task 3: `frontend/src/components/admin/FileUpload.tsx` 작성 (AC: #1~#5)
  - [x] `"use client"` 지시어 최상단 선언
  - [x] `password`, `file`, `uploadStatus`, `errorMessage` 상태 관리 (useState)
  - [x] 비밀번호 입력 단계: 비밀번호 입력창 + 확인 버튼
  - [x] 업로드 단계: 파일 선택 input + 업로드 버튼
  - [x] 업로드 시작 시 "기존 규정 파일을 새 파일로 교체합니다" 안내 표시
  - [x] 폴링 로직: `useEffect` + `setInterval` (2000ms), status가 "completed" 또는 "failed"이면 `clearInterval`
  - [x] 상태별 UI: processing(처리 중 + 스피너), completed(업로드 완료), failed(처리 실패)
  - [x] 401 응답 → "비밀번호가 올바르지 않습니다" 오류 + 비밀번호 단계로 초기화

- [x] Task 4: `frontend/src/app/admin/page.tsx` 작성 (AC: #1~#5)
  - [x] `FileUpload` 컴포넌트 import 및 렌더링
  - [x] 페이지 제목 "관리자 페이지" 표시

## Dev Notes

### 핵심 설계 결정

**비밀번호 검증 방식**: 별도의 로그인 API 없음. 비밀번호를 클라이언트 state에 저장하고 업로드 시 Authorization 헤더로 전송. 401 반환 시 오류 메시지 표시 + 비밀번호 입력 단계로 초기화.

**교체 안내 문구**: 항상 업로드 시작 시점에 표시 (백엔드가 항상 기존 문서를 전체 교체하므로). "completed" 상태 조회 불필요.

**폴링 종료 조건**: `useEffect` cleanup 함수에서 반드시 `clearInterval` 호출. "completed" 또는 "failed" 상태 수신 시, 컴포넌트 언마운트 시 모두 정리.

### 이전 스토리(1.5)에서 확립된 패턴 — 반드시 준수

| 항목 | 패턴 | 위반 시 결과 |
|------|------|-------------|
| Authorization 헤더 | 비밀번호 값 직접 전송 (예: `"Authorization": "mypassword"`) | Bearer prefix 추가하면 401 |
| 상태 값 | `"idle"`, `"processing"`, `"completed"`, `"failed"` | 다른 값 사용 시 UI 오작동 |
| 업로드 엔드포인트 | `POST /admin/upload` with `file` field (multipart) | 필드명 오류 시 400 |
| 상태 조회 | `GET /admin/status` (인증 불필요) | 인증 헤더 불필요 |

### 생성되는 파일 (전부 NEW)

```
frontend/src/
├── app/
│   └── admin/
│       └── page.tsx         ← NEW: 관리자 페이지 진입점
├── components/
│   └── admin/
│       └── FileUpload.tsx   ← NEW: 상태 관리 포함 업로드 컴포넌트
└── lib/
    ├── api.ts               ← NEW: 백엔드 API 호출 함수
    └── types.ts             ← NEW: TypeScript 타입 정의
```

기존 파일 수정 없음. `frontend/src/app/page.tsx`, `layout.tsx` 건드리지 말 것.

### 핵심 기술 스택 주의사항

**Next.js 16 + React 19 — AGENTS.md 경고: "This is NOT the Next.js you know"**

- App Router 사용 (`src/app/` 구조). `pages/` 디렉토리 방식 사용 금지
- 클라이언트 컴포넌트 필수: `useState`, `useEffect`, 이벤트 핸들러 사용 시 파일 최상단에 `"use client"` 선언 필수
- `page.tsx`는 기본적으로 서버 컴포넌트 → FileUpload처럼 인터랙션이 있는 로직은 별도 `"use client"` 컴포넌트로 분리

**Tailwind CSS v4 (기존 v3와 다름)**

- `tailwind.config.js` 파일 없음. `globals.css`의 `@import "tailwindcss"` 방식
- `@theme inline` 블록에서 커버 변수 정의됨 (`globals.css` 참조)
- 유틸리티 클래스명은 동일 (`bg-blue-500`, `flex`, `text-sm` 등)
- `tailwind.config.js`를 새로 만들거나 수정하지 말 것

**환경변수**

```
# frontend/.env.local (로컬 개발용, 이미 .env.example에 안내됨)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

`NEXT_PUBLIC_` 접두사 없으면 브라우저에서 `undefined` — `api.ts`에서 반드시 `NEXT_PUBLIC_API_URL` 사용.

### api.ts 구현 가이드

```typescript
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function uploadPdf(file: File, password: string) {
  const formData = new FormData();
  formData.append("file", file);  // 필드명 "file" 정확히 일치해야 함 (Story 1.5 admin.py 참조)

  const res = await fetch(`${BASE_URL}/admin/upload`, {
    method: "POST",
    headers: { Authorization: password },  // Bearer prefix 없음, 값 그대로
    body: formData,
    // Content-Type 헤더 수동 설정 금지 — FormData일 때 브라우저가 boundary 포함해서 자동 설정
  });

  if (res.status === 401) throw new Error("UNAUTHORIZED");
  if (!res.ok) throw new Error("UPLOAD_FAILED");
  return res.json();
}

export async function getAdminStatus() {
  const res = await fetch(`${BASE_URL}/admin/status`);
  return res.json();
}
```

### FileUpload.tsx 상태 흐름

```
초기 상태: step="password" (비밀번호 입력 화면)
  ↓ 비밀번호 입력 + 확인
step="upload" (파일 선택 + 업로드 화면)
  ↓ 파일 선택 + 업로드 버튼 클릭
    → "기존 규정 파일을 새 파일로 교체합니다" 표시
    → POST /admin/upload 호출
      → 401: step="password" 초기화, 오류 메시지 표시
      → 200: uploadStatus="processing", 폴링 시작
        ↓ GET /admin/status 2초 간격 폴링
          → "completed": uploadStatus="completed", 폴링 중단
          → "failed": uploadStatus="failed", 폴링 중단
```

### 폴링 구현 패턴

```typescript
useEffect(() => {
  if (uploadStatus !== "processing") return;
  
  const intervalId = setInterval(async () => {
    const data = await getAdminStatus();
    if (data.status === "completed" || data.status === "failed") {
      setUploadStatus(data.status);
      clearInterval(intervalId);
    }
  }, 2000);

  return () => clearInterval(intervalId);  // cleanup 필수
}, [uploadStatus]);
```

### AR 요구사항 체크

| AR | 내용 | 구현 위치 |
|----|------|----------|
| AR-6 | 관리자 업로드: 2초 간격 폴링 | FileUpload.tsx useEffect |
| AR-10 | frontend/.env.local: NEXT_PUBLIC_API_URL | api.ts BASE_URL |
| AR-11 | JS/TS camelCase, React PascalCase | FileUpload.tsx, api.ts, types.ts |

### References

- AR-4 (인증): [Source: _bmad-output/planning-artifacts/epics.md#additional-requirements]
- AR-6 (폴링): [Source: _bmad-output/planning-artifacts/epics.md#additional-requirements]
- AR-10 (환경변수): [Source: _bmad-output/planning-artifacts/epics.md#additional-requirements]
- AR-11 (명명규칙): [Source: _bmad-output/planning-artifacts/epics.md#additional-requirements]
- API 계약 (Authorization 헤더, 상태값): [Source: _bmad-output/implementation-artifacts/1-5-관리자-pdf-업로드-교체-상태-api.md]
- Next.js App Router: [Source: frontend/AGENTS.md — "read node_modules/next/dist/docs/ before writing code"]
- Tailwind v4 설정: [Source: frontend/src/app/globals.css, frontend/package.json]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `next lint` 명령어가 `lint` 서브디렉토리를 찾으려 해서 실패 → `npx eslint src/...` 직접 실행으로 대체, 정상 통과

### Completion Notes List

- `frontend/src/lib/types.ts` 신규 생성: UploadStatus 유니온 타입, AdminStatus·UploadResponse 인터페이스
- `frontend/src/lib/api.ts` 신규 생성: uploadPdf() (multipart POST, Authorization 헤더), getAdminStatus() (GET /admin/status)
- `frontend/src/components/admin/FileUpload.tsx` 신규 생성: "use client" 컴포넌트, 비밀번호→업로드 2단계 UI, 2초 폴링, 상태별 피드백
- `frontend/src/app/admin/page.tsx` 신규 생성: 서버 컴포넌트 페이지, metadata 포함, FileUpload 렌더링
- TypeScript 타입 검사 통과 (오류 없음)
- ESLint 검사 통과 (경고 없음)
- Next.js production build 성공: `/admin` 라우트 정상 생성

### File List

- `frontend/src/lib/types.ts` (신규)
- `frontend/src/lib/api.ts` (신규)
- `frontend/src/components/admin/FileUpload.tsx` (신규)
- `frontend/src/app/admin/page.tsx` (신규)

### Review Findings

#### Decision Needed
- [x] [Review][Decision] D1 — AC5: 교체 안내 문구 항상 표시 → **결정: 현행 유지** (항상 표시, 변경 없음)
- [x] [Review][Decision] D2 — AC1: 비밀번호 즉시 검증 → **결정: GET /admin/status에 auth 추가** (backend admin.py + test_admin.py + api.ts + FileUpload.tsx 수정)

#### Patches — High
- [x] [Review][Patch] P1 — `setUploadStatus("processing")` 호출이 `uploadPdf` 완료 전이라 이전 job의 stale status를 폴링이 읽어 오탐 가능 [FileUpload.tsx:50-55]
- [x] [Review][Patch] P2 — 업로드 "failed" 후 업로드 버튼이 사라져 페이지 새로고침 없이 재시도 불가 [FileUpload.tsx:128-136]
- [x] [Review][Patch] P3 — 폴링 타임아웃 없음 — 백엔드가 멈추면 "처리 중..." 스피너가 무한 회전 [FileUpload.tsx:17-34]

#### Patches — Medium
- [x] [Review][Patch] P4 — 비-401 실패 시 `showReplaceWarning`이 `true`로 유지돼 재시도 시 교체 경고가 이미 보임 [FileUpload.tsx:64-66]
- [x] [Review][Patch] P5 — `useRef`로 intervalId 관리 필요 — React StrictMode 이중 실행 시 두 개의 interval이 동시 실행될 수 있음 [FileUpload.tsx:20]
- [x] [Review][Patch] P6 — `getAdminStatus()` 런타임 타입 검증 없음 — 백엔드가 예상 외 status 값 반환 시 폴링이 무한 실행 [api.ts:27, FileUpload.tsx:23-24]
- [x] [Review][Patch] P7 — 업로드 완료 후 `password` state 미초기화 — 컴포넌트 생존 중 평문 비밀번호가 메모리에 잔류 [FileUpload.tsx:10]
- [x] [Review][Patch] P8 — `AbortController` 없음 — 사용자가 페이지 이탈 시 in-flight fetch가 setState 호출 [api.ts:12-16]

#### Patches — Low
- [x] [Review][Patch] P9 — `NEXT_PUBLIC_API_URL` 미설정 시 무음으로 `localhost:8000`으로 폴백 — 프로덕션 배포 오류 진단 어려움 [api.ts:3]
- [x] [Review][Patch] P10 — 파일 MIME/크기 클라이언트 검증 없음 — `accept=".pdf"` 는 UI 힌트일 뿐 우회 가능 [FileUpload.tsx:115]
- [x] [Review][Patch] P11 — `UploadResponse.status` 타입이 `string`으로 느슨함 — `UploadStatus`로 교체 [types.ts:7]
- [x] [Review][Patch] P12 — 비-401 실패 후 파일 input이 이전 파일명을 유지 — P2 재시도 버튼 추가 시 함께 초기화 필요 [FileUpload.tsx:64-66]

#### Deferred
- [x] [Review][Defer] W1 — 폴링 첫 tick이 2초 후라 백엔드가 즉시 완료해도 최대 2초 지연 표시 — 경미한 UX 갭, 현재 범위 초과 [FileUpload.tsx:20]

### Change Log

- 2026-06-03: Story 1.6 구현 완료 — 관리자 PDF 업로드 UI (types.ts, api.ts, FileUpload.tsx, admin/page.tsx 신규 생성)
- 2026-06-03: 코드 리뷰 완료 — 2 decision-needed, 12 patch, 1 defer, 3 dismiss
