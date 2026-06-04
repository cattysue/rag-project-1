import os
import re

import numpy as np
from openai import OpenAI
from rank_bm25 import BM25Okapi

from db.database import get_connection
from services.embeddings import get_embedding

TOP_K = 10
GPT_MODEL = "gpt-4o"

SYSTEM_PROMPT = """당신은 K고등학교 학업성적관리규정 전문 도우미 "규정이"입니다.
아래 [관련 조항] 내용만 근거로 교사의 질문에 답변하세요.
- 조항 번호와 항목명을 명시하여 출처를 밝혀 주세요.
- 제공된 조항에 답이 없으면 반드시 "해당 내용은 규정에 명시되어 있지 않습니다"라고만 답하세요.
- 추측하거나 외부 지식을 사용하지 마세요."""

NO_CONTENT_ANSWER = "해당 내용은 규정에 명시되어 있지 않습니다"

_gpt_client: OpenAI | None = None


def _get_gpt_client() -> OpenAI:
    global _gpt_client
    if _gpt_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다")
        _gpt_client = OpenAI(api_key=api_key)
    return _gpt_client


def search_similar_chunks(query_embedding: list[float]) -> list[dict]:
    """pgvector 코사인 거리로 유사 청크를 검색하여 상위 TOP_K 반환."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT chunk_text, article_number, article_title,
                       embedding <=> %s::vector AS distance
                FROM documents
                ORDER BY distance ASC
                LIMIT %s
                """,
                (np.array(query_embedding, dtype=np.float32), TOP_K),
            )
            rows = cur.fetchall()
    return [
        {
            "chunk_text": row[0],
            "article_number": row[1],
            "article_title": row[2],
            "distance": float(row[3]),
        }
        for row in rows
    ]


def get_all_chunks() -> list[dict]:
    """DB에서 전체 청크 로드 (BM25 색인용)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT chunk_text, article_number, article_title FROM documents ORDER BY id"
            )
            rows = cur.fetchall()
    return [
        {
            "chunk_text": row[0],
            "article_number": row[1],
            "article_title": row[2],
        }
        for row in rows
    ]


def _tokenize_korean(text: str) -> list[str]:
    """공백·구두점 단위 토크나이징 (한국어 BM25용)."""
    tokens = re.split(r'[\s\.,·\-\(\)\[\]·「」『』【】〔〕]+', text)
    return [t for t in tokens if t]


def search_bm25(query: str, chunks: list[dict]) -> list[dict]:
    """BM25 키워드 검색. 점수 > 0인 상위 TOP_K 반환."""
    if not chunks:
        return []
    tokenized_corpus = [_tokenize_korean(c["chunk_text"]) for c in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(_tokenize_korean(query))
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    return [
        {**chunks[i], "bm25_score": float(score)}
        for i, score in ranked[:TOP_K]
        if score > 0
    ]


def _reciprocal_rank_fusion(
    vector_chunks: list[dict],
    bm25_chunks: list[dict],
    k: int = 60,
) -> list[dict]:
    """RRF로 벡터/BM25 결과 합산. chunk_text 기준 중복 제거."""
    scores: dict[str, float] = {}
    chunks_by_text: dict[str, dict] = {}

    for rank, chunk in enumerate(vector_chunks):
        key = chunk["chunk_text"]
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        chunks_by_text[key] = chunk

    for rank, chunk in enumerate(bm25_chunks):
        key = chunk["chunk_text"]
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        chunks_by_text[key] = chunk

    sorted_keys = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [chunks_by_text[key] for key in sorted_keys[:TOP_K]]


_FALLBACK_ARTICLE_LABEL = "[서문/부칙]"


def _build_messages(
    question: str, chunks: list[dict], history: list[dict]
) -> list[dict]:
    # article_number가 없는 청크(서문·부칙)도 폴백 레이블로 포함 — 제외하면 빈 컨텍스트로 GPT 호출
    context = "\n\n".join(
        f"[{c.get('article_number') or _FALLBACK_ARTICLE_LABEL} {c.get('article_title', '')}]\n{c['chunk_text']}"
        for c in chunks
    )
    system_with_context = f"{SYSTEM_PROMPT}\n\n[관련 조항]\n{context}"
    messages: list[dict] = [{"role": "system", "content": system_with_context}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})
    return messages


def _deduplicate_sources(chunks: list[dict]) -> list[dict]:
    seen: set[str] = set()
    sources: list[dict] = []
    for chunk in chunks:
        key = chunk.get("article_number") or _FALLBACK_ARTICLE_LABEL
        if key not in seen:
            seen.add(key)
            sources.append(
                {
                    "article_number": chunk.get("article_number"),
                    "article_title": chunk.get("article_title"),
                }
            )
    return sources


def _expand_query(question: str) -> str:
    """GPT로 질문을 학업성적관리규정 용어로 재표현해 검색 정확도를 높인다."""
    client = _get_gpt_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 학업성적관리규정 문서 검색 도우미입니다. "
                    "사용자 질문을 규정 문서에서 쓰는 공식 용어로 바꿔 주세요. "
                    "원래 질문의 의미를 유지하면서 '이의신청', '반입', '결시', '결석', "
                    "'성적처리' 같은 공식 행정 용어를 사용하세요. "
                    "오직 바꾼 질문 한 문장만 출력하세요."
                ),
            },
            {"role": "user", "content": question},
        ],
        temperature=0,
        max_tokens=100,
    )
    return response.choices[0].message.content or question


def get_chat_answer(question: str, messages: list[dict]) -> dict:
    """하이브리드 검색(BM25 + 벡터)으로 관련 조항 검색 후 GPT-4o 답변 생성."""
    expanded = _expand_query(question)

    # 벡터 검색 (expanded → 원본 순서로 시도)
    vector_chunks = search_similar_chunks(get_embedding(expanded))
    if not vector_chunks:
        vector_chunks = search_similar_chunks(get_embedding(question))

    # BM25 키워드 검색
    all_chunks = get_all_chunks()
    bm25_chunks = search_bm25(expanded, all_chunks)
    if not bm25_chunks:
        bm25_chunks = search_bm25(question, all_chunks)

    # RRF 합산
    chunks = _reciprocal_rank_fusion(vector_chunks, bm25_chunks)

    if not chunks:
        return {"answer": NO_CONTENT_ANSWER, "sources": []}

    gpt_messages = _build_messages(question, chunks, messages)
    client = _get_gpt_client()
    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=gpt_messages,
        temperature=0,
    )
    answer = response.choices[0].message.content or NO_CONTENT_ANSWER
    sources = _deduplicate_sources(chunks)
    return {"answer": answer, "sources": sources}
