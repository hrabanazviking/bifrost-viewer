"""Bifröst — 3D graph viewer + knowledge layer over the knowledge DB.

A Mythic Engineering creation. See SYSTEM_VISION.md, ARCHITECTURE.md, and
PROJECT_LAWS.md in the project root for the soul, bones, and immutable rules.

Endpoints
---------
GET  /                              static page (3d-force-graph UI)
GET  /api/health                    liveness + DB/ollama/cache check
GET  /api/graph?level=chunk|doc     cached graph layer for chunks or docs
GET  /api/graph/build-status        progress of the async graph build
POST /api/graph/build               kick off (or rebuild) the graph cache in background
GET  /api/chunk/{id}                full chunk text
GET  /api/cluster-names             LLM-named HDBSCAN clusters (cached)
GET  /api/search?q=…&hyde=0         hybrid search; hyde=1 swaps query for hypothetical answer
GET  /api/path?a=ID&b=ID            shortest-path through the similarity graph (Dijkstra)
GET  /api/skein/status              Skein KG build state + counts
POST /api/skein/build               kick off Skein build in background
GET  /api/skein/graph               entity graph (UMAP-projected) for 3D rendering
GET  /api/skry?q=…                  query-time entity neighborhood
GET  /api/kg/status                 legacy llama-per-chunk batch progress (kept for comparison)
POST /api/refresh                   invalidate caches; equivalent to POST /api/graph/build

All API endpoints require a token via ?token=… or Authorization: Bearer …

Robustness vows (per PROJECT_LAWS.md)
-------------------------------------
* Fault tolerance: every endpoint is wrapped in try/except; failures log
  warnings and return structured errors rather than crashing the server.
* Logging: structured logging via the `logging` module, never bare print().
* DB pooling: shared psycopg_pool.ConnectionPool, opened once at startup.
* Async build: heavy graph rebuilds run in a thread with a status endpoint;
  the loading screen never blocks indefinitely.
* Graceful degradation: ollama-dependent features (HyDE, cluster-naming) fail
  loudly but do not bring down search or graph rendering.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import secrets
import threading
import time
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

import httpx
import numpy as np
import orjson
import psycopg
import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

# ─── config ─────────────────────────────────────────────────────────────────

PROJECT = Path(__file__).parent.resolve()
load_dotenv(PROJECT / ".env")

DB_URL = os.environ["VIEWER_DB_URL"]
BIND_HOST = os.environ.get("VIEWER_BIND_HOST", "127.0.0.1")
PORT = int(os.environ.get("VIEWER_PORT", "8731"))
TOKEN = os.environ["VIEWER_TOKEN"]
EDGE_TOP_K = int(os.environ.get("VIEWER_EDGE_TOP_K", "4"))
EDGE_MIN_SIM = float(os.environ.get("VIEWER_EDGE_MIN_SIM", "0.55"))
HDBSCAN_MIN_CLUSTER = int(os.environ.get("VIEWER_HDBSCAN_MIN_CLUSTER", "8"))
EDGE_LABEL_TERMS = int(os.environ.get("VIEWER_EDGE_LABEL_TERMS", "4"))
OLLAMA_URL = os.environ["VIEWER_OLLAMA_URL"]
EMBED_MODEL = os.environ["VIEWER_EMBED_MODEL"]
CHAT_MODEL = os.environ["VIEWER_CHAT_MODEL"]

CACHE_DIR = PROJECT / ".cache"
CACHE_DIR.mkdir(exist_ok=True)
LOG_DIR = PROJECT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ─── logging ────────────────────────────────────────────────────────────────

_log_fmt = "%(asctime)s [%(levelname).1s] %(name)s: %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=_log_fmt,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "bifrost.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("bifrost")

# ─── DB pool (opened lazily so import does not require the DB) ──────────────

_pool: Optional[ConnectionPool] = None


def _configure_conn(conn: psycopg.Connection) -> None:
    register_vector(conn)


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            DB_URL, min_size=1, max_size=8, timeout=30,
            kwargs={"autocommit": False}, configure=_configure_conn, open=True,
        )
        log.info("opened DB connection pool")
    return _pool


def db_conn():
    """Use as: `with db_conn() as conn:` — returns pool-managed connection."""
    return get_pool().connection()


# ─── app + auth ─────────────────────────────────────────────────────────────

app = FastAPI(title="Bifröst", docs_url=None, redoc_url=None)


def orj(payload: Any, status_code: int = 200) -> Response:
    """orjson-serialized Response. Faster than FastAPI's default JSONResponse,
    and handles numpy types out of the box (option NUMPY_SERIALIZE_NUMPY)."""
    body = orjson.dumps(payload, option=orjson.OPT_SERIALIZE_NUMPY)
    return Response(content=body, status_code=status_code, media_type="application/json")


def require_token(request: Request, token: str | None = Query(default=None)):
    supplied = token
    if not supplied:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            supplied = auth[7:].strip()
    if not supplied or not secrets.compare_digest(supplied, TOKEN):
        raise HTTPException(status_code=401, detail="bad or missing token")


def safely(name: str):
    """Decorator: wrap an endpoint with try/except → 500 + structured log."""
    def wrap(fn):
        from functools import wraps

        @wraps(fn)
        def inner(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                log.warning("endpoint %s failed: %s\n%s", name, e, traceback.format_exc())
                return orj({"error": str(e), "endpoint": name}, status_code=500)
        return inner
    return wrap


# ─── graph build ────────────────────────────────────────────────────────────

_STOPWORDS = set("""
a an and are as at be by for from has have he her his i in is it its of on or that
the their them they this to was were will with you your we our us not no but if
""".split())


def chunk_top_terms(texts: list[str], top_n: int = 12) -> list[set[str]]:
    """Per-chunk top tf-idf terms (for cheap edge-label intersection)."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    vec = TfidfVectorizer(
        max_features=4000, stop_words="english", lowercase=True,
        token_pattern=r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-']{2,}",
    )
    mat = vec.fit_transform(texts)
    vocab = np.array(vec.get_feature_names_out())
    out: list[set[str]] = []
    for i in range(mat.shape[0]):
        row = mat.getrow(i)
        if row.nnz == 0:
            out.append(set())
            continue
        idx = row.indices
        data = row.data
        order = np.argsort(-data)[:top_n]
        out.append({w for w in vocab[idx[order]] if w not in _STOPWORDS})
    return out


