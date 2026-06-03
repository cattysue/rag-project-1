import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app

VALID_PASSWORD = "test-password"
AUTH_HEADERS = {"Authorization": VALID_PASSWORD}


@pytest.fixture(autouse=True)
def no_db_init():
    with patch("main.init_db"):
        yield


@pytest.fixture(autouse=True)
def set_admin_password(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", VALID_PASSWORD)


@pytest.fixture(autouse=True)
def reset_upload_status():
    import routers.admin as admin_module
    admin_module._upload_status.clear()
    admin_module._upload_status["status"] = "idle"
    yield


client = TestClient(app)


def _pdf_upload(password=VALID_PASSWORD, filename="규정.pdf"):
    return client.post(
        "/admin/upload",
        files={"file": (filename, b"%PDF-1.4 fake content", "application/pdf")},
        headers={"Authorization": password},
    )


# ── AC #1: 올바른 비밀번호 → 200 + {"status": "processing"} ──────────────────

def test_upload_valid_password_returns_processing():
    with patch("routers.admin._process_pdf"):
        response = _pdf_upload()
    assert response.status_code == 200
    assert response.json() == {"status": "processing"}


def test_upload_starts_background_task():
    with patch("routers.admin._process_pdf") as mock_process:
        _pdf_upload()
    mock_process.assert_called_once()


# ── AC #2: 잘못된 비밀번호 → 401 ──────────────────────────────────────────────

def test_upload_wrong_password_returns_401():
    response = _pdf_upload(password="wrong-password")
    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


# ── AC #2 (Authorization 헤더 없음) → 401 ────────────────────────────────────

def test_upload_no_auth_header_returns_401():
    response = client.post(
        "/admin/upload",
        files={"file": ("규정.pdf", b"%PDF-1.4 fake content", "application/pdf")},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


# ── AC #5: PDF 아닌 파일 → 400 ───────────────────────────────────────────────

def test_upload_non_pdf_returns_400():
    response = client.post(
        "/admin/upload",
        files={"file": ("document.txt", b"plain text content", "text/plain")},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 400


def test_upload_non_pdf_with_wrong_extension():
    response = client.post(
        "/admin/upload",
        files={"file": ("image.png", b"\x89PNG\r\n", "image/png")},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 400


# ── 파일 크기 제한 → 413 ──────────────────────────────────────────────────────

def test_upload_oversized_file_returns_413():
    import routers.admin as admin_module
    oversized = b"%PDF-1.4 " + b"x" * (admin_module.MAX_UPLOAD_BYTES + 1)
    response = client.post(
        "/admin/upload",
        files={"file": ("large.pdf", oversized, "application/pdf")},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 413


# ── 동시 업로드 방어 → 409 ───────────────────────────────────────────────────

def test_upload_while_processing_returns_409():
    import routers.admin as admin_module
    admin_module._upload_status["status"] = "processing"
    response = _pdf_upload()
    assert response.status_code == 409


# ── AC #3: GET /admin/status → 인증 필요 + 상태 반환 ─────────────────────────

def test_status_requires_auth():
    response = client.get("/admin/status")
    assert response.status_code == 401


def test_status_returns_current_state():
    response = client.get("/admin/status", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert "status" in response.json()


def test_status_returns_idle_by_default():
    response = client.get("/admin/status", headers=AUTH_HEADERS)
    assert response.json()["status"] == "idle"


def test_status_returns_processing_after_upload():
    with patch("routers.admin._process_pdf"):
        _pdf_upload()
    response = client.get("/admin/status", headers=AUTH_HEADERS)
    assert response.json()["status"] == "processing"


def test_status_valid_states():
    import routers.admin as admin_module
    for state in ("idle", "processing", "completed", "failed"):
        admin_module._upload_status["status"] = state
        response = client.get("/admin/status", headers=AUTH_HEADERS)
        assert response.json()["status"] == state


# ── AC #4: 기존 문서 교체 — _process_pdf 단위 테스트 ─────────────────────────

def test_process_pdf_calls_replace_documents():
    fake_chunks = [
        {"chunk_text": "제1조 내용", "article_number": "제1조",
         "article_title": "목적", "page_number": 1}
    ]
    fake_embeddings = [[0.1, 0.2, 0.3]]

    with patch("routers.admin.parse_pdf", return_value=fake_chunks), \
         patch("routers.admin.get_embeddings", return_value=fake_embeddings), \
         patch("routers.admin.replace_documents") as mock_replace:
        import routers.admin as admin_module
        admin_module._process_pdf(b"%PDF-1.4")
        mock_replace.assert_called_once_with(fake_chunks, fake_embeddings)


def test_process_pdf_sets_completed_on_success():
    import routers.admin as admin_module
    fake_chunks = [{"chunk_text": "제1조 내용", "article_number": "제1조",
                    "article_title": "목적", "page_number": 1}]
    with patch("routers.admin.parse_pdf", return_value=fake_chunks), \
         patch("routers.admin.get_embeddings", return_value=[[0.1] * 1536]), \
         patch("routers.admin.replace_documents"):
        admin_module._process_pdf(b"%PDF-1.4")
    assert admin_module._upload_status["status"] == "completed"


def test_process_pdf_empty_pdf_sets_failed():
    """텍스트 추출 불가 PDF(스캔 이미지 등) → 기존 문서 보존, status=failed"""
    import routers.admin as admin_module
    with patch("routers.admin.parse_pdf", return_value=[]), \
         patch("routers.admin.replace_documents") as mock_replace, \
         patch("routers.admin.get_embeddings") as mock_embed:
        admin_module._process_pdf(b"%PDF-1.4")
    assert admin_module._upload_status["status"] == "failed"
    assert "error" in admin_module._upload_status
    mock_replace.assert_not_called()
    mock_embed.assert_not_called()


def test_process_pdf_sets_failed_on_exception():
    import routers.admin as admin_module
    with patch("routers.admin.parse_pdf", side_effect=Exception("parse error")):
        admin_module._process_pdf(b"%PDF-1.4")
    assert admin_module._upload_status["status"] == "failed"


def test_process_pdf_stores_error_message():
    """실패 시 오류 메시지가 status dict에 저장됨"""
    import routers.admin as admin_module
    with patch("routers.admin.parse_pdf", side_effect=Exception("parse error")):
        admin_module._process_pdf(b"%PDF-1.4")
    assert admin_module._upload_status.get("error") == "parse error"


def test_process_pdf_clears_error_on_success():
    """이전 실패 후 재업로드 성공 시 error 필드가 제거됨"""
    import routers.admin as admin_module
    admin_module._upload_status["error"] = "previous error"
    fake_chunks = [{"chunk_text": "제1조 내용", "article_number": "제1조",
                    "article_title": "목적", "page_number": 1}]
    with patch("routers.admin.parse_pdf", return_value=fake_chunks), \
         patch("routers.admin.get_embeddings", return_value=[[0.1] * 1536]), \
         patch("routers.admin.replace_documents"):
        admin_module._process_pdf(b"%PDF-1.4")
    assert "error" not in admin_module._upload_status
