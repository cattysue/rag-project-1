import hmac
import logging
import os
import tempfile
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, UploadFile

from db.database import replace_documents
from services.embeddings import get_embeddings
from services.pdf import parse_pdf

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin")

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50MB

_upload_status: dict = {"status": "idle"}


def verify_admin(authorization: str | None = Header(default=None)) -> None:
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_password:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not hmac.compare_digest(
        (authorization or "").encode("utf-8"),
        admin_password.encode("utf-8"),
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _process_pdf(file_content: bytes) -> None:
    try:
        chunks = parse_pdf(file_content)
        texts = [c["chunk_text"] for c in chunks]
        if not texts:
            _upload_status["status"] = "failed"
            _upload_status["error"] = "PDF에서 텍스트를 추출할 수 없습니다. 스캔 이미지 PDF인지 확인하세요."
            return
        embeddings = get_embeddings(texts)
        replace_documents(chunks, embeddings)
        _upload_status["status"] = "completed"
        _upload_status.pop("error", None)
    except Exception as e:
        logger.exception("PDF 처리 실패")
        _upload_status["status"] = "failed"
        _upload_status["error"] = str(e)


def _process_pdf_from_path(tmp_path: str) -> None:
    try:
        with open(tmp_path, "rb") as f:
            file_content = f.read()
        _process_pdf(file_content)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            logger.warning("임시 파일 삭제 실패: %s", tmp_path)


@router.post("/upload")
async def upload_pdf(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_admin),
):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"파일 크기가 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB를 초과합니다",
        )

    # await 이후에 체크+쓰기 — 사이에 yield 없으므로 두 요청이 동시에 통과 불가
    if _upload_status["status"] == "processing":
        raise HTTPException(status_code=409, detail="이미 처리 중인 파일이 있습니다")

    # 임시 파일로 저장 후 bytes 즉시 해제 — 대용량 파일이 백그라운드 처리 전체 기간 동안 메모리에 잔류하지 않도록
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    del content

    _upload_status["status"] = "processing"
    _upload_status.pop("error", None)
    background_tasks.add_task(_process_pdf_from_path, tmp_path)
    return {"status": "processing"}


@router.get("/status")
async def get_status(_: None = Depends(verify_admin)):
    return _upload_status
