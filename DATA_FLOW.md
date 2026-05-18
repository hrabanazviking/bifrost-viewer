# DATA_FLOW.md — Bifröst

> *Written jointly by the Architect and the Cartographer. Every byte that
> enters this system has a path; this is its map.*

---

## Entry Points

Data can enter Bifröst's awareness through five distinct doors. No other
ingress paths exist.

| # | Door | Triggered by | Direction |
|---|------|--------------|-----------|
| 1 | `documents` + `chunks` (Postgres) | Out of scope (owned by `~/ai/ingest/`). Bifröst observes; does not write. | **In** |
| 2 | `skein_*` tables (Postgres) | Out of scope (owned by `~/ai/skein-kg/`). Bifröst reads; does not write. | **In** |
| 3 | `kg_*` legacy tables (Postgres) | Out of scope (legacy llama batch). Read-only from Bifröst. | **In** |
| 4 | `POST /api/ingest/url` | A user pasting a URL into the viewer's URL bar. | **In** (spawns ingest subprocess that writes via the ingest pipeline) |
| 5 | `.env` | Operator at install time. | **In** (config only) |

Outgoing surfaces:

| # | Door | Triggered by | Direction |
|---|------|--------------|-----------|
| A | HTTP JSON over the tailscale interface | Browser at the configured token. | **Out** |
| B | `logs/bifrost.log` + stdout | Every endpoint, every background event. | **Out** |
| C | `.cache/*.json` | Graph builder subprocess, skein-graph projector, cluster-names builder. | **Out** (writes; reads on next request) |

---

## Rivers of Flow

### River I — Cold Page Load (no cache)

```
browser GET /                                    →  static/index.html
browser GET /api/skein/status                    →  read skein_* tables
browser GET /api/gpu                             →  shell out to nvidia-smi (1.5s cache)
browser GET /api/graph?level=chunk
   viewer: load_cached_graph() → None
   viewer: kick_off_build(force=False)
      spawns subprocess: uv run graph_builder.py <fingerprint>
   viewer: returns 202 Accepted with {pending: true, build_state}
browser polls /api/graph/build-status every 1.5s
   viewer reads .cache/build_status_<fp>.json (written by subprocess)
   returns {stage, progress, running, error, cache_exists}
browser loader displays "weaving the bridge · <stage> · <pct>%"

graph_builder.py subprocess (separate Python interpreter, no GIL contention):
   1. Read all chunks + embeddings from Postgres
   2. UMAP 3D projection (CPU-bound, single-threaded by random_state)
   3. HDBSCAN clustering (full at ≤12k chunks; subsample-then-1NN above)
   4. tf-idf top terms per chunk (for edge labels)
   5. all-pairs cosine; top-K edges with min similarity
   6. Document-level aggregation (one node per doc, cross-doc edges)
   7. Write .cache/graph_<fp>.json via orjson (atomic via .tmp rename)
   8. Write .cache/build_status_<fp>.json with running=false, stage=done

next poll sees cache_exists=true, running=false
browser GET /api/graph?level=chunk → 200 OK with the cached JSON (170-330 ms)
browser renders ForceGraph3D with the payload
```

### River II — Warm Cache Page Load

```
browser GET /api/graph?level=chunk
   viewer: load_cached_graph() reads .cache/graph_<fp>.json
   returns 200 OK with the cached payload in ~170 ms
```

If the fingerprint has changed since the cache was written (e.g. new chunks
have been ingested), `load_cached_graph()` returns None and the cold-load
flow above engages. The previous cache is pruned during the build.

### River III — Hybrid Search

```
browser GET /api/search?q=<query>&hyde=0|1
   if hyde=1:
      ollama_chat(question → hypothetical answer)
      query_text = hypothetical answer
   ollama_embed([query_text]) → embedding
   Postgres CTE:
      sem CTE: top 60 chunks by cosine
      kw CTE: top 60 chunks by ts_rank(tsv, plainto_tsquery(q))
      RRF fusion: 1/(60+sem_rank) + 1/(60+kw_rank)
   return top-K {id, sim, score}
browser pulses matching nodes yellow, flies camera to centroid
```

### River IV — Skry Lookup (Query-time Entity Neighborhood)

```
browser GET /api/skry?q=<name_or_phrase>
   import skry; skry.skry(...)
   skry.core:
      ollama_embed([query]) → embedding
      Postgres top-K chunks by cosine
      check skein_entities exists → load vocabulary {name_norm: canonical}
      lazy regex NER on retrieved chunks (filtered by vocab if present)
      aggregate: count × mean_similarity → score
   return {query, vocab_mode, entities[], evidence_chunk_ids}
browser populates side panel; if level=ENTITIES, highlights matching nodes
```

### River V — Path Finding

```
browser GET /api/path?a=<id>&b=<id>
   load_cached_graph()["chunk"]["links"] → networkx.Graph
   weight = 1 - sim (clamped above zero)
   networkx.shortest_path(G, a, b, weight="weight")
   return {found, nodes[], edges[]}
browser renders edges along the path in cyan, dims everything else
```

### River VI — Skein Build (Out-of-Process)

```
browser POST /api/skein/build
   subprocess.Popen(["uv", "run", "skein", "build"]) in ../skein-kg/
   record proc + log_path in _skein_build_proc dict
   return {ok, pid, log}

subprocess (in skein-kg, separate interpreter):
   skein.core.build_skein(...)
      - one ollama_chat per document (vocabulary discovery)
      - regex mention scan
      - entity embedding aggregation
      - top-K cosine edges + predicate snapping via embedded text-spans
      - persists to skein_entities, skein_entity_chunks,
        skein_relations, skein_build in Postgres

browser polls /api/skein/status every 5s
   reads counts from Postgres + checks if proc.poll() is None
   returns {built, running, n_entities, n_relations, last_build}

on completion: viewer prunes .cache/skein_graph_*.json
next /api/skein/graph rebuilds the 3D layout (UMAP on entity embeddings)
```

