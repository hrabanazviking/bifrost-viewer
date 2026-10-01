# ARCHITECTURE.md — Bifröst
## *The Bones of the World*

> The shape that bears all weight. Walls move only with great deliberation —
> not because someone wished a feature would fit better.

---

## Major Structure

```
~/ai/ingest-viewer/
├── viewer.py           ← The Mind: FastAPI app, all endpoints, async build orchestrator
├── inference.py        ← Separate chat contracts, private key, bounded admission/circuit
├── inference.json      ← Chat routing policy
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
  `documents` + `chunks` schema (see `ingest/schema.sql`).
- Ollama with the embedding model (`nomic-embed-text`) and chat model
  (`llama3.2:3b`) referenced in `.env`.

---

## Rivers of Flow

### River of First Sight (cold page load)

```
browser GET /explore                → static/index.html
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
    if hyde: selected chat router(question→hypothetical answer)
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
on completion: new build-generation cache key; next /api/skein/graph builds the matching 3D layout while previous caches remain available
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
| Mind → chat router | bounded httpx, policy JSON | 45 s per-operation HTTP timeout, 0.2 s admission wait, one call | Explicit primary circuit/fallback; HyDE raw-query and cluster-label degradation |
| Mind → Ollama embeddings | httpx | 300 s | Original embedding identity; keyword fallback on query-embedding failure |
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
file per kind at any time. Obsolete generated layouts are pruned only after a
replacement is atomically published; failed computation/writes keep the old files.

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

## 2026-09-30 architecture update

Current graph builds run in graph_builder.py subprocesses for both corpus and
entity layouts. The asynchronous maintenance loop owns recovery independently
of browser polling. runtime_support.py owns atomic cache publication; local_server.py
owns loopback plus configured listener sockets. Fingerprint prefix v3 selects sparse
document neighbors and preserves existing payload fields. Existing cache files are
kept recoverable. scripts/watch_inbox.py is an optional ingest CLI supervisor,
with parsing/storage ownership remaining in the separate bundled ingest component.
See INTERFACE.md and docs/operations.md for current contracts and limits.

## Bundled ingest ownership (2026-09-30)

The ingest/ subproject owns the published parser/embedding CLI, schema and frozen
dependencies. It remains a separate subprocess domain; viewer.py delegates rather
than writing source tables. URL jobs use uv run --frozen --project ingest. The
watcher uses that same source runtime, with INGEST_ENV_FILE and INGEST_STATE_DIR
pointing to private configuration and durable inbox storage independently. Existing
local sibling entry points forward to the bundled source for compatibility.

## Portable security boundary

SecurityGateway admits requests before body parsing, checks transport/host/origin,
verifies bearer scopes, and enforces weighted quotas and expensive-query concurrency.
SecurityStore serializes recovery, key revocation and job admission in private SQLite
transactions. API keys have hashes; the owner launcher credential and SMTP password
are recoverable secrets protected by filesystem permissions. This does not protect
against an attacker already controlling the local user account.

IngestQueue supervises one bounded subprocess at a time. Idempotency and quota
admission commit together; interrupted jobs recover after restart and document
hashes prevent duplicate writes. The worker uses its own restricted PostgreSQL role,
not the viewer database owner. safe_fetch pins validated public addresses and checks
every redirect. Local trusted inbox ingestion remains a separate existing supervisor.

Owner UI and protocol details live in security/README_AI.md and security/INTERFACE.md.

## Durable ingestion boundaries

The ingest component owns parsing, embedding validation and atomic source appends.
Recovery/embedding/diagnostics are separate modules; recovery.json validates and
bounds retries/deadlines. A fixed target vector dimension is checked before writes.
The local inbox delegates process lifetime and atomic last-good state to small
script helpers and reports health/progress in private inbox metadata. The API queue
uses one file-locked supervisor, sanitized private-log markers and an append-only
SQL role in a read-only filesystem sandbox. Original revoked clients remain blocked
even when the owner requests retry. No recovery path changes the source schema.

Skein 0.1.1 holds a cooperative database advisory lock and gates publication on
discovery coverage. Entity layouts use actual build-generation keys and one
repeatable-read snapshot. Source counts/IDs remain the underlying corpus fingerprint;
in-place source changes still require deliberate refresh.

## Human workspace and agent connections

`GET /` serves `static/workspace.html`: identity, read-only counts, health, search,
passage reading and append forms. It never loads the full graph just for counters.
`/explore` preserves the graph. `/security` uses the shared responsive theme, and
`/connect` provides server metadata, placeholder-only setup examples and MD downloads.

`security/connections.py` owns public discovery, owner-controlled advertised origin,
principal-specific capabilities and a curated authenticated agent OpenAPI schema.
Discovery has a separate public quota and contains no corpus or credentials. The
profile is metadata, not a proxy or network configurator. Origin/TLS/Host admission
and the private SecurityStore remain authoritative.

`clients/` runs on an AI machine. A bounded standard-library REST client verifies
TLS, refuses redirects and requires stable append IDs. Its optional SDK 2 MCP stdio
adapter exposes only scoped knowledge operations, with append tools disabled until
explicitly enabled. It uses the same REST API, never PostgreSQL or an alternate
write endpoint. The viewer's dependency environment remains independent.

## Independent native chat ownership — 2026-10-01

The same-host Aesir service owns native CUDA generation and local authentication;
its user unit owns supervised process restart. Bifröst inference.py independently
owns provider admission, private regular-file credential loading, HTTP budgets,
one finite semaphore wait, completion/model validation and an explicit primary
circuit/fallback. Native health identifies the loaded model and absent embedding
capability. The existing Ollama embedding URL and model remain the corpus space.
The viewer delegates its legacy ollama_chat helper to the lazy router, closes it
on shutdown, and exposes safe inference state in existing authenticated health.
No source DB, append role, externally reachable route or scoped-key policy changes.
Measured native latency is still higher; the default remains Ollama.
See AESIR_BACKEND.md for configuration, time-budget boundaries and recovery.