def doc_palette(doc_ids: list[int]) -> dict[int, str]:
    uniq = sorted(set(doc_ids))
    return {d: f"hsl({int(360 * i / max(1, len(uniq)))}, 80%, 60%)" for i, d in enumerate(uniq)}


def cluster_palette(cluster_ids: list[int]) -> dict[int, str]:
    uniq = sorted({c for c in cluster_ids if c >= 0})
    pal = {c: f"hsl({int(360 * i / max(1, len(uniq)))}, 70%, 55%)" for i, c in enumerate(uniq)}
    pal[-1] = "#5a5f7a"
    return pal


def fingerprint() -> str:
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*), COALESCE(MAX(id), 0) FROM chunks")
        n, max_id = cur.fetchone()
    return f"v2_{n}_{max_id}"


def cache_path(fp: str) -> Path:
    return CACHE_DIR / f"graph_{fp}.json"


def build_graph(fp: str, progress=None) -> dict:
    """Compute chunk-level + doc-level graphs in one pass. `progress` is
    called with a (stage_name, fraction) tuple at each major checkpoint."""
    import umap
    import hdbscan

    def step(name, frac):
        if progress:
            try:
                progress(name, frac)
            except Exception:
                pass
        log.info("graph build · %s (%.0f%%)", name, frac * 100)

    step("loading chunks from db", 0.02)
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.id, c.document_id, c.chunk_index, c.text, c.embedding,
                   d.title, d.content_type, d.source
            FROM chunks c JOIN documents d ON c.document_id = d.id
            ORDER BY c.id
            """
        )
        rows = cur.fetchall()

    if not rows:
        empty = {"fingerprint": fp, "nodes": [], "links": [], "documents": [],
                 "clusters": [], "stats": {"n_chunks": 0, "n_docs": 0, "n_edges": 0,
                 "n_clusters": 0, "edge_top_k": EDGE_TOP_K, "edge_min_sim": EDGE_MIN_SIM}}
        return {"chunk": empty, "document": empty}

    ids = [r[0] for r in rows]
    doc_ids = [r[1] for r in rows]
    texts = [r[3] for r in rows]
    embeddings = np.array([r[4] for r in rows], dtype=np.float32)

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    unit = embeddings / norms
    n = len(rows)

    step(f"UMAP projection ({n} chunks)", 0.08)
    n_neighbors = max(2, min(15, n - 1))
    reducer = umap.UMAP(n_components=3, n_neighbors=n_neighbors, metric="cosine",
                       min_dist=0.1, random_state=42)
    coords = reducer.fit_transform(embeddings)
    coords = coords - coords.mean(axis=0)
    scale = 200.0 / max(1e-6, np.abs(coords).max())
    coords = coords * scale

    step("HDBSCAN clustering", 0.55)
    cluster_ids = np.full(n, -1, dtype=int)
    if n >= max(HDBSCAN_MIN_CLUSTER * 2, 10):
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=HDBSCAN_MIN_CLUSTER,
            min_samples=max(2, HDBSCAN_MIN_CLUSTER // 4),
            metric="euclidean", cluster_selection_method="eom",
        )
        try:
            cluster_ids = clusterer.fit_predict(unit)
        except Exception as e:
            log.warning("HDBSCAN failed: %s — proceeding without clusters", e)

    step("computing edge labels (tf-idf)", 0.72)
    try:
        term_sets = chunk_top_terms(texts, top_n=12)
    except Exception as e:
        log.warning("tf-idf failed: %s — edges will have no shared-term labels", e)
        term_sets = [set() for _ in texts]

    step("computing top-K edges", 0.82)
    sim = unit @ unit.T
    np.fill_diagonal(sim, -1.0)
    links: list[dict] = []
    seen: set[tuple[int, int]] = set()
    k = min(EDGE_TOP_K, n - 1) if n > 1 else 0
    if k > 0:
        top_idx = np.argpartition(-sim, kth=k - 1, axis=1)[:, :k]
        for i in range(n):
            for j in top_idx[i]:
                j = int(j)
                s = float(sim[i, j])
                if s < EDGE_MIN_SIM or i == j:
                    continue
                a, b = (i, j) if i < j else (j, i)
                if (a, b) in seen:
                    continue
                seen.add((a, b))
                shared = sorted(term_sets[a] & term_sets[b])[:EDGE_LABEL_TERMS] if term_sets[a] and term_sets[b] else []
                links.append({"source": ids[a], "target": ids[b], "sim": round(s, 3),
                              "shared": shared})

    doc_color = doc_palette(doc_ids)
    cl_color = cluster_palette(cluster_ids.tolist())
    doc_meta = {r[1]: (r[5], r[6], r[7]) for r in rows}

    step("assembling payloads", 0.92)
    chunk_nodes = []
    for i, r in enumerate(rows):
        cid, did, cidx, text, _emb, title, ctype, source = r
        snippet = text if len(text) <= 200 else text[:200] + "…"
        cl = int(cluster_ids[i])
        chunk_nodes.append({
            "id": cid, "doc_id": did, "doc_title": title, "content_type": ctype,
            "chunk_index": cidx, "snippet": snippet, "cluster": cl,
            "color_doc": doc_color[did], "color_cluster": cl_color[cl],
            "x": float(coords[i, 0]), "y": float(coords[i, 1]), "z": float(coords[i, 2]),
        })

    documents_meta = [
        {"id": d, "title": doc_meta[d][0], "content_type": doc_meta[d][1],
         "source": doc_meta[d][2], "color": doc_color[d]}
        for d in sorted(set(doc_ids))
    ]

    clusters_meta: list[dict] = []
    for cl in sorted(set(cluster_ids.tolist())):
        if cl < 0:
            continue
        mask = cluster_ids == cl
        centroid = coords[mask].mean(axis=0)
        sample = [int(ids[i]) for i in np.where(mask)[0][:8]]
        clusters_meta.append({
            "id": int(cl), "size": int(mask.sum()), "color": cl_color[cl],
            "centroid": [float(centroid[0]), float(centroid[1]), float(centroid[2])],
            "sample_chunk_ids": sample,
        })

    chunk_payload = {
        "fingerprint": fp, "nodes": chunk_nodes, "links": links,
        "documents": documents_meta, "clusters": clusters_meta,
        "stats": {"n_chunks": n, "n_docs": len(documents_meta),
                  "n_edges": len(links), "n_clusters": len(clusters_meta),
                  "edge_top_k": EDGE_TOP_K, "edge_min_sim": EDGE_MIN_SIM},
    }

    # Document-level aggregation
    doc_to_idx: dict[int, list[int]] = defaultdict(list)
    for i, d in enumerate(doc_ids):
        doc_to_idx[d].append(i)

    doc_nodes = []
    for d in sorted(doc_to_idx):
        idxs = doc_to_idx[d]
        c = coords[idxs].mean(axis=0)
        title, ctype, source = doc_meta[d]
        doc_nodes.append({
            "id": d, "doc_id": d, "doc_title": title, "content_type": ctype,
            "snippet": f"{len(idxs)} chunks · {ctype}",
            "color_doc": doc_color[d], "color_cluster": doc_color[d],
            "size_chunks": len(idxs),
            "x": float(c[0]), "y": float(c[1]), "z": float(c[2]),
        })

    unique_docs = sorted(doc_to_idx)
    doc_unit_centroids = {d: unit[doc_to_idx[d]].mean(axis=0) for d in unique_docs}
    for d, v in doc_unit_centroids.items():
        nv = np.linalg.norm(v)
        if nv > 0:
            doc_unit_centroids[d] = v / nv

    doc_links: list[dict] = []
    for i, d1 in enumerate(unique_docs):
        for d2 in unique_docs[i + 1:]:
            s = float(doc_unit_centroids[d1] @ doc_unit_centroids[d2])
            if s >= EDGE_MIN_SIM:
                doc_links.append({"source": d1, "target": d2, "sim": round(s, 3), "shared": []})

    doc_payload = {
        "fingerprint": fp, "nodes": doc_nodes, "links": doc_links,
        "documents": documents_meta, "clusters": [],
        "stats": {"n_chunks": n, "n_docs": len(documents_meta),
                  "n_edges": len(doc_links), "n_clusters": 0,
                  "edge_top_k": "all-pairs", "edge_min_sim": EDGE_MIN_SIM},
    }

    step("done", 1.0)
    return {"chunk": chunk_payload, "document": doc_payload}


# ─── async graph build (out-of-process so it cannot GIL-block the server) ───

# The state machine now lives in a JSON file under .cache/, written by the
# graph_builder.py subprocess and read by /api/graph/build-status.

_build_proc_lock = threading.Lock()
_build_proc: dict = {"proc": None, "fp": None, "started_at": None, "log_path": None}


def _build_status_path(fp: str) -> Path:
    return CACHE_DIR / f"build_status_{fp}.json"


def _read_build_status(fp: str) -> dict:
    p = _build_status_path(fp)
    if not p.exists():
        return {"running": False, "stage": "idle", "progress": 0.0,
                "started_at": None, "finished_at": None, "error": None,
                "fingerprint": fp}
    try:
        return orjson.loads(p.read_bytes())
    except Exception as e:
        return {"running": False, "stage": "status-unreadable", "progress": 0.0,
                "error": str(e), "fingerprint": fp}


def kick_off_build(force: bool = False) -> bool:
    """Spawn graph_builder.py for the current fingerprint, returning True if a
    new build was started (False if the cache is already valid or a build is
    already running)."""
    import subprocess
    try:
        fp = fingerprint()
    except Exception as e:
        log.warning("cannot compute fingerprint: %s", e)
        return False
    target = cache_path(fp)
    if not force and target.exists():
        # Already cached — mark status as done so polling clients see "ready".
        _build_status_path(fp).write_bytes(orjson.dumps({
            "running": False, "stage": "cached", "progress": 1.0,
            "fingerprint": fp, "started_at": None,
            "finished_at": datetime.datetime.now().isoformat(),
            "error": None,
        }))
        return False
    with _build_proc_lock:
        p = _build_proc["proc"]
        if p is not None and p.poll() is None:
            return False  # already running
        # Prune old per-fingerprint status files
        for old in CACHE_DIR.glob("build_status_v*.json"):
            if old != _build_status_path(fp):
                try:
                    old.unlink()
                except OSError:
                    pass
        log_path = LOG_DIR / f"graph_build_{int(time.time())}.log"
        log_file = open(log_path, "w")
        proc = subprocess.Popen(
            ["uv", "run", str(PROJECT / "graph_builder.py"), fp],
            cwd=str(PROJECT),
            stdout=log_file, stderr=subprocess.STDOUT,
        )
        _build_proc.update({
            "proc": proc, "fp": fp,
            "started_at": datetime.datetime.now().isoformat(),
            "log_path": str(log_path),
        })
        log.info("spawned graph_builder pid=%s fp=%s log=%s", proc.pid, fp, log_path.name)
        return True


def load_cached_graph() -> dict | None:
    """Return cached graph for the current fingerprint, or None if no cache."""
    try:
        fp = fingerprint()
    except Exception as e:
        log.warning("could not compute fingerprint: %s", e)
        return None
    path = cache_path(fp)
    if not path.exists():
        return None
    try:
        return orjson.loads(path.read_bytes())
    except Exception as e:
        log.warning("cache file %s unreadable: %s", path.name, e)
        return None


# ─── ollama helpers ─────────────────────────────────────────────────────────

def ollama_embed(texts: list[str]) -> list[list[float]]:
    r = httpx.post(f"{OLLAMA_URL}/api/embed",
                   json={"model": EMBED_MODEL, "input": texts}, timeout=300)
    r.raise_for_status()
    return r.json()["embeddings"]


def ollama_chat(prompt: str, *, system: str | None = None, max_tokens: int = 256) -> str:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    r = httpx.post(f"{OLLAMA_URL}/api/chat", json={
        "model": CHAT_MODEL, "messages": msgs, "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.2},
    }, timeout=120)
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def ollama_alive() -> bool:
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def db_alive() -> bool:
    try:
        with db_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            return cur.fetchone()[0] == 1
    except Exception:
        return False


# ─── routes ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
@safely("health")
def health(_=Depends(require_token)):
    db_ok = db_alive()
    ollama_ok = ollama_alive()
    cache_exists = False
    try:
        fp = fingerprint() if db_ok else None
        cache_exists = bool(fp) and cache_path(fp).exists()
    except Exception:
        fp = None
    build_st = _read_build_status(fp) if fp else {"stage": "unknown"}
    return orj({
        "ok": db_ok,
        "db": db_ok, "ollama": ollama_ok,
        "chunk_graph_cached": cache_exists,
        "fingerprint": fp,
        "build_state": build_st,
    })


@app.get("/api/graph")
@safely("graph")
def get_graph(level: str = "chunk", _=Depends(require_token)):
    if level not in ("chunk", "document"):
        raise HTTPException(status_code=400, detail="level must be chunk or document")
    g = load_cached_graph()
    if g is None:
        # Kick off background build if not already running; client should poll
        kick_off_build(force=False)
        return orj({
            "pending": True,
            "build_state": _read_build_status(fingerprint()),
            "message": "graph cache absent or stale; build started in background — poll /api/graph/build-status",
        }, status_code=202)
    return orj(g[level])


@app.get("/api/graph/build-status")
@safely("graph_build_status")
def graph_build_status(_=Depends(require_token)):
    try:
        fp = fingerprint()
    except Exception as e:
        return orj({"running": False, "stage": "no-db", "error": str(e),
                    "cache_exists": False, "current_fingerprint": None})
    st = _read_build_status(fp)
    st["current_fingerprint"] = fp
    st["cache_exists"] = cache_path(fp).exists()
    # If the subprocess died without writing 'finished_at', mark failed.
    with _build_proc_lock:
        p = _build_proc["proc"]
        if (p is not None and p.poll() is not None
                and st.get("running") and _build_proc["fp"] == fp):
            st["running"] = False
            st["stage"] = "failed"
            st["error"] = st.get("error") or f"builder exited with code {p.returncode}"
    return orj(st)


@app.post("/api/graph/build")
@safely("graph_build")
def graph_build(force: bool = True, _=Depends(require_token)):
    started = kick_off_build(force=force)
    return orj({"ok": True, "started": started,
                "build_state": _read_build_status(fingerprint())})


@app.post("/api/refresh")
@safely("refresh")
def refresh(_=Depends(require_token)):
    started = kick_off_build(force=True)
    # Invalidate cluster names too
    for old in CACHE_DIR.glob("clusternames_*.json"):
        try:
            old.unlink()
        except OSError as e:
            log.warning("could not remove %s: %s", old.name, e)
    return orj({"ok": True, "started": started})


@app.get("/api/chunk/{chunk_id}")
@safely("chunk")
def get_chunk(chunk_id: int, _=Depends(require_token)):
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT c.id, c.text, c.chunk_index, d.id, d.title, d.source, d.content_type "
            "FROM chunks c JOIN documents d ON c.document_id = d.id WHERE c.id = %s",
            (chunk_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="chunk not found")
    return orj({"id": row[0], "text": row[1], "chunk_index": row[2],
                "doc_id": row[3], "doc_title": row[4], "source": row[5], "content_type": row[6]})


@app.get("/api/cluster-names")
@safely("cluster_names")
def cluster_names(_=Depends(require_token)):
    g = load_cached_graph()
    if g is None:
        raise HTTPException(status_code=409, detail="chunk graph not cached yet; build it first")
    g = g["chunk"]
    fp = g["fingerprint"]
    names_path = CACHE_DIR / f"clusternames_{fp}.json"
    if names_path.exists():
        try:
            return orj(orjson.loads(names_path.read_bytes()))
        except Exception as e:
            log.warning("cluster-names cache unreadable: %s", e)

    clusters = g.get("clusters", [])
    if not clusters:
        out = {"fingerprint": fp, "names": {}}
        names_path.write_bytes(orjson.dumps(out))
        return orj(out)

    all_ids = [cid for cl in clusters for cid in cl["sample_chunk_ids"]]
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, text FROM chunks WHERE id = ANY(%s)", (all_ids,))
        text_by_id = {r[0]: r[1] for r in cur.fetchall()}

    sys_p = ("You name clusters of related text excerpts. Output ONLY a short label, 2-5 words, "
             "title-case, no quotes, no punctuation, no preamble.")
    names: dict[str, str] = {}
    for cl in clusters:
        samples = [text_by_id.get(cid, "")[:500] for cid in cl["sample_chunk_ids"]]
        prompt = "Excerpts from one cluster:\n\n" + "\n\n---\n\n".join(samples) + "\n\nLabel:"
        try:
            label = ollama_chat(prompt, system=sys_p, max_tokens=24)
        except Exception as e:
            log.warning("cluster name for cluster %s failed: %s", cl["id"], e)
            label = f"Cluster {cl['id']}"
        label = label.split("\n")[0].strip().strip('"').strip(".")[:48] or f"Cluster {cl['id']}"
        names[str(cl["id"])] = label

    out = {"fingerprint": fp, "names": names}
    names_path.write_bytes(orjson.dumps(out))
    return orj(out)


@app.get("/api/search")
@safely("search")
def search(q: str, k: int = 12, hyde: int = 0, _=Depends(require_token)):
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="empty query")
    if k < 1 or k > 100:
        raise HTTPException(status_code=400, detail="k must be in [1, 100]")
    query_text = q
    hyde_doc = None
    if hyde:
        try:
            hyde_doc = ollama_chat(
                f"Write a short, factual passage (3-5 sentences) that would answer the question:\n\n{q}",
                system="You are a knowledgeable assistant. Write only the passage, no preamble.",
                max_tokens=180,
            )
            query_text = hyde_doc
        except Exception as e:
            log.warning("HyDE generation failed (falling back to raw query): %s", e)
            hyde_doc = None
    try:
        emb = ollama_embed([query_text])[0]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ollama embed failed: {e}")
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            WITH sem AS (
                SELECT c.id, 1 - (c.embedding <=> %s::vector) AS sim,
                       ROW_NUMBER() OVER (ORDER BY c.embedding <=> %s::vector) AS sem_rank
                FROM chunks c ORDER BY c.embedding <=> %s::vector LIMIT 60
            ),
            kw AS (
                SELECT c.id, ts_rank(c.tsv, plainto_tsquery('english', %s)) AS kw,
                       ROW_NUMBER() OVER (ORDER BY ts_rank(c.tsv, plainto_tsquery('english', %s)) DESC) AS kw_rank
                FROM chunks c WHERE c.tsv @@ plainto_tsquery('english', %s) LIMIT 60
            )
            SELECT sem.id, sem.sim,
                   COALESCE(1.0/(60+sem.sem_rank), 0) + COALESCE(1.0/(60+kw.kw_rank), 0) AS rrf
            FROM sem LEFT JOIN kw ON sem.id = kw.id
            ORDER BY rrf DESC NULLS LAST LIMIT %s
            """,
            (emb, emb, emb, q, q, q, k),
        )
        hits = [{"id": r[0], "sim": float(r[1]), "score": float(r[2])} for r in cur.fetchall()]
    return orj({"query": q, "hyde_used": bool(hyde), "hyde_doc": hyde_doc, "hits": hits})


