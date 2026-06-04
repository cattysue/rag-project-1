import os

import numpy as np
from openai import OpenAI

from db.database import get_connection
from services.embeddings import get_embedding

SIMILARITY_THRESHOLD = 0.75  # cosine distance — 이 값 이상이면 관련 조항 없음으로 판단
TOP_K = 5
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
    """pgvector 코사인 거리로 유사 청크를 검색하고 임계값 이하만 반환."""
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
        if float(row[3]) < SIMILARITY_THRESHOLD
    ]


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


def get_chat_answer(question: str, messages: list[dict]) -> dict:
    """질문을 임베딩하고 유사 조항을 검색한 뒤 GPT-4o 답변을 생성한다.

    유사 조항이 없으면 GPT를 호출하지 않고 환각 방지 메시지를 반환한다.
    """
    query_embedding = get_embedding(question)
    chunks = search_similar_chunks(query_embedding)

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
