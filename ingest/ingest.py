"""Ingest documents into the knowledge Postgres+pgvector DB.

Usage:
    uv run ingest.py add <file-or-url>
    uv run ingest.py search "<query>" [--k 5]
    uv run ingest.py stats
    uv run ingest.py list
    uv run ingest.py delete <doc-id>
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
from pathlib import Path

import httpx
import psycopg
import typer
from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from psycopg.types.json import Jsonb
from rich.console import Console
from rich.table import Table

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))
from embedding import embed_all  # noqa: E402
from recovery import (  # noqa: E402
    ConfigurationFailure, InputFailure, check_source, database_retry,
    failure, progress, required, setting, source_signature,
)

load_dotenv(Path(os.getenv("INGEST_ENV_FILE", str(Path(__file__).parent / ".env"))))

DB_URL = os.environ.get("INGEST_DB_URL", "")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "")
EMBED_MODEL = os.environ.get("INGEST_EMBED_MODEL", "")

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


def get_conn() -> psycopg.Connection:
    required(DB_URL, OLLAMA_URL, EMBED_MODEL)
    options = f"-c statement_timeout={setting('db_statement_timeout_ms')} -c lock_timeout={setting('db_lock_timeout_ms')}"
    conn = psycopg.connect(DB_URL, connect_timeout=setting("db_connect_timeout"), options=options)
    try:
        register_vector(conn)
        conn.commit()  # finish type discovery before caller's read-only snapshot
    except Exception:
        conn.close()
        raise
    return conn


def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    required(DB_URL, OLLAMA_URL, EMBED_MODEL)
    with httpx.Client() as client:
        return embed_all(client, OLLAMA_URL, EMBED_MODEL, texts)


def _jsonl_record_to_text(rec) -> str:
    """Render one JSONL record as readable text.
    Handles common training-data shapes: ChatML in a "text" field, ShareGPT
    "conversations" (from/value), OpenAI "messages" (role/content), and falls
    back to pretty-printed JSON.
    """
    import json
    import re
    if isinstance(rec, dict):
        if isinstance(rec.get("conversations"), list):
            parts = []
            for turn in rec["conversations"]:
                if not isinstance(turn, dict):
                    continue
                role = str(turn.get("from") or turn.get("role") or "speaker").strip()
                val = turn.get("value") if "value" in turn else turn.get("content", "")
                parts.append(f"[{role}] {val}")
            return "\n\n".join(parts)
        if isinstance(rec.get("messages"), list):
            parts = []
            for m in rec["messages"]:
                if not isinstance(m, dict):
                    continue
                parts.append(f"[{m.get('role','speaker')}] {m.get('content','')}")
            return "\n\n".join(parts)
        if isinstance(rec.get("text"), str):
            t = rec["text"]
            # Decode escaped \n the file may contain literally
            t = t.replace("\\n", "\n").replace("\\t", "\t") if "\\n" in t else t
            # Strip ChatML markers but keep role labels
            t = re.sub(r"<\|im_start\|>(\w+)\s*", r"[\1] ", t)
            t = re.sub(r"<\|im_end\|>", "", t)
            return t.strip()
        if "prompt" in rec or "completion" in rec or "response" in rec:
            p = rec.get("prompt") or rec.get("instruction") or rec.get("input") or ""
            c = rec.get("completion") or rec.get("response") or rec.get("output") or ""
            return f"[prompt] {p}\n\n[response] {c}".strip()
    return json.dumps(rec, indent=2, ensure_ascii=False)


def parse_source(src: str) -> tuple[str, str, list[str]]:
    """Return (title, content_type, chunk_texts) for any file path or URL."""
    if src.startswith(("http://", "https://")):
        import trafilatura

        from safe_fetch import fetch_public
        downloaded = fetch_public(src)
        md = trafilatura.extract(downloaded, output_format="markdown") or ""
        meta = trafilatura.extract_metadata(downloaded)
        title = (meta.title if meta and meta.title else src)
        from unstructured.partition.md import partition_md
        elements = partition_md(text=md)
        content_type = "web/markdown"
    else:
        p = Path(src).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(p)
        title = p.name
        content_type = p.suffix.lstrip(".") or "unknown"
        if p.suffix.lower() == ".txt" and os.getenv("INGEST_API_JOB_ID"):
            return title, content_type, _text_chunks(p.read_text(encoding="utf-8"))
        elif p.suffix.lower() == ".json":
            import json
            from unstructured.documents.elements import Text
            data = json.loads(p.read_text(encoding="utf-8"))
            elements = [Text(text=json.dumps(data, indent=2, ensure_ascii=False))]
        elif p.suffix.lower() == ".jsonl":
            elements = _jsonl_elements(p)
        else:
            from unstructured.partition.auto import partition
            elements = partition(filename=str(p))

    from unstructured.chunking.basic import chunk_elements
    chunk_chars, overlap = setting("chunk_chars"), setting("chunk_overlap")
    if overlap >= chunk_chars:
        raise ConfigurationFailure("Chunk overlap must be smaller than chunk size")
    chunks = chunk_elements(
        elements,
        max_characters=chunk_chars,
        new_after_n_chars=int(chunk_chars * 0.75),
        overlap=overlap,
    )
    return title, content_type, [str(c) for c in chunks if str(c).strip()]


def _text_chunks(text: str) -> list[str]:
    """API text is already extracted: preserve its characters and whitespace."""
    maximum, overlap = setting("chunk_chars"), setting("chunk_overlap")
    if overlap >= maximum:
        raise ConfigurationFailure("Chunk overlap must be smaller than chunk size")
    if not text.strip():
        return []
    chunks = []
    for start in range(0, len(text), maximum - overlap):
        chunk = text[start:start + maximum]
        chunks.append(chunk)
        if start + maximum >= len(text):
            break
    return chunks


def _jsonl_elements(path: Path) -> list:
    from unstructured.documents.elements import Text
    elements = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                raise InputFailure(f"Malformed JSONL at line {line_number}; no records inserted") from None
            elements.append(Text(text=_jsonl_record_to_text(record)))
    return elements


def _existing_document(content_hash: str) -> int | None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM documents WHERE hash = %s", (content_hash,))
        existing = cur.fetchone()
        return existing[0] if existing else None


def _target_dimension() -> int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT format_type(atttypid,atttypmod) FROM pg_attribute WHERE attrelid=to_regclass('public.chunks') AND attname='embedding' AND NOT attisdropped")
        row = cur.fetchone()
    match = re.fullmatch(r"vector\((\d+)\)", row[0]) if row else None
    if not match:
        raise ConfigurationFailure("Configure a fixed-dimension public.chunks embedding column first")
    return int(match[1])


def _record(source: str, title: str, content_type: str, content_hash: str) -> tuple:
    metadata = {}
    if os.getenv("INGEST_API_JOB_ID"):
        metadata = {"api_job_id": os.environ["INGEST_API_JOB_ID"], "api_client_id": os.environ["INGEST_API_CLIENT_ID"]}
        title = os.getenv("INGEST_SUBMISSION_TITLE") or title
        if not source.startswith(("https://", "http://")):
            source = f"bifrost-api://{metadata['api_client_id']}/{metadata['api_job_id']}"
    return source, title, content_type, content_hash, Jsonb(metadata)


def _persist(record: tuple, texts: list[str], embeddings: list[list[float]]) -> int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (source, title, content_type, hash, metadata) VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (hash) DO NOTHING RETURNING id",
            record,
        )
        inserted = cur.fetchone()
        if inserted is None:
            cur.execute("SELECT id FROM documents WHERE hash=%s", (record[3],))
            return cur.fetchone()[0]
        doc_id = inserted[0]
        cur.executemany(
            "INSERT INTO chunks (document_id, chunk_index, text, embedding) VALUES (%s, %s, %s, %s)",
            [(doc_id, i, text, embedding) for i, (text, embedding) in enumerate(zip(texts, embeddings, strict=True))],
        )
        conn.commit()
    return doc_id


@app.command()
def add(source: str) -> None:
    """Ingest a stable file or public URL with atomic, idempotent DB retries."""
    required(DB_URL, OLLAMA_URL, EMBED_MODEL)
    signature = source_signature(source)
    progress("parsing", .05)
    title, content_type, texts = parse_source(source)
    check_source(source, signature)
    if not texts:
        raise InputFailure("No content extracted; source retained")
    if any("\x00" in text for text in texts):
        raise InputFailure("Parsed text contains NUL; correct source encoding")
    progress("validating", .15, chunks=len(texts))
    content_hash = hashlib.sha256("\n".join(texts).encode("utf-8")).hexdigest()
    existing = database_retry(lambda: _existing_document(content_hash))
    if existing is not None:
        progress("done", 1., doc_id=existing, chunks=len(texts))
        console.print(f"Already ingested as doc_id={existing} (hash match)")
        return
    dimension = database_retry(_target_dimension)
    embeddings = embed(texts)
    if any(len(vector) != dimension for vector in embeddings):
        raise ConfigurationFailure("Embedding model dimension differs from target database")
    check_source(source, signature)
    progress("persisting", .9, chunks=len(texts))
    record = _record(source, title, content_type, content_hash)
    doc_id = database_retry(lambda: _persist(record, texts, embeddings))
    progress("done", 1., doc_id=doc_id, chunks=len(texts))
    console.print(f"Indexed doc_id={doc_id}; chunks={len(texts)}")


@app.command()
def search(query: str, k: int = 5, hybrid: bool = True) -> None:
    """Semantic (and optionally hybrid keyword) search."""
    q_emb = embed([query])[0]
    with get_conn() as conn, conn.cursor() as cur:
        if hybrid:
            cur.execute(
                """
                WITH sem AS (
                    SELECT c.id, c.text, d.source, d.title,
                           1 - (c.embedding <=> %s::vector) AS sim_score,
                           ROW_NUMBER() OVER (ORDER BY c.embedding <=> %s::vector) AS sem_rank
                    FROM chunks c JOIN documents d ON c.document_id = d.id
                    ORDER BY c.embedding <=> %s::vector LIMIT 50
                ),
                kw AS (
                    SELECT c.id, ts_rank(c.tsv, plainto_tsquery('english', %s)) AS kw_score,
                           ROW_NUMBER() OVER (ORDER BY ts_rank(c.tsv, plainto_tsquery('english', %s)) DESC) AS kw_rank
                    FROM chunks c
                    WHERE c.tsv @@ plainto_tsquery('english', %s)
                    ORDER BY kw_score DESC LIMIT 50
                )
                SELECT sem.text, sem.source, sem.title, sem.sim_score,
                       COALESCE(1.0/(60+sem.sem_rank), 0) + COALESCE(1.0/(60+kw.kw_rank), 0) AS rrf
                FROM sem LEFT JOIN kw ON sem.id = kw.id
                ORDER BY rrf DESC NULLS LAST
                LIMIT %s;
                """,
                (q_emb, q_emb, q_emb, query, query, query, k),
            )
        else:
            cur.execute(
                """
                SELECT c.text, d.source, d.title,
                       1 - (c.embedding <=> %s::vector) AS similarity, NULL
                FROM chunks c JOIN documents d ON c.document_id = d.id
                ORDER BY c.embedding <=> %s::vector LIMIT %s;
                """,
                (q_emb, q_emb, k),
            )
        rows = cur.fetchall()

    if not rows:
        console.print("[yellow]No matches[/]")
        return
    for text, src, title, sim, score in rows:
        score_str = f"{score:.3f}" if score is not None else f"{sim:.3f}"
        console.print(f"[bold cyan]{score_str}[/] [dim]{title}[/]  [dim italic]({src})[/]")
        snippet = text if len(text) <= 400 else text[:400] + "…"
        console.print(snippet + "\n")


@app.command()
def stats() -> None:
    """Show counts."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM documents")
        n_docs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM chunks")
        n_chunks = cur.fetchone()[0]
        cur.execute(
            "SELECT content_type, COUNT(*) FROM documents GROUP BY content_type ORDER BY 2 DESC"
        )
        by_type = cur.fetchall()
    console.print(f"[bold]Documents:[/] {n_docs}   [bold]Chunks:[/] {n_chunks}")
    if by_type:
        t = Table(title="By content_type")
        t.add_column("type")
        t.add_column("count", justify="right")
        for ct, c in by_type:
            t.add_row(str(ct), str(c))
        console.print(t)


