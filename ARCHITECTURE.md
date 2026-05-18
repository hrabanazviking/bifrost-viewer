# ARCHITECTURE.md — Bifröst
## *The Bones of the World*

> The shape that bears all weight. Walls move only with great deliberation —
> not because someone wished a feature would fit better.

---

## Major Structure

```
~/ai/ingest-viewer/
├── viewer.py           ← The Mind: FastAPI app, all endpoints, async build orchestrator
├── pyproject.toml      ← Dep manifest (uv-managed)
├── .env                ← Local config (NEVER committed)
├── .env.example        ← Template for new installs
├── static/
│   ├── index.html      ← The Face: full 3D viewer UI (HTML + CSS + JS, single file)
│   └── README_AI.md    ← Notes for AI maintainers working in the static realm
├── .cache/             ← Memoized graph builds, cluster names, skein projections
├── logs/               ← Structured logs (bifrost.log, skein_build_*.log)
├── SYSTEM_VISION.md    ← The soul (read first)
├── DOMAIN_MAP.md       ← Realm boundaries
├── ARCHITECTURE.md     ← This document
├── PROJECT_LAWS.md     ← Immutable rules for contributors
└── README.md           ← Quick-start
```

External siblings consumed as dependencies (see `[tool.uv.sources]`):

```
~/ai/skein-kg/    ← Static entity graph built from embeddings
~/ai/skry-kg/     ← Query-time entity neighborhood projection
```

External system dependencies (assumed present, NOT managed by Bifröst):

- Postgres with `vector` and `pg_trgm` extensions and the standard
  `documents` + `chunks` schema (see `~/ai/ingest/schema.sql`).
- Ollama with the embedding model (`nomic-embed-text`) and chat model
  (`llama3.2:3b`) referenced in `.env`.

---

## Rivers of Flow

### River of First Sight (cold page load)

```
browser GET /                       → static/index.html
browser GET /api/skein/status       → Skein widget initializes
browser GET /api/graph?level=chunk  → cache miss → 202 Accepted + build kicked off
browser polls /api/graph/build-status (every 1.5s) → shows progress in loader
build thread:
    1. fingerprint() against Postgres
    2. fetch all chunks + embeddings
    3. UMAP 3D projection
    4. HDBSCAN clustering
    5. tf-idf edge labels
    6. top-K cosine edge build
    7. orjson.dumps → .cache/graph_<fp>.json
build complete → status reports cache_exists=true
browser GET /api/graph?level=chunk  → 200 OK with payload (170ms from cache)
browser renders 3d-force-graph → page becomes interactive
```

### River of Subsequent Sight (warm cache)

```
browser GET /api/graph?level=chunk  → cache hit → 170ms response
browser renders → interactive
```

### River of Search

```
browser → /api/search?q=…&hyde=0
    if hyde: ollama_chat(question→hypothetical answer)
    embedding ← ollama_embed(query_text)
    Postgres hybrid query (semantic + keyword RRF)
    return top-K chunk IDs
browser pulses matching nodes, flies camera to centroid
```

### River of Skein (vocabulary discovery → predicate-snapped graph)

```
browser → POST /api/skein/build
viewer spawns subprocess: `uv run skein build` in ~/ai/skein-kg/
the subprocess:
    1. discover_vocabulary — one ollama call per document
    2. find_mentions       — regex over all chunks
    3. compute_entity_embeddings — mean of chunk vectors
    4. build_edges         — top-K cosine on entity embeddings
    5. snap_predicates     — embed text-between-mentions, snap to fixed vocab
    6. persist             — write skein_entities, skein_relations, skein_build
browser polls /api/skein/status → progress visible
on completion: skein_graph cache invalidated; next /api/skein/graph rebuilds 3D layout
```

### River of Skry (live entity lookup)

```
browser → /api/skry?q=Odin
viewer calls skry.skry(...):
    1. embed query
    2. Postgres top-K chunks by cosine
    3. lazy regex NER on those chunks (filtered by skein_entities if present)
    4. rank by count × mean_similarity
return entity list with evidence chunk IDs
browser shows side panel
```

---

## Key Connectors

| From | To | Protocol | Notes |
|------|----|----------|-------|
| Face → Mind | HTTP/JSON | Token in URL (`?token=…`) or `Authorization: Bearer …` | All API calls go through `safely(...)` |
| Mind → Deep Memory | psycopg + `psycopg_pool` | Single shared pool, min_size=1, max_size=8 | Opened lazily at first request |
| Mind → Ollama | httpx | Timeout: 120-300 s | Failures degrade gracefully (HyDE falls back to raw query, cluster names fall back to "Cluster N") |
| Mind → Skein | Python import | `skein.build_skein`, `skein.neighbors_of` | The Skein build itself is run as a *subprocess* to keep the FastAPI process responsive |
| Mind → Skry | Python import | `skry.skry(...)` | In-process call, ~100 ms typical |

---

## Background Work Model

Two patterns coexist:

1. **In-process thread** for the chunk-graph build (`threading.Thread`). State
   is kept in a global dict guarded by `_build_lock`. Used because the graph
   build needs the same DB pool and numpy state as the request thread.

2. **Detached subprocess** for the Skein build. Used because Skein takes
   ~15-20 min and we don't want a thread holding any DB cursor or memory for
   that long. The subprocess writes to its own log file under `logs/`.

Both report progress via a `/api/.../status` endpoint that the frontend polls.

---

## Cache Discipline

Every cache file is named with a *fingerprint* that includes the data shape it
was derived from. For the chunk graph: `graph_v2_<chunk_count>_<max_chunk_id>.json`.
When ingest adds new chunks, the fingerprint changes; on the next read, the
old cache is detected as stale and rebuilt. There is exactly one valid cache
file per kind at any time — others are pruned during build.

If the cache file format ever needs to change incompatibly, bump the version
prefix (`v2_` → `v3_`). Old caches will be silently ignored and pruned, never
loaded.

---

## What can change safely

- Add new endpoints. Use the `@safely(...)` decorator. Add the route to the
  module docstring.
- Add new visualization modes / toggles to `static/index.html`. The single-file
  layout is intentional — keep it.
- Tune the EDGE_TOP_K, EDGE_MIN_SIM, HDBSCAN_MIN_CLUSTER constants in `.env`.
- Add new caches under `.cache/` using the fingerprint pattern.

## What must NOT change without redrawing this map first

- The endpoint shapes consumed by `static/index.html`. The Face trusts those
  contracts.
- The async build state machine (`_build_state`, `_build_lock`, the polling
  endpoint). The loader UX depends on it.
- The fingerprint scheme. Other caches and external scripts may rely on it.
- The realm boundaries in `DOMAIN_MAP.md`.