@app.get("/api/path")
@safely("path")
def path(a: int, b: int, _=Depends(require_token)):
    import networkx as nx
    g = load_cached_graph()
    if g is None:
        raise HTTPException(status_code=409, detail="chunk graph not cached yet")
    G = nx.Graph()
    for link in g["chunk"]["links"]:
        w = max(1e-3, 1.0 - link["sim"])
        G.add_edge(link["source"], link["target"], weight=w, sim=link["sim"])
    if a not in G or b not in G:
        raise HTTPException(status_code=404, detail="one or both nodes not in similarity graph")
    try:
        nodes = nx.shortest_path(G, a, b, weight="weight")
    except nx.NetworkXNoPath:
        return orj({"a": a, "b": b, "found": False, "nodes": [], "edges": []})
    edges = [{"source": nodes[i], "target": nodes[i + 1],
              "sim": G[nodes[i]][nodes[i + 1]]["sim"]} for i in range(len(nodes) - 1)]
    return orj({"a": a, "b": b, "found": True, "nodes": nodes, "edges": edges})


# ─── Skein + Skry ───────────────────────────────────────────────────────────

SKEIN_DIR = PROJECT.parent / "skein-kg"
_skein_build_proc = {"proc": None, "started_at": None, "log_path": None}


def _skein_tables_exist(cur) -> bool:
    cur.execute(
        "SELECT EXISTS (SELECT FROM information_schema.tables "
        "WHERE table_name = 'skein_entities')"
    )
    return cur.fetchone()[0]


