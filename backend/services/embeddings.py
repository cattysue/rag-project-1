import os
from openai import OpenAI

# Story 2.1 rag.py에서도 이 상수를 임포트해야 함 — 저장/검색 모델이 반드시 일치해야 함
EMBEDDING_MODEL = "text-embedding-3-small"

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다")
        _client = OpenAI(api_key=api_key)
    return _client


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """배치 임베딩 — 단일 API 호출로 여러 텍스트를 처리"""
    client = _get_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    if not response.data:
        raise ValueError(
            f"OpenAI 임베딩 응답이 비어있습니다 (입력 개수: {len(texts)})"
        )
    return [item.embedding for item in response.data]


def get_embedding(text: str) -> list[float]:
    """단일 텍스트 임베딩 편의 함수"""
    return get_embeddings([text])[0]
