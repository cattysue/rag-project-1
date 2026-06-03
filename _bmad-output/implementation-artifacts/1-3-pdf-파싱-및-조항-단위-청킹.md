# Story 1.3: PDF 파싱 및 조항 단위 청킹

Status: review

## Story

As a 시스템,
I want PDF 파일을 "제○조" 패턴으로 조항 단위 분리하는 기능을,
so that 각 조항이 독립적인 검색 단위가 되고 출처 조항 번호를 메타데이터로 저장할 수 있다.

## Acceptance Criteria

1. **Given** 학업성적관리규정 PDF 파일이 주어졌을 때 **When** `pdf.py`의 파싱 함수를 실행하면 **Then** "제○조" 정규식 패턴으로 조항이 분리되고 각 청크에 `article_number`와 `article_title`이 추출된다
2. **Given** 서문·부칙처럼 조항 구분이 없는 텍스트가 포함된 경우 **When** 파싱 함수를 실행하면 **Then** 단락 단위 폴백 처리로 해당 텍스트도 누락 없이 청크로 분리된다
3. **Given** 파싱이 완료되었을 때 **When** 결과 청크 목록을 확인하면 **Then** 각 항목이 `chunk_text`, `article_number`, `article_title`, `page_number`를 포함한 딕셔너리다
4. **Given** `test_pdf_chunking.py`를 실행했을 때 **When** 샘플 텍스트에 대한 파싱 테스트가 수행되면 **Then** 조항 번호 추출 검증 테스트가 통과된다

## Tasks / Subtasks