@app.get("/api/skein/status")
@safely("skein_status")
def skein_status(_=Depends(require_token)):
    p = _skein_build_proc["proc"]
    running = p is not None and p.poll() is None
    with db_conn() as conn, conn.cursor() as cur:
        if not _skein_tables_exist(cur):
            return orj({"built": False, "running": running, "n_entities": 0, "n_relations": 0})
        cur.execute("SELECT COUNT(*) FROM skein_entities"); ne = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM skein_relations"); nr = cur.fetchone()[0]
        cur.execute("SELECT fingerprint, finished_at, stats FROM skein_build ORDER BY id DESC LIMIT 1")
        last = cur.fetchone()
    return orj({
        "built": ne > 0, "running": running,
        "n_entities": ne, "n_relations": nr,
        "last_build": ({"fingerprint": last[0], "finished_at": last[1].isoformat(),
                        "stats": last[2]} if last else None),
    })


@app.post("/api/skein/build")
@safely("skein_build")
def skein_build(_=Depends(require_token)):
    import subprocess
    p = _skein_build_proc["proc"]
    if p is not None and p.poll() is None:
        return orj({"ok": False, "reason": "already running",
                    "started_at": _skein_build_proc["started_at"]})
    log_path = LOG_DIR / f"skein_build_{int(time.time())}.log"
    log_file = open(log_path, "w")
    new = subprocess.Popen(
        ["uv", "run", "skein", "build"],
        cwd=str(SKEIN_DIR),
        stdout=log_file, stderr=subprocess.STDOUT,
    )
    _skein_build_proc.update({
        "proc": new, "started_at": datetime.datetime.now().isoformat(),
        "log_path": str(log_path),
    })
    for old in CACHE_DIR.glob("skein_graph_*.json"):
        try:
            old.unlink()
        except OSError:
            pass
    log.info("started skein build pid=%s log=%s", new.pid, log_path)
    return orj({"ok": True, "pid": new.pid, "log": str(log_path)})


