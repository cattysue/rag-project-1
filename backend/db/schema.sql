CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id              SERIAL PRIMARY KEY,
    chunk_text      TEXT NOT NULL,
    embedding       vector(1536) NOT NULL,
    article_number  VARCHAR(50),
    article_title   VARCHAR(200),
    page_number     INTEGER,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
