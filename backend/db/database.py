import os
import psycopg2
from contextlib import contextmanager
from psycopg2 import extras
from pgvector.psycopg2 import register_vector

# load_dotenv()는 main.py에서만 호출 — DB 레이어는 env 초기화 책임을 갖지 않음


@contextmanager
def get_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL 환경변수가 설정되지 않았습니다")
    conn = psycopg2.connect(db_url)
    register_vector(conn)
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()


def replace_documents(chunks: list[dict], embeddings: list[list[float]]) -> None:
    """기존 문서 전체 삭제 + 새 청크 저장을 단일 트랜잭션으로 처리 (원자성 보장).
    Story 1.5 관리자 업로드에서 clear + save 대신 이 함수를 사용할 것.
    """
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"chunks({len(chunks)})와 embeddings({len(embeddings)}) 길이가 다릅니다"
        )
    rows = [
        (
            chunk["chunk_text"],
            embedding,
            chunk.get("article_number"),
            chunk.get("article_title"),
            chunk.get("page_number"),
        )
        for chunk, embedding in zip(chunks, embeddings)
    ]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents")
            extras.execute_values(
                cur,
                """INSERT INTO documents
                       (chunk_text, embedding, article_number, article_title, page_number)
                   VALUES %s""",
                rows,
            )
        conn.commit()