def _skein_fingerprint(cur) -> str | None:
    cur.execute("SELECT fingerprint FROM skein_build ORDER BY id DESC LIMIT 1")
    r = cur.fetchone()
    return r[0] if r else None


def _build_skein_graph(fp: str) -> dict:
    import umap
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name, kind, mentions, embedding FROM skein_entities ORDER BY id")
        ents = cur.fetchall()
        cur.execute("SELECT subject_id, object_id, predicate, sim, evidence_chunk_ids FROM skein_relations")
        rels = cur.fetchall()
    if not ents:
        return {"fingerprint": fp, "nodes": [], "links": [], "kinds": []}

    embs = np.array([e[4] for e in ents], dtype=np.float32)
    n = len(ents)
    n_neighbors = max(2, min(15, n - 1))
    if n > 4:
        reducer = umap.UMAP(n_components=3, n_neighbors=n_neighbors, metric="cosine",
                           min_dist=0.15, random_state=42)
        coords = reducer.fit_transform(embs)
        coords = coords - coords.mean(axis=0)
        scale = 180.0 / max(1e-6, np.abs(coords).max())
        coords = coords * scale
    else:
        coords = np.zeros((n, 3), dtype=np.float32)

    kinds_sorted = sorted({e[2] or "other" for e in ents})
    kind_color = {k: f"hsl({int(360 * i / max(1, len(kinds_sorted)))}, 75%, 60%)"
                  for i, k in enumerate(kinds_sorted)}

    nodes = [{
        "id": eid, "name": name, "kind": kind or "other", "mentions": int(mentions),
        "color": kind_color.get(kind or "other", "#888"),
        "x": float(coords[i, 0]), "y": float(coords[i, 1]), "z": float(coords[i, 2]),
    } for i, (eid, name, kind, mentions, _emb) in enumerate(ents)]

    links = [{"source": s, "target": o, "predicate": p, "sim": float(sim),
              "evidence": list(ev or [])[:5]} for s, o, p, sim, ev in rels]
    return {
        "fingerprint": fp, "nodes": nodes, "links": links,
        "kinds": [{"kind": k, "color": kind_color[k]} for k in kinds_sorted],
        "stats": {"n_entities": len(nodes), "n_relations": len(links),
                  "n_kinds": len(kinds_sorted)},
    }


