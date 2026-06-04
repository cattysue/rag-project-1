import asyncio
import logging
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db
from routers import admin, chat

load_dotenv()

_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [o.strip() for o in _origins_env.split(",")]


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv("ADMIN_PASSWORD"):
        raise RuntimeError(
            "ADMIN_PASSWORD 환경변수가 설정되지 않았습니다. 서버를 시작할 수 없습니다."
        )
    if all(o.startswith("http://localhost") for o in allowed_origins):
        logging.warning(
            "ALLOWED_ORIGINS이 localhost만 허용합니다. "
            "프로덕션 배포 시 Railway 프론트엔드 URL을 ALLOWED_ORIGINS에 추가하세요."
        )
    await asyncio.to_thread(init_db)
    yield


app = FastAPI(title="규정이 API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(chat.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
