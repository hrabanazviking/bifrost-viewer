# DOMAIN_MAP.md — Bifröst
## *Cartography of Realms*

> Every realm has a sacred boundary. To cross a boundary is to break the world.
> If a feature does not fit any realm here, the map is wrong, not the feature
> — fix the map first.

---

## The Realms

### 1. The Face of the World — `static/`

**Responsibility:** Everything the user sees. HTML, CSS, JavaScript, the
3D-force-graph rendering, the panels, the toggles, the search bar, the loader.

**Knows about:** Browser APIs, three.js, fetch(), the public shape of
`/api/*` responses.

**Forbidden from:**
- Touching the database directly.
- Calling Ollama directly.
- Holding any secret beyond the URL-supplied token.
- Performing any computation longer than a single animation frame.

### 2. The Mind and Rules — `viewer.py` (route layer)

**Responsibility:** HTTP routing, authentication, request validation,
orchestration of background builds, marshalling responses through orjson.

**Knows about:** FastAPI, the cache layer, the build state machine, Skein +
Skry library calls, ollama proxying.

**Forbidden from:**
- Issuing raw SQL outside the DB pool helper.
- Embedding HTML / static assets inline (those belong in `static/`).
- Performing multi-second computation in the request thread (must be backgrounded).
- Swallowing errors silently — every endpoint is wrapped via `@safely(...)`.

### 3. The Deep Memory — Postgres (read-only from Bifröst)

**Responsibility:** `documents`, `chunks`, `kg_*`, `skein_*` tables.

**Knows about:** Nothing. It is reads and writes, and that is all.

**Forbidden from (Bifröst's perspective):**
- Being mutated by Bifröst beyond the `skein_*` and graph-build artifacts.
  Documents and chunks are sacred and owned by the Ingest project.

### 4. The Caches — `.cache/`

**Responsibility:** Memoized graph builds, cluster names, skein graph
projections. Keyed by data fingerprints so stale caches are auto-invalidated.

**Knows about:** orjson, the path conventions (`graph_<fp>.json`,
`skein_graph_<fp>.json`, `clusternames_<fp>.json`).

**Forbidden from:**
- Being treated as the source of truth. Caches are *always* re-derivable from
  the database.
- Surviving a schema change. New `vN_` prefix on the fingerprint = old caches
  must die.

### 5. The Logs — `logs/`

**Responsibility:** Structured log of every endpoint call, every warning,
every error, every background build progress event. Per Law of Fault
Tolerance, nothing prints to stdout in production — it goes through `log`.

**Knows about:** Python's `logging` module and the `bifrost.log` file.

**Forbidden from:**
- Storing personal data beyond what is necessary to debug a failure.
- Being rotated by anything other than systemd/logrotate (no in-process
  rotation logic).

### 6. The Companion Realms — `~/ai/skein-kg/` and `~/ai/skry-kg/`

**Responsibility:** Two separate packages, installed as dependencies. Skein
weaves the static entity graph; Skry performs query-time entity lookups.

**Knows about:** Their own data — see their own SYSTEM_VISION docs.

**Forbidden from (Bifröst's side):**
- Being modified in-place. They are external libraries; Bifröst calls their
  public API and trusts their contracts. To change them, go to their repo and
  cut a release.

---

## Why these boundaries

Two things break a small project: presentation code that knows about the
database, and business logic that ends up smeared across templates. The
Realms above prevent both.

The Face of the World can be replaced wholesale (with a different rendering
library, a TUI, even a screensaver) without touching the Mind. The Mind can
be repointed at a different Postgres or a different Ollama without touching
the Face. The Deep Memory can grow new tables without Bifröst caring, as
long as the public columns of `documents` and `chunks` stay stable.