@app.get("/api/skein/graph")
@safely("skein_graph")
def skein_graph(_=Depends(require_token)):
    with db_conn() as conn, conn.cursor() as cur:
        if not _skein_tables_exist(cur):
            return orj({"fingerprint": None, "nodes": [], "links": [], "kinds": []})
        fp = _skein_fingerprint(cur) or "noversion"
    path = CACHE_DIR / f"skein_graph_{fp}.json"
    if path.exists():
        try:
            return orj(orjson.loads(path.read_bytes()))
        except Exception as e:
            log.warning("skein graph cache unreadable, rebuilding: %s", e)
    g = _build_skein_graph(fp)
    path.write_bytes(orjson.dumps(g, option=orjson.OPT_SERIALIZE_NUMPY))
    return orj(g)


@app.get("/api/skry")
@safely("skry")
def skry_lookup(q: str, top_chunks: int = 60, top_entities: int = 20,
                _=Depends(require_token)):
    from skry import skry as _skry
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="empty query")
    if top_chunks < 1 or top_chunks > 500 or top_entities < 1 or top_entities > 200:
        raise HTTPException(status_code=400, detail="top_chunks and top_entities out of bounds")
    result = _skry(DB_URL, ollama_url=OLLAMA_URL, embed_model=EMBED_MODEL,
                   query=q, top_chunks=top_chunks, top_entities=top_entities)
    return orj(result)


