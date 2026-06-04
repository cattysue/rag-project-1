import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

MOCK_ANSWER = {
    "answer": "제3조에 따르면 성적 이의신청 기간은 성적 통보 후 5일 이내입니다.",
    "sources": [{"article_number": "제3조", "article_title": "성적 이의신청"}],
}

MOCK_EMPTY_ANSWER = {
    "answer": "해당 내용은 규정에 명시되어 있지 않습니다",
    "sources": [],
}


@pytest.fixture(autouse=True)
def no_db_init():
    with patch("main.init_db"):
        yield


def test_chat_response_structure():
    with patch("routers.chat.rag.get_chat_answer", return_value=MOCK_ANSWER):
        res = client.post("/chat", json={"question": "성적 이의신청 기간이 언제야?"})
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert "sources" in data
    assert isinstance(data["answer"], str)
    assert isinstance(data["sources"], list)


def test_chat_sources_have_required_fields():
    with patch("routers.chat.rag.get_chat_answer", return_value=MOCK_ANSWER):
        res = client.post("/chat", json={"question": "이의신청"})
    data = res.json()
    assert len(data["sources"]) > 0
    for source in data["sources"]:
        assert "article_number" in source
        assert "article_title" in source


def test_chat_no_relevant_content():
    with patch("routers.chat.rag.get_chat_answer", return_value=MOCK_EMPTY_ANSWER):
        res = client.post("/chat", json={"question": "오늘 날씨 어때?"})
    assert res.status_code == 200
    data = res.json()
    assert "규정에 명시되어 있지 않습니다" in data["answer"]
    assert data["sources"] == []


def test_chat_with_conversation_history():
    with patch("routers.chat.rag.get_chat_answer", return_value=MOCK_ANSWER) as mock_fn:
        res = client.post(
            "/chat",
            json={
                "question": "좀 더 자세히 설명해줘",
                "messages": [
                    {"role": "user", "content": "성적 이의신청 기간이 언제야?"},
                    {"role": "assistant", "content": "제3조에 따르면 5일 이내입니다."},
                ],
            },
        )
    assert res.status_code == 200
    call_args = mock_fn.call_args
    history = call_args[0][1]
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_chat_empty_question():
    with patch("routers.chat.rag.get_chat_answer", return_value=MOCK_EMPTY_ANSWER):
        res = client.post("/chat", json={"question": ""})
    assert res.status_code == 200
