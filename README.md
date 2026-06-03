# 규정이 — 학업성적관리규정 RAG 챗봇

K고 교사를 위한 학업성적관리규정 질의응답 챗봇입니다.

## 로컬 실행 방법

### 1. PostgreSQL 데이터베이스 시작
```bash
docker-compose up -d
```

### 2. 백엔드 (FastAPI) 실행
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env   # 환경변수 설정 후
uvicorn main:app --reload
```
→ http://localhost:8000/docs 에서 API 문서 확인

### 3. 프론트엔드 (Next.js) 실행
```bash
cd frontend
npm install
npm run dev
```
→ http://localhost:3000 에서 챗봇 화면 확인

## 환경변수

`backend/.env.example` 파일을 복사하여 `backend/.env`를 만들고 값을 채워주세요.
