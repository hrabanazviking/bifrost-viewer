CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS documents (
    id          BIGSERIAL PRIMARY KEY,
    source      TEXT NOT NULL,
    title       TEXT,
    content_type TEXT,
    hash        TEXT UNIQUE,
    metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id           BIGSERIAL PRIMARY KEY,
    document_id  BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index  INT NOT NULL,
    text         TEXT NOT NULL,
    embedding    vector(768),
    tsv          tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    char_start   INT,
    char_end     INT,
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_tsv_gin
    ON chunks USING gin (tsv);
CREATE INDEX IF NOT EXISTS chunks_document_idx
    ON chunks (document_id);
CREATE INDEX IF NOT EXISTS documents_source_idx
    ON documents (source);
CREATE INDEX IF NOT EXISTS documents_metadata_gin
    ON documents USING gin (metadata);