@app.command()
def doctor(json_output: bool = typer.Option(False, "--json")) -> None:
    """Read-only schema/corpus invariants; reports problems without changing data."""
    from diagnostics import inspect_database
    result = database_retry(lambda: inspect_database(get_conn))
    if json_output:
        sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
    else:
        console.print(result)
    if not result["ok"]:
        raise typer.Exit(21)


@app.command("list")
def list_docs(limit: int = 20) -> None:
    """List recently ingested documents."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, content_type, ingested_at, source "
            "FROM documents ORDER BY ingested_at DESC LIMIT %s",
            (limit,),
        )
        rows = cur.fetchall()
    t = Table()
    for col in ("id", "title", "type", "ingested", "source"):
        t.add_column(col)
    for r in rows:
        t.add_row(*[str(x) for x in r])
    console.print(t)


@app.command()
def delete(doc_id: int) -> None:
    """Delete a document and its chunks."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
        conn.commit()
    console.print(f"[green]✓[/] deleted doc_id={doc_id}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        app()
    except Exception as exc:
        code, category = failure(exc)
        progress("failed", 0., error_category=category)
        message = str(exc) if isinstance(exc, (InputFailure, ConfigurationFailure)) else type(exc).__name__
        logging.getLogger("ingest").error("Ingestion failed category=%s detail=%s", category, message)
        raise SystemExit(code) from None


if __name__ == "__main__":
    main()