# ─── URL ingest ─────────────────────────────────────────────────────────────

INGEST_DIR = PROJECT.parent / "ingest"
_ingest_jobs: dict[str, dict] = {}   # job_id → {proc, started_at, url, status, returncode, log_path}
_ingest_lock = threading.Lock()


def _ingest_job_state(job_id: str) -> dict | None:
    with _ingest_lock:
        j = _ingest_jobs.get(job_id)
        if not j:
            return None
        proc = j["proc"]
        running = proc.poll() is None
        state = "running" if running else ("ok" if proc.returncode == 0 else "failed")
        out = {
            "job_id": job_id, "url": j["url"], "status": state,
            "started_at": j["started_at"],
            "returncode": proc.returncode if not running else None,
            "log_tail": "",
        }
        try:
            log_text = Path(j["log_path"]).read_text(encoding="utf-8", errors="replace")
            out["log_tail"] = log_text[-2000:]
        except Exception:
            pass
        return out


@app.post("/api/ingest/url")
@safely("ingest_url")
def ingest_url(payload: dict, _=Depends(require_token)):
    import subprocess, uuid
    url = (payload.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="missing 'url'")
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=400, detail="url must start with http:// or https://")
    if not INGEST_DIR.exists():
        raise HTTPException(status_code=500, detail=f"ingest project not found at {INGEST_DIR}")
    job_id = uuid.uuid4().hex[:12]
    log_path = LOG_DIR / f"ingest_{job_id}.log"
    log_file = open(log_path, "w")
    proc = subprocess.Popen(
        ["uv", "run", "ingest.py", "add", url],
        cwd=str(INGEST_DIR), stdout=log_file, stderr=subprocess.STDOUT,
    )
    with _ingest_lock:
        _ingest_jobs[job_id] = {
            "proc": proc, "url": url,
            "started_at": datetime.datetime.now().isoformat(),
            "log_path": str(log_path),
        }
    log.info("started URL ingest job=%s pid=%s url=%s", job_id, proc.pid, url)
    return orj({"ok": True, "job_id": job_id, "url": url})