- [x] Task 1: `backend/services/pdf.py` 작성 (AC: #1, #2, #3)
  - [x] `parse_pdf(file_content: bytes) -> list[dict]` 구현 (pypdf로 텍스트 추출)
  - [x] `_extract_chunks(pages_text)` 구현 ("제○조" 정규식 분리 + 서문 폴백)
  - [x] `_fallback_split(text, default_page)` 구현 (단락 단위 폴백)
  - [x] `_page_at(offset, offsets)` 구현 (텍스트 오프셋 → 페이지 번호 변환)

- [x] Task 2: `backend/tests/test_pdf_chunking.py` 작성 (AC: #4)
  - [x] 기본 조항 번호·제목 추출 테스트
  - [x] 서문(조항 없는 텍스트) 폴백 테스트
  - [x] 조항 전체 없음 → 단락 분리 테스트
  - [x] 반환 딕셔너리 필수 필드 존재 테스트
  - [x] 제목 없는 조항 처리 테스트
  - [x] `parse_pdf()` PdfReader 모킹 테스트

- [x] Task 3: 전체 테스트 실행 — 24 passed (기존 14 + 신규 10), 0 failures

## Dev Notes

### 이전 스토리에서 확립된 패턴 — 반드시 준수

**Story 1.1 / 1.2 코드리뷰를 통해 확립된 규칙:**
- `load_dotenv()` 호출 금지 — 서비스 파일에서 절대 호출하지 말 것. main.py 전담.
- 서비스 함수는 환경변수에 의존하지 않음 (pdf.py는 순수 텍스트 처리)
- 테스트는 외부 의존성(실제 PDF, 실제 DB)을 모킹으로 대체
- 모듈 수준 상수 패턴 사용 (test_db.py의 `SCHEMA_PATH` 패턴 참고)
- get_connection()은 `@contextmanager` — pdf.py는 DB를 사용하지 않음 (DB 저장은 Story 1.4)

### 이 스토리에서 생성되는 파일

```
backend/
└── services/
    ├── __init__.py     ← 기존 빈 파일, 수정 없음
    └── pdf.py          ← NEW
backend/
└── tests/
    └── test_pdf_chunking.py  ← NEW (AC #4에서 이름 명시됨)
```

> 수정되는 기존 파일 없음. 순수 신규 추가.

### backend/services/pdf.py 전체 구현

```python
import re
from io import BytesIO
from pypdf import PdfReader

# "제1조", "제12조 (제목)", "제12조(제목)" 등 모두 인식
_ARTICLE_RE = re.compile(r'(제\s*\d+\s*조(?:\s*\([^)]+\))?)')


def parse_pdf(file_content: bytes) -> list[dict]:
    reader = PdfReader(BytesIO(file_content))
    pages_text = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages_text.append((page_num, text))
    return _extract_chunks(pages_text)


def _extract_chunks(pages_text: list[tuple[int, str]]) -> list[dict]:
    # 전체 텍스트 + 페이지 오프셋 맵 구성
    combined = ""
    offsets: list[tuple[int, int]] = []  # (시작 offset, page_num)
    for page_num, text in pages_text:
        offsets.append((len(combined), page_num))
        combined += text + "\n"

    matches = list(_ARTICLE_RE.finditer(combined))

    # 조항이 전혀 없으면 전체를 단락 단위로 분리
    if not matches:
        return _fallback_split(combined, offsets[0][1] if offsets else 1)

    chunks: list[dict] = []

    # 서문: 첫 조항 이전 텍스트
    preface = combined[: matches[0].start()].strip()
    if preface:
        chunks.extend(_fallback_split(preface, offsets[0][1]))

    # 각 조항 처리
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(combined)
        chunk_text = combined[start:end].strip()
        if not chunk_text:
            continue

        header = match.group(0)
        m = re.match(r'제\s*(\d+)\s*조(?:\s*\(([^)]+)\))?', header)
        article_number = f"제{m.group(1)}조" if m else None
        article_title = m.group(2).strip() if m and m.group(2) else None

        chunks.append({
            "chunk_text": chunk_text,
            "article_number": article_number,
            "article_title": article_title,
            "page_number": _page_at(start, offsets),
        })

    return chunks


def _page_at(offset: int, offsets: list[tuple[int, int]]) -> int:
    """텍스트 오프셋에 해당하는 페이지 번호 반환"""
    page = offsets[0][1]
    for char_off, page_num in offsets:
        if offset >= char_off:
            page = page_num
        else:
            break
    return page


def _fallback_split(text: str, default_page: int) -> list[dict]:
    """조항 구분 없는 텍스트 → 빈 줄 단위로 단락 분리"""
    paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
    return [
        {
            "chunk_text": p,
            "article_number": None,
            "article_title": None,
            "page_number": default_page,
        }
        for p in paragraphs
    ]
```

### 설계 결정 및 주의사항

| 항목 | 결정 | 이유 |
|------|------|------|
| 입력 타입 | `bytes` | Story 1.5에서 FastAPI UploadFile.read()가 bytes 반환 |
| 조항 제목 없는 경우 | `article_title = None` | None으로 반환, 프론트에서 표시 시 처리 |
| 서문/부칙 | `article_number = None` | 검색 가능하지만 출처 표시 없음 |
| 공개 vs 비공개 함수 | `_` 접두어로 내부 함수 표시 | 테스트에서는 직접 임포트 가능 |
| 페이지 번호 추적 | 텍스트 offset 기반 | pypdf 페이지별 추출 후 합산 |

### 정규식 패턴 상세

```
_ARTICLE_RE = re.compile(r'(제\s*\d+\s*조(?:\s*\([^)]+\))?)')
```

- `제` : 한글 "제"
- `\s*\d+\s*` : 숫자 (공백 허용 — OCR/PDF 추출 시 공백 삽입 가능)
- `조` : 한글 "조"
- `(?:\s*\(([^)]+)\))?` : 선택적 제목 "(목적)" 등

**매칭 예시:**
- `"제1조 (목적)"` → article_number="제1조", article_title="목적"
- `"제12조(정의)"` → article_number="제12조", article_title="정의"
- `"제 3 조"` → article_number="제3조", article_title=None
- `"제100조 (부칙)"` → article_number="제100조", article_title="부칙"

### backend/tests/test_pdf_chunking.py 전체 구현

```python
from unittest.mock import MagicMock, patch
from services.pdf import parse_pdf, _extract_chunks, _fallback_split


def _mock_page(text: str) -> MagicMock:
    page = MagicMock()
    page.extract_text.return_value = text
    return page


# ── _extract_chunks() 단위 테스트 ─────────────────────────────────────────

def test_article_extraction_basic():
    pages = [(1, "제1조 (목적) 이 규정은 성적 관리를 목적으로 한다.\n\n제2조 (정의) 성적이란 평가 결과를 말한다.")]
    chunks = _extract_chunks(pages)
    assert len(chunks) == 2
    assert chunks[0]["article_number"] == "제1조"
    assert chunks[0]["article_title"] == "목적"
    assert chunks[1]["article_number"] == "제2조"
    assert chunks[1]["article_title"] == "정의"


def test_preface_becomes_fallback_chunks():
    pages = [(1, "K고등학교 학업성적관리규정\n\n이 규정은 학교에 적용된다.\n\n제1조 (목적) 목적이다.")]
    chunks = _extract_chunks(pages)
    preface_chunks = [c for c in chunks if c["article_number"] is None]
    article_chunks = [c for c in chunks if c["article_number"] == "제1조"]
    assert len(preface_chunks) >= 1
    assert len(article_chunks) == 1


def test_no_articles_entire_fallback():
    pages = [(1, "서문 단락 1\n\n서문 단락 2\n\n부칙 내용")]
    chunks = _extract_chunks(pages)
    assert len(chunks) == 3
    assert all(c["article_number"] is None for c in chunks)


def test_chunk_has_required_fields():
    pages = [(1, "제3조 (평가) 평가는 다음과 같이 한다.")]
    chunks = _extract_chunks(pages)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert "chunk_text" in chunk
        assert "article_number" in chunk
        assert "article_title" in chunk
        assert "page_number" in chunk


def test_article_without_title():
    pages = [(1, "제5조 내용만 있고 제목이 없는 조항.")]
    chunks = _extract_chunks(pages)
    assert chunks[0]["article_number"] == "제5조"
    assert chunks[0]["article_title"] is None


def test_multipage_page_number_tracking():
    pages = [
        (1, "제1조 (목적) 1페이지 내용"),
        (2, "제2조 (정의) 2페이지 내용"),
    ]
    chunks = _extract_chunks(pages)
    assert chunks[0]["page_number"] == 1
    assert chunks[1]["page_number"] == 2


# ── _fallback_split() 단위 테스트 ────────────────────────────────────────

def test_fallback_split_by_blank_lines():
    text = "단락 A\n\n단락 B\n\n단락 C"
    chunks = _fallback_split(text, default_page=1)
    assert len(chunks) == 3
    assert chunks[0]["chunk_text"] == "단락 A"
    assert all(c["page_number"] == 1 for c in chunks)
    assert all(c["article_number"] is None for c in chunks)


def test_fallback_split_ignores_empty_paragraphs():
    text = "단락 A\n\n\n\n단락 B"
    chunks = _fallback_split(text, default_page=1)
    assert len(chunks) == 2


# ── parse_pdf() 통합 테스트 (PdfReader mock) ──────────────────────────────

def test_parse_pdf_extracts_articles():
    mock_page = _mock_page("제1조 (목적) 이 규정의 목적을 설명한다.")
    with patch("services.pdf.PdfReader") as MockReader:
        MockReader.return_value.pages = [mock_page]
        chunks = parse_pdf(b"fake-pdf-bytes")
    assert len(chunks) == 1
    assert chunks[0]["article_number"] == "제1조"
    assert chunks[0]["page_number"] == 1


def test_parse_pdf_empty_page():
    mock_page = _mock_page("")
    with patch("services.pdf.PdfReader") as MockReader:
        MockReader.return_value.pages = [mock_page]
        chunks = parse_pdf(b"empty-page-pdf")
    assert isinstance(chunks, list)
```

### 명명 규칙 준수

| 항목 | 규칙 | 적용 |
|------|------|------|
| 파일명 | snake_case | `pdf.py` |
| 공개 함수 | snake_case | `parse_pdf()` |
| 내부 함수 | `_` 접두어 + snake_case | `_extract_chunks()`, `_fallback_split()`, `_page_at()` |
| 반환 딕셔너리 키 | snake_case | `chunk_text`, `article_number`, `article_title`, `page_number` |

### Story 1.4와의 연결 (미리 알아두기)

Story 1.4(임베딩 및 벡터 저장)에서 `parse_pdf()`의 반환값을 그대로 사용:
```python
# Story 1.4 예시 (미리 보기)
chunks = parse_pdf(file_content)
for chunk in chunks:
    embedding = get_embedding(chunk["chunk_text"])
    save_to_db(chunk, embedding)
```

→ `parse_pdf()` 반환 타입을 변경하지 말 것. `chunk_text`, `article_number`, `article_title`, `page_number` 4개 키는 Story 1.4, 1.5의 의존성.

### Project Structure Notes

- `pdf.py`는 `backend/services/` 폴더 안에 — `backend/` 루트나 `backend/routers/`에 두지 말 것
- `test_pdf_chunking.py`는 `backend/tests/` 폴더 안에 — AC #4에서 파일명 명시됨
- 테스트는 실제 PDF 파일 없이 MagicMock으로 PdfReader를 대체
- `services/__init__.py`는 수정하지 말 것 (빈 파일 유지)

### References

- AR-2 (청킹 전략): [Source: _bmad-output/planning-artifacts/epics.md#additional-requirements]
- AR-8 (PDF 파싱 라이브러리): [Source: _bmad-output/planning-artifacts/epics.md#additional-requirements]
- FR-2.3 (PDF 업로드 후 자동 임베딩): [Source: _bmad-output/planning-artifacts/epics.md#functional-requirements]
- 폴더 구조: [Source: _bmad-output/planning-artifacts/architecture.md#완성된-프로젝트-디렉토리-구조]
- 이전 스토리 패턴: [Source: _bmad-output/implementation-artifacts/1-2-데이터베이스-스키마-및-pgvector-초기화.md]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

- pypdf가 venv에 미설치 상태였음 → `pip install pypdf==5.1.0` 후 정상 동작

### Completion Notes List

- services/pdf.py: parse_pdf(), _extract_chunks(), _fallback_split(), _page_at() 구현
- 정규식: `제\s*\d+\s*조(?:\s*\([^)]+\))?` — 공백 포함 조항 번호, 선택적 제목 인식
- 서문/부칙(조항 없는 텍스트) → _fallback_split()으로 단락 단위 처리
- 멀티페이지 텍스트 오프셋 기반 페이지 번호 추적
- pytest 24 passed (기존 14 회귀 포함)

### File List

- `backend/services/pdf.py` (NEW)
- `backend/tests/test_pdf_chunking.py` (NEW)
