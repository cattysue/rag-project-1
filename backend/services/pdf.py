import re
from io import BytesIO

import tiktoken
from pypdf import PdfReader

# text-embedding-3-small 토큰 상한 8,191 대비 안전 마진 확보
# 문자 수 대신 실제 토큰 수로 잘라야 한국어에서도 한도 초과 없음
MAX_CHUNK_TOKENS = 7_500
_TOKENIZER = tiktoken.get_encoding("cl100k_base")

# (?m)^  → 줄 시작에서만 매칭 — 본문 내 "제N조에 따라" 참조를 분리 경계로 오인하지 않음
# named groups: num, title — 별도 re.match 재파싱 불필요
_ARTICLE_RE = re.compile(
    r'(?m)^[ \t]*(?P<header>제\s*(?P<num>\d+)\s*조(?:\s*\((?P<title>[^)]+)\))?)'
)


def parse_pdf(file_content: bytes) -> list[dict]:
    reader = PdfReader(BytesIO(file_content))
    pages_text: list[tuple[int, str]] = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages_text.append((page_num, text))
    return _extract_chunks(pages_text)


def _extract_chunks(pages_text: list[tuple[int, str]]) -> list[dict]:
    # O(n) 문자열 빌드 + 페이지 오프셋 추적
    parts: list[str] = []
    offsets: list[tuple[int, int]] = []
    pos = 0
    for page_num, text in pages_text:
        offsets.append((pos, page_num))
        page_text = text + "\n\n"  # 이중 줄바꿈 — 페이지 경계 단어 붙음 방지
        parts.append(page_text)
        pos += len(page_text)
    combined = "".join(parts)

    matches = list(_ARTICLE_RE.finditer(combined))

    if not matches:
        return _fallback_split(combined, offsets[0][1] if offsets else 1)

    chunks: list[dict] = []

    # 서문: 첫 조항 이전 텍스트
    preface = combined[: matches[0].start()].strip()
    if preface:
        chunks.extend(_fallback_split(preface, offsets[0][1]))

    for i, match in enumerate(matches):
        start = match.start("header")  # 선행 공백 제외, "제" 위치부터
        end = matches[i + 1].start() if i + 1 < len(matches) else len(combined)
        chunk_text = combined[start:end].strip()
        if not chunk_text:
            continue

        # named group으로 직접 추출 — 재파싱 없음
        article_number = f"제{match.group('num')}조"
        raw_title = match.group("title")
        article_title = re.sub(r"\s+", " ", raw_title).strip() if raw_title else None

        chunks.append({
            "chunk_text": _truncate_chunk(chunk_text),
            "article_number": article_number,
            "article_title": article_title,
            "page_number": _page_at(start, offsets),
        })

    return chunks


def _page_at(offset: int, offsets: list[tuple[int, int]]) -> int:
    page = offsets[0][1]
    for char_off, page_num in offsets:
        if offset >= char_off:
            page = page_num
        else:
            break
    return page


def _fallback_split(text: str, default_page: int) -> list[dict]:
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    return [
        {
            "chunk_text": _truncate_chunk(p),
            "article_number": None,
            "article_title": None,
            "page_number": default_page,
        }
        for p in paragraphs
    ]


def _truncate_chunk(text: str) -> str:
    tokens = _TOKENIZER.encode(text)
    if len(tokens) <= MAX_CHUNK_TOKENS:
        return text
    truncated = _TOKENIZER.decode(tokens[:MAX_CHUNK_TOKENS])
    last_nl = truncated.rfind("\n")
    return truncated[:last_nl].rstrip() if last_nl > len(truncated) // 2 else truncated