@app.get("/api/ingest/jobs/{job_id}")
@safely("ingest_job_status")
def ingest_job_status(job_id: str, _=Depends(require_token)):
    state = _ingest_job_state(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="no such job")
    return orj(state)


@app.get("/api/ingest/jobs")
@safely("ingest_jobs_list")
def ingest_jobs_list(_=Depends(require_token)):
    with _ingest_lock:
        ids = list(_ingest_jobs.keys())
    return orj([_ingest_job_state(i) for i in ids if _ingest_job_state(i)])


# ─── GPU gauge ──────────────────────────────────────────────────────────────

_gpu_cache: dict = {"at": 0.0, "data": None}


@app.get("/api/gpu")
@safely("gpu")
def gpu(_=Depends(require_token)):
    """nvidia-smi snapshot. Cached for 1.5s to avoid hammering it."""
    import subprocess
    now = time.time()
    if _gpu_cache["data"] is not None and (now - _gpu_cache["at"]) < 1.5:
        return orj(_gpu_cache["data"])
    try:
        r = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=name,utilization.gpu,memory.used,memory.total,"
             "temperature.gpu,power.draw,power.limit",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode != 0:
            payload = {"available": False, "reason": r.stderr.strip() or "nvidia-smi failed"}
        else:
            gpus = []
            for line in r.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 7:
                    continue
                def _num(s, t=float):
                    try: return t(s)
                    except (ValueError, TypeError): return None
                gpus.append({
                    "name": parts[0],
                    "util_pct": _num(parts[1], int),
                    "mem_used_mb": _num(parts[2], int),
                    "mem_total_mb": _num(parts[3], int),
                    "temp_c": _num(parts[4], int),
                    "power_w": _num(parts[5], float),
                    "power_limit_w": _num(parts[6], float),
                })
            payload = {"available": True, "gpus": gpus}
    except FileNotFoundError:
        payload = {"available": False, "reason": "nvidia-smi not installed"}
    except subprocess.TimeoutExpired:
        payload = {"available": False, "reason": "nvidia-smi timed out"}
    _gpu_cache["at"] = now
    _gpu_cache["data"] = payload
    return orj(payload)


# ─── legacy llama-per-chunk KG status (kept for comparison) ─────────────────

@app.get("/api/kg/status")
@safely("kg_status")
def kg_status(_=Depends(require_token)):
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name = 'kg_extraction_progress')"
        )
        if not cur.fetchone()[0]:
            return orj({"started": False, "total": 0, "done": 0, "entities": 0, "relations": 0})
        cur.execute("SELECT COUNT(*) FROM chunks"); total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM kg_extraction_progress WHERE status = 'done'"); done = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM kg_extraction_progress WHERE status = 'failed'"); failed = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM kg_entities"); n_e = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM kg_relations"); n_r = cur.fetchone()[0]
    return orj({"started": True, "total": total, "done": done, "failed": failed,
                "entities": n_e, "relations": n_r,
                "pct": round(100.0 * done / total, 1) if total else 0.0})


@app.get("/")
def root():
    return FileResponse(PROJECT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=str(PROJECT / "static")), name="static")


@app.on_event("startup")
def _startup():
    log.info("Bifröst starting · host=%s port=%s db=%s ollama=%s",
             BIND_HOST, PORT, DB_URL, OLLAMA_URL)
    try:
        get_pool()
    except Exception as e:
        log.warning("DB pool could not open at startup (will retry on demand): %s", e)
    # On startup, if no cache exists for the current fingerprint, queue a build.
    if load_cached_graph() is None:
        log.info("no cached chunk graph for current fingerprint — queuing background build")
        kick_off_build(force=False)


@app.on_event("shutdown")
def _shutdown():
    global _pool
    if _pool is not None:
        try:
            _pool.close()
        except Exception as e:
            log.warning("error closing pool: %s", e)
    log.info("Bifröst shutting down")


if __name__ == "__main__":
    log.info(f"Bifröst on http://{BIND_HOST}:{PORT}/?token={TOKEN}")
    uvicorn.run(app, host=BIND_HOST, port=PORT, log_level="info")
