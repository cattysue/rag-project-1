import logging
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import rag

logger = logging.getLogger(__name__)

router = APIRouter()


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


MAX_HISTORY_TURNS = 50


class ChatRequest(BaseModel):
    question: str
    messages: list[Message] = []


class Source(BaseModel):
    article_number: str | None
    article_title: str | None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    history = [m.model_dump() for m in req.messages[-MAX_HISTORY_TURNS:]]
    try:
        result = rag.get_chat_answer(req.question, history)
    except Exception:
        logger.exception("RAG 파이프라인 오류")
        raise HTTPException(status_code=500, detail="답변 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")
    return ChatResponse(
        answer=result["answer"],
        sources=[Source(**s) for s in result["sources"]],
    )
