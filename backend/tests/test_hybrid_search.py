"""하이브리드 검색 (BM25 + RRF) 단위 테스트."""
import pytest
from services.rag import _tokenize_korean, search_bm25, _reciprocal_rank_fusion


# ---------------------------------------------------------------------------
# _tokenize_korean
# ---------------------------------------------------------------------------

def test_tokenize_korean_basic():
    tokens = _tokenize_korean("성적 이의신청 기간은 얼마나 되나요?")
    assert "성적" in tokens
    assert "이의신청" in tokens
    assert "기간은" in tokens


def test_tokenize_korean_punctuation_removed():
    tokens = _tokenize_korean("결시(결석) 처리·방법, 안내")
    assert "" not in tokens          # 빈 문자열 없어야 함
    assert "결시" in tokens
    assert "결석" in tokens
    assert "처리" in tokens


def test_tokenize_korean_empty_string():
    assert _tokenize_korean("") == []


def test_tokenize_korean_whitespace_only():
    assert _tokenize_korean("   ") == []


# ---------------------------------------------------------------------------
# search_bm25
# ---------------------------------------------------------------------------

SAMPLE_CHUNKS = [
    {
        "chunk_text": "결시 학생의 성적 처리 방법은 다음과 같다",
        "article_number": "제5조",
        "article_title": "결시 처리",
    },
    {
        "chunk_text": "수행평가 반영 비율은 교과별로 다르게 정한다",
        "article_number": "제3조",
        "article_title": "수행평가 비율",
    },
    {
        "chunk_text": "성적 이의신청 기간은 성적 공개 후 5일 이내 제출한다",
        "article_number": "제8조",
        "article_title": "이의신청 기간",
    },
]


def test_search_bm25_empty_chunks():
    result = search_bm25("결석 처리", [])
    assert result == []


def test_search_bm25_returns_relevant_chunk():
    result = search_bm25("결석 처리 방법", SAMPLE_CHUNKS)
    assert len(result) > 0
    # "결시"/"결석" 포함 청크가 상위에 와야 함
    assert result[0]["article_number"] == "제5조"


def test_search_bm25_no_match_returns_empty():
    result = search_bm25("xyz123 없는단어", SAMPLE_CHUNKS)
    # BM25 점수 0인 항목은 제외
    assert result == []


def test_search_bm25_result_has_bm25_score():
    result = search_bm25("이의신청 기간", SAMPLE_CHUNKS)
    assert len(result) > 0
    assert "bm25_score" in result[0]
    assert result[0]["bm25_score"] > 0


def test_search_bm25_preserves_original_fields():
    result = search_bm25("수행평가 비율", SAMPLE_CHUNKS)
    assert len(result) > 0
    assert "chunk_text" in result[0]
    assert "article_number" in result[0]
    assert "article_title" in result[0]


# ---------------------------------------------------------------------------
# _reciprocal_rank_fusion
# ---------------------------------------------------------------------------

def _make_chunk(text: str, article: str) -> dict:
    return {"chunk_text": text, "article_number": article, "article_title": ""}


def test_rrf_deduplicates_common_chunk():
    chunk_a = _make_chunk("공통 결과", "제1조")
    chunk_b = _make_chunk("다른 결과", "제2조")
    vector = [chunk_a, chunk_b]
    bm25 = [chunk_a]
    result = _reciprocal_rank_fusion(vector, bm25)
    texts = [c["chunk_text"] for c in result]
    assert texts.count("공통 결과") == 1


def test_rrf_boosts_common_result_to_top():
    chunk_shared = _make_chunk("공통 결과", "제1조")
    chunk_vec_only = _make_chunk("벡터만", "제2조")
    vector = [chunk_vec_only, chunk_shared]  # 벡터에서는 1위가 chunk_vec_only
    bm25 = [chunk_shared]                    # BM25에서는 chunk_shared만
    result = _reciprocal_rank_fusion(vector, bm25)
    # 두 검색 모두 등장한 chunk_shared가 최종 1위여야 함
    assert result[0]["chunk_text"] == "공통 결과"


def test_rrf_empty_both_inputs():
    result = _reciprocal_rank_fusion([], [])
    assert result == []


def test_rrf_empty_vector_only_bm25():
    chunk = _make_chunk("BM25만", "제1조")
    result = _reciprocal_rank_fusion([], [chunk])
    assert len(result) == 1
    assert result[0]["chunk_text"] == "BM25만"


def test_rrf_empty_bm25_only_vector():
    chunk = _make_chunk("벡터만", "제1조")
    result = _reciprocal_rank_fusion([chunk], [])
    assert len(result) == 1
    assert result[0]["chunk_text"] == "벡터만"


def test_rrf_respects_top_k():
    # TOP_K=10이므로 입력이 15개여도 최대 10개 반환
    vector = [_make_chunk(f"청크{i}", f"제{i}조") for i in range(15)]
    result = _reciprocal_rank_fusion(vector, [])
    assert len(result) <= 10
