"""Read-only schema and corpus checks; no automatic database migration or repair."""
from __future__ import annotations

from typing import Callable
import re

import psycopg


def inspect_database(connect: Callable[[], psycopg.Connection]) -> dict:
    queries = {
        "documents": "SELECT count(*) FROM documents",
        "chunks": "SELECT count(*) FROM chunks",
        "missing_embeddings": "SELECT count(*) FROM chunks WHERE embedding IS NULL",
        "zero_embeddings": "SELECT count(*) FROM chunks WHERE (embedding <#> embedding)=0",
        "orphan_chunks": "SELECT count(*) FROM chunks c LEFT JOIN documents d ON d.id=c.document_id WHERE d.id IS NULL",
        "empty_documents": "SELECT count(*) FROM documents d WHERE NOT EXISTS(SELECT 1 FROM chunks c WHERE c.document_id=d.id)",
        "broken_chunk_sequences": "SELECT count(*) FROM (SELECT document_id FROM chunks GROUP BY document_id HAVING min(chunk_index)<>0 OR max(chunk_index)<>count(*)-1 OR count(DISTINCT chunk_index)<>count(*)) s",
    }
    with connect() as conn, conn.cursor() as cur:
        cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        results = {}
        for name, query in queries.items():
            cur.execute(query)
            results[name] = cur.fetchone()[0]
        cur.execute("SELECT format_type(atttypid,atttypmod) FROM pg_attribute WHERE attrelid=to_regclass('public.chunks') AND attname='embedding' AND NOT attisdropped")
        row = cur.fetchone()
        results["embedding_column"] = row[0] if row else None
    faults = ("missing_embeddings", "zero_embeddings", "orphan_chunks", "empty_documents", "broken_chunk_sequences")
    valid_dimension = bool(re.fullmatch(r"vector\([1-9]\d*\)", results["embedding_column"] or ""))
    return {"ok": valid_dimension and not any(results[name] for name in faults), "checks": results,
            "repair_performed": False}
