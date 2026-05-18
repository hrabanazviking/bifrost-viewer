CREATE TABLE IF NOT EXISTS kg_entities (
    id            BIGSERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    name_norm     TEXT NOT NULL,
    kind          TEXT,
    mentions      INT NOT NULL DEFAULT 0,
    UNIQUE (name_norm, kind)
);

CREATE INDEX IF NOT EXISTS kg_entities_name_norm_idx ON kg_entities (name_norm);
CREATE INDEX IF NOT EXISTS kg_entities_kind_idx ON kg_entities (kind);

CREATE TABLE IF NOT EXISTS kg_relations (
    id            BIGSERIAL PRIMARY KEY,
    subject_id    BIGINT NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    predicate     TEXT NOT NULL,
    object_id     BIGINT NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    chunk_id      BIGINT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    UNIQUE (subject_id, predicate, object_id, chunk_id)
);

CREATE INDEX IF NOT EXISTS kg_relations_subject_idx ON kg_relations (subject_id);
CREATE INDEX IF NOT EXISTS kg_relations_object_idx ON kg_relations (object_id);
CREATE INDEX IF NOT EXISTS kg_relations_chunk_idx ON kg_relations (chunk_id);

CREATE TABLE IF NOT EXISTS kg_extraction_progress (
    chunk_id      BIGINT PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
    status        TEXT NOT NULL,  -- 'done' | 'failed'
    error         TEXT,
    processed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS kg_extraction_progress_status_idx ON kg_extraction_progress (status);
