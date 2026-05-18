"""Background batch: extract entities + relations from every chunk with llama.

Resumable — skips chunks already in kg_extraction_progress.
Run with: uv run kg_extract.py [--limit N] [--workers W]
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx
import psycopg
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TimeRemainingColumn, TextColumn

PROJECT = Path(__file__).parent.resolve()
load_dotenv(PROJECT / ".env")

DB_URL = os.environ["VIEWER_DB_URL"]
OLLAMA_URL = os.environ["VIEWER_OLLAMA_URL"]
CHAT_MODEL = os.environ["VIEWER_CHAT_MODEL"]

console = Console()
app = typer.Typer(no_args_is_help=False, add_completion=False)


SYSTEM = (
    "You extract a small knowledge graph from a single text excerpt.\n"
    "Return STRICT JSON only, no preamble, no code fences. Schema:\n"
    '{"entities": [{"name": str, "kind": str}], '
    '"relations": [{"subject": str, "predicate": str, "object": str}]}\n'
    "Kinds: person, place, deity, artifact, concept, event, group, work, other.\n"
    "Predicates: short verbs/phrases (lowercase, snake_case if multi-word). "
    "Examples: wields, son_of, located_in, member_of, killed, created, ruled, "
    "associated_with, part_of. Use 0-8 entities and 0-8 relations per excerpt. "
    "Use Title Case names. Skip pronouns and generic phrases. Subject and object "
    "of every relation MUST appear in entities."
)


def schema_apply():
    with psycopg.connect(DB_URL) as conn, conn.cursor() as cur:
        cur.execute((PROJECT / "kg_schema.sql").read_text())
        conn.commit()


def normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def parse_response(raw: str) -> dict | None:
    # llama sometimes adds prose; grab the first {...} block
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(d, dict):
        return None
    d.setdefault("entities", [])
    d.setdefault("relations", [])
    if not isinstance(d["entities"], list) or not isinstance(d["relations"], list):
        return None
    return d


def call_llm(client: httpx.Client, text: str) -> dict | None:
    body = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Excerpt:\n\n" + text[:3500] + "\n\nJSON:"},
        ],
        "stream": False,
        "format": "json",
        "options": {"num_predict": 700, "temperature": 0.1},
    }
    r = client.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=300)
    r.raise_for_status()
    content = r.json()["message"]["content"]
    return parse_response(content)


def upsert_entity(cur: psycopg.Cursor, name: str, kind: str | None) -> int | None:
    name = name.strip()
    if not name or len(name) > 200:
        return None
    n_norm = normalize(name)
    k = (kind or "other").strip().lower()[:32] or "other"
    cur.execute(
        """
        INSERT INTO kg_entities (name, name_norm, kind, mentions)
        VALUES (%s, %s, %s, 1)
        ON CONFLICT (name_norm, kind)
        DO UPDATE SET mentions = kg_entities.mentions + 1
        RETURNING id
        """,
        (name, n_norm, k),
    )
    return cur.fetchone()[0]


def persist(chunk_id: int, parsed: dict | None, error: str | None):
    with psycopg.connect(DB_URL) as conn, conn.cursor() as cur:
        if error or parsed is None:
            cur.execute(
                "INSERT INTO kg_extraction_progress (chunk_id, status, error) VALUES (%s, 'failed', %s) "
                "ON CONFLICT (chunk_id) DO UPDATE SET status=EXCLUDED.status, error=EXCLUDED.error, processed_at=now()",
                (chunk_id, error or "parse_failed"),
            )
            conn.commit()
            return
        ent_ids: dict[str, int] = {}
        for e in parsed["entities"][:12]:
            if not isinstance(e, dict):
                continue
            name = e.get("name", "")
            kind = e.get("kind", "other")
            if not isinstance(name, str) or not isinstance(kind, str):
                continue
            eid = upsert_entity(cur, name, kind)
            if eid is not None:
                ent_ids[normalize(name)] = eid
        for rel in parsed["relations"][:12]:
            if not isinstance(rel, dict):
                continue
            s = rel.get("subject", ""); p = rel.get("predicate", ""); o = rel.get("object", "")
            if not (isinstance(s, str) and isinstance(p, str) and isinstance(o, str)):
                continue
            sid = ent_ids.get(normalize(s))
            oid = ent_ids.get(normalize(o))
            if sid is None or oid is None or sid == oid:
                continue
            pred = re.sub(r"\s+", "_", p.strip().lower())[:48]
            if not pred:
                continue
            cur.execute(
                "INSERT INTO kg_relations (subject_id, predicate, object_id, chunk_id) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (sid, pred, oid, chunk_id),
            )
        cur.execute(
            "INSERT INTO kg_extraction_progress (chunk_id, status) VALUES (%s, 'done') "
            "ON CONFLICT (chunk_id) DO UPDATE SET status='done', error=NULL, processed_at=now()",
            (chunk_id,),
        )
        conn.commit()


def pending_chunks(limit: int | None) -> list[tuple[int, str]]:
    q = (
        "SELECT c.id, c.text FROM chunks c "
        "LEFT JOIN kg_extraction_progress p ON p.chunk_id = c.id "
        "WHERE p.chunk_id IS NULL "
        "ORDER BY c.id"
    )
    if limit:
        q += f" LIMIT {int(limit)}"
    with psycopg.connect(DB_URL) as conn, conn.cursor() as cur:
        cur.execute(q)
        return cur.fetchall()


def worker(chunk_id: int, text: str) -> tuple[int, str | None]:
    try:
        with httpx.Client(http2=False) as client:
            parsed = call_llm(client, text)
        persist(chunk_id, parsed, None if parsed else "parse_failed")
        return chunk_id, None
    except Exception as e:
        try:
            persist(chunk_id, None, str(e)[:500])
        except Exception:
            pass
        return chunk_id, str(e)[:200]


@app.command()
def run(
    limit: int | None = typer.Option(None, help="Process at most N chunks"),
    workers: int = typer.Option(2, help="Concurrent ollama requests (keep low for a 6GB GPU)"),
):
    schema_apply()
    todo = pending_chunks(limit)
    if not todo:
        console.print("[green]nothing to do — all chunks processed[/]")
        return
    console.print(f"[bold]chunks pending:[/] {len(todo)}  [dim](workers={workers}, model={CHAT_MODEL})[/]")
    t0 = time.time()
    ok = fail = 0
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        BarColumn(), TextColumn("{task.completed}/{task.total}"),
        TimeRemainingColumn(),
    ) as prog:
        task = prog.add_task("extracting", total=len(todo))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(worker, cid, txt) for cid, txt in todo]
            for fut in as_completed(futures):
                cid, err = fut.result()
                if err:
                    fail += 1
                else:
                    ok += 1
                prog.update(task, advance=1, description=f"extracting (ok {ok} fail {fail})")
    dt = time.time() - t0
    console.print(f"[green]done[/] in {dt/60:.1f} min · ok {ok} · fail {fail}")


@app.command()
def stats():
    schema_apply()
    with psycopg.connect(DB_URL) as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM chunks"); total = cur.fetchone()[0]
        cur.execute("SELECT status, COUNT(*) FROM kg_extraction_progress GROUP BY status")
        by_status = dict(cur.fetchall())
        cur.execute("SELECT COUNT(*) FROM kg_entities"); n_e = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM kg_relations"); n_r = cur.fetchone()[0]
        cur.execute(
            "SELECT kind, COUNT(*) FROM kg_entities GROUP BY kind ORDER BY 2 DESC LIMIT 12"
        )
        kinds = cur.fetchall()
        cur.execute(
            "SELECT predicate, COUNT(*) FROM kg_relations GROUP BY predicate ORDER BY 2 DESC LIMIT 12"
        )
        preds = cur.fetchall()
    done = by_status.get("done", 0); failed = by_status.get("failed", 0)
    console.print(f"[bold]chunks[/] {total}  [bold]done[/] {done}  [bold]failed[/] {failed}  "
                  f"[dim]({100*done/max(1,total):.1f}%)[/]")
    console.print(f"[bold]entities[/] {n_e}  [bold]relations[/] {n_r}")
    if kinds:
        console.print("[bold]top kinds:[/] " + "  ".join(f"{k}:{c}" for k, c in kinds))
    if preds:
        console.print("[bold]top predicates:[/] " + "  ".join(f"{p}:{c}" for p, c in preds))


if __name__ == "__main__":
    app()
