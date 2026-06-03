import tiktoken
from unittest.mock import MagicMock, patch
# _extract_chunks, _fallback_split은 단위 테스트 편의상 직접 임포트
# 시그니처 변경 시 이 테스트들도 함께 수정 필요
from services.pdf import (
    parse_pdf,
    _extract_chunks,
    _fallback_split,
    _truncate_chunk,
    MAX_CHUNK_TOKENS,
)

_ENC = tiktoken.get_encoding("cl100k_base")


def _mock_page(text: str) -> MagicMock:
    page = MagicMock()
    page.extract_text.return_value = text
    return page


# ── _extract_chunks() 기본 동작 ───────────────────────────────────────────

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


# ── Fix #1 검증: 본문 내 조항 참조가 분리 경계가 되지 않아야 함 ────────────

def test_inbody_article_reference_not_split():
    """'제3조에 따라'처럼 문장 중간 참조가 새 청크를 만들면 안 됨"""
    text = "제1조 (목적) 이 규정은 제3조에 따라 운영된다. 또한 제5조의 규정을 준용한다."
    pages = [(1, text)]
    chunks = _extract_chunks(pages)
    # 제1조만 분리되어야 함 — 제3조, 제5조는 본문 내 참조
    assert len(chunks) == 1
    assert chunks[0]["article_number"] == "제1조"
    assert "제3조에 따라" in chunks[0]["chunk_text"]


# ── Fix #2 검증: 긴 청크가 MAX_CHUNK_CHARS에서 잘림 ─────────────────────

def test_truncate_chunk_long_text():
    long_text = "가" * (MAX_CHUNK_TOKENS + 500)  # 한글 1자 ≈ 1토큰, 한도 초과 보장
    result = _truncate_chunk(long_text)
    assert len(_ENC.encode(result)) <= MAX_CHUNK_TOKENS


def test_truncate_chunk_short_text_unchanged():
    short_text = "제1조 내용"
    assert _truncate_chunk(short_text) == short_text


def test_long_article_chunk_is_truncated():
    long_body = "내용 " * 5000  # 토큰 한도 초과
    pages = [(1, f"제1조 (목적) {long_body}")]
    chunks = _extract_chunks(pages)
    assert chunks[0]["article_number"] == "제1조"
    assert len(_ENC.encode(chunks[0]["chunk_text"])) <= MAX_CHUNK_TOKENS


# ── Fix #3 검증: article_title 내부 공백·줄바꿈 정규화 ────────────────────

def test_article_title_normalizes_internal_newline():
    """PDF 추출 시 제목 괄호 안에 줄바꿈이 포함될 수 있음"""
    pages = [(1, "제2조 (이의\n신청) 이의신청은 다음과 같다.")]
    chunks = _extract_chunks(pages)
    assert chunks[0]["article_title"] == "이의 신청"


def test_article_title_normalizes_multiple_spaces():
    pages = [(1, "제3조 (성적  처리) 성적 처리 방법이다.")]
    chunks = _extract_chunks(pages)
    assert chunks[0]["article_title"] == "성적 처리"


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
