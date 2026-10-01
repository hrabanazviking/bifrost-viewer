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
import os
import numpy as np
import time
from pathlib import Path

import httpx
import psycopg
import typer
from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from rich.console import Console
from rich.table import Table

load_dotenv(Path(os.getenv("INGEST_ENV_FILE", str(Path(__file__).parent / ".env"))))

DB_URL = os.environ["INGEST_DB_URL"]
OLLAMA_URL = os.environ["OLLAMA_URL"]
EMBED_MODEL = os.environ["INGEST_EMBED_MODEL"]
CHUNK_CHARS = int(os.environ.get("INGEST_CHUNK_CHARS", 2000))
CHUNK_OVERLAP = int(os.environ.get("INGEST_CHUNK_OVERLAP", 200))

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


def get_conn() -> psycopg.Connection:
    conn = psycopg.connect(DB_URL, connect_timeout=int(os.getenv("INGEST_DB_CONNECT_TIMEOUT", "5")))
    register_vector(conn)
    return conn


def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    batch_size = max(1, int(os.getenv("INGEST_EMBED_BATCH_SIZE", "32")))
    embeddings = []
    dimension = None
    with httpx.Client() as client:
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            for attempt in range(3):
                try:
                    response = client.post(f"{OLLAMA_URL}/api/embed", json={"model": EMBED_MODEL, "input": batch}, timeout=300)
                    response.raise_for_status()
                    vectors = np.asarray(response.json().get("embeddings"), dtype=np.float32)
                    if vectors.ndim != 2 or len(vectors) != len(batch) or not vectors.shape[1]:
                        raise ValueError("embedding response has an incomplete batch")
                    if not np.isfinite(vectors).all() or not np.all(np.any(vectors, axis=1)):
                        raise ValueError("embedding response contains invalid vectors")
                    if dimension is not None and vectors.shape[1] != dimension:
                        raise ValueError("embedding dimensions changed between batches")
                    dimension = vectors.shape[1]
                    embeddings.extend(vectors.tolist())
                    break
                except httpx.HTTPError as exc:
                    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code not in (408, 429) and exc.response.status_code < 500:
                        raise
                    if attempt == 2:
                        raise
                    time.sleep(2 ** attempt)
    return embeddings


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

        downloaded = trafilatura.fetch_url(src)
        if downloaded is None:
            raise RuntimeError(f"Could not fetch URL: {src}")
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
        if p.suffix.lower() == ".json":
            import json
            from unstructured.documents.elements import Text
            data = json.loads(p.read_text(encoding="utf-8"))
            elements = [Text(text=json.dumps(data, indent=2, ensure_ascii=False))]
        elif p.suffix.lower() == ".jsonl":
            import json
            from unstructured.documents.elements import Text
            elements = []
            for ln, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                elements.append(Text(text=_jsonl_record_to_text(rec)))
        else:
            from unstructured.partition.auto import partition
            elements = partition(filename=str(p))

    from unstructured.chunking.basic import chunk_elements
    chunks = chunk_elements(
        elements,
        max_characters=CHUNK_CHARS,
        new_after_n_chars=int(CHUNK_CHARS * 0.75),
        overlap=CHUNK_OVERLAP,
    )
    return title, content_type, [str(c) for c in chunks if str(c).strip()]


@app.command()
def add(source: str) -> None:
    """Ingest a file path or URL."""
    console.print(f"[bold cyan]Ingesting:[/] {source}")
    title, content_type, texts = parse_source(source)
    if not texts:
        console.print("[red]No content extracted[/]")
        raise typer.Exit(1)
    console.print(f"  parsed → {len(texts)} chunks")

    h = hashlib.sha256("\n".join(texts).encode("utf-8")).hexdigest()
    # Avoid holding database locks while the model computes a whole document.
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM documents WHERE hash = %s", (h,))
        existing = cur.fetchone()
        if existing:
            console.print(f"[yellow]Already ingested as doc_id={existing[0]} (hash match)[/]")
            return
    console.print(f"  embedding {len(texts)} chunks…")
    embeddings = embed(texts)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (source, title, content_type, hash) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (hash) DO NOTHING RETURNING id",
            (source, title, content_type, h),
        )
        inserted = cur.fetchone()
        if inserted is None:
            console.print("[yellow]Already ingested by another worker (hash match)[/]")
            return
        doc_id = inserted[0]
        cur.executemany(
            "INSERT INTO chunks (document_id, chunk_index, text, embedding) VALUES (%s, %s, %s, %s)",
            [(doc_id, i, text, embedding) for i, (text, embedding) in enumerate(zip(texts, embeddings, strict=True))],
        )
        conn.commit()
    console.print(f"[green]✓[/] doc_id={doc_id}  {len(texts)} chunks indexed")


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


if __name__ == "__main__":
    app()