### River VII — URL Ingest (Out-of-Process)

```
browser POST /api/ingest/url with {url}
   subprocess.Popen(["uv", "run", "ingest.py", "add", url]) in ../ingest/
   register {job_id, proc, url, log_path} in _ingest_jobs
   return {ok, job_id, url}

subprocess (in ~/ai/ingest/, separate interpreter):
   ingest.py add <url>
      trafilatura.fetch_url + extract → markdown
      unstructured.chunking → chunks
      ollama_embed → vectors
      INSERT into documents + chunks

browser polls /api/ingest/jobs/<job_id> every 2s
   reads proc.poll() + tails the log file
   returns {status: "running"|"ok"|"failed", returncode, log_tail}

on completion: toast turns green or red
next chunk-graph rebuild (manual or auto) picks up the new chunks
```

### River VIII — GPU Snapshot

```
browser GET /api/gpu  (every 2s from index.html)
   if (now - _gpu_cache.at) < 1.5s: return cached
   subprocess.run(["nvidia-smi", "--query-gpu=...", "--format=csv,noheader,nounits"], timeout=3)
   parse 6 fields
   cache + return {available, gpus: [{name, util_pct, mem_used_mb, mem_total_mb, temp_c, power_w}]}
browser updates gauge with severity coloring
```

---

## Storage Locations and Lifecycles

| Storage | Owned by | Lifetime | Invalidation rule |
|---|---|---|---|
| `documents` table | ingest project (not Bifröst) | Persistent | Manual delete by owner |
| `chunks` table | ingest project | Persistent | CASCADE on document delete |
| `skein_*` tables | skein-kg library | Persistent | Wiped + rewritten on each `skein build` |
| `kg_*` tables | legacy llama batch | Persistent (kept for comparison) | Manual; no longer written |
| `.cache/graph_<fp>.json` | Bifröst graph_builder | Persistent until fingerprint changes | Auto-pruned on next build for new fp |
| `.cache/skein_graph_<fp>.json` | Bifröst viewer | Persistent until skein rebuild | Pruned on POST `/api/skein/build` |
| `.cache/clusternames_<fp>.json` | Bifröst viewer | Persistent until chunk-graph rebuild | Pruned on POST `/api/refresh` |
| `.cache/build_status_<fp>.json` | graph_builder subprocess | Per build | Pruned on next build for new fp |
| `logs/bifrost.log` | viewer | Append-only | External rotation (logrotate / journald) |
| `logs/skein_build_*.log` | viewer (skein subprocess) | Per skein build | Manual cleanup; one per build |
| `logs/ingest_*.log` | viewer (ingest subprocess) | Per URL ingest job | Manual cleanup; one per job |
| `logs/graph_build_*.log` | viewer (graph_builder subprocess) | Per graph build | Manual cleanup; one per build |

---

## Boundary Crossings

These are the only places where data leaves one realm and enters another.
Each crossing is enumerated so future maintainers know where to look when
data shape changes.

| # | From | To | Format | Where to find |
|---|------|----|--------|---------------| 
| 1 | Postgres | viewer `build_graph()` | rows of (id, doc_id, chunk_index, text, embedding, …) | `viewer.py` build_graph SELECT |
| 2 | viewer | `.cache/graph_*.json` | nested dict (chunk + document payloads) | `graph_builder.py` write_bytes |
| 3 | `.cache/graph_*.json` | viewer GET /api/graph | orjson deserialized → orjson serialized | `load_cached_graph` |
| 4 | viewer | browser | JSON over HTTP | `orj(...)` Response helper |
| 5 | browser → viewer | URL ingest | `{"url": "..."}` POST body | `ingest_url` endpoint |
| 6 | viewer → ingest subprocess | argv | `["uv", "run", "ingest.py", "add", url]` | `ingest_url` endpoint |
| 7 | viewer → skein subprocess | argv | `["uv", "run", "skein", "build"]` | `skein_build` endpoint |
| 8 | viewer → graph_builder subprocess | argv + status JSON | `["uv", "run", "graph_builder.py", fp]` then file polling | `kick_off_build` |

---

## Where Things Go Wrong (and How They Are Reported)

| Failure | Detection | User-visible behavior |
|---|---|---|
| Postgres unreachable | `db_alive()` returns False | `/api/health` reports `db: false`; graph endpoints raise 500 via `@safely(...)` |
| Ollama unreachable | `ollama_alive()` returns False | `/api/health` reports `ollama: false`; HyDE silently falls back to raw query (logged); cluster-names labels default to `Cluster <id>` |
| nvidia-smi missing | subprocess raises FileNotFoundError | `/api/gpu` returns `{available: false}`; frontend hides the GPU widget |
| Graph build crash | subprocess exits non-zero or writes `stage=failed` | `/api/graph/build-status` reports `running=false, stage=failed, error=...`; loader turns red with the error text |
| Skein build crash | subprocess exits non-zero | `/api/skein/status` shows `running=false`; failed log in `logs/skein_build_*.log` |
| URL ingest failure | subprocess exits non-zero | Toast turns red with the last error line from the subprocess log |
| Cache file corrupt | orjson decode raises | `load_cached_graph()` returns None (logged warning); build is re-triggered |
| Subprocess hangs | Build status polling sees no progress for >N min | Not currently auto-detected; manual `pkill -f graph_builder.py` is the escape hatch. See `docs/bugs/0001-no-build-watchdog.md` |
