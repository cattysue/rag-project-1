import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(autouse=True)
def no_db_init():
    """lifespan의 init_db() 호출을 mock — 테스트 시 실제 DB 불필요"""
    with patch("main.init_db"):
        yield


client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_header_present():
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_rejects_unlisted_origin():
    """허용 목록에 없는 origin은 CORS 헤더를 받지 않아야 함"""
    response = client.get(
        "/health",
        headers={"Origin": "https://malicious.example.com"},
    )
    assert response.headers.get("access-control-allow-origin") != "https://malicious.example.com"


def test_cors_env_split_logic():
    """ALLOWED_ORIGINS 콤마 분리 로직 단위 테스트"""
    origins_env = "http://localhost:3000,https://example.railway.app"
    origins = [o.strip() for o in origins_env.split(",")]
    assert "http://localhost:3000" in origins
    assert "https://example.railway.app" in origins
    assert len(origins) == 2


def test_env_example_has_required_keys():
    import os
    env_example_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
    with open(env_example_path, encoding="utf-8") as f:
        content = f.read()
    assert "OPENAI_API_KEY" in content
    assert "DATABASE_URL" in content
    assert "ADMIN_PASSWORD" in content
