# DEVLOG.md — Bifröst

> *Written by the Scribe. The record of what changed, why it changed, and
> what was learned. Append-only; never rewrite history.*

---

## 2026-05-18 — Session One: From "Knowledge Database" to "Bifröst"

**Roles invoked across the session:** Skald, Cartographer, Architect, Forge
Worker, Auditor, Scribe.

**Crew:** Volmarr Wyrd (Architect-in-chief, Mythic Engineer), Claude Opus 4.7
(Master Craftsman).

### What was there at dawn

- `~/ai/ingest/` already existed: a pgvector knowledge base with a
  `documents` + `chunks` schema, an `ingest.py` CLI, and a `watch.py`
  inbox watcher. ~15 k chunks across a handful of documents.
- No viewer.
- No knowledge-graph layer.

### What was built

**Phase 1 — Bifröst, first incarnation.** A FastAPI server + single-file
3d-force-graph frontend that projects every chunk into 3D via UMAP, draws
sparse cosine-similarity edges, colors by source document. Sub-second load
once cached. Bound to the tailscale interface; protected by a token.

**Phase 2 — Eight features in one sprint.** Document-level overview;
HDBSCAN topic clusters; edge tooltips showing shared salient terms;
hybrid search with optional HyDE; LLM-assigned cluster names; semantic
path-finder (shortest-path through the similarity graph); and the start of
an entity-extraction knowledge-graph layer using llama-per-chunk.

**Phase 3 — Confronting the llama-per-chunk cost.** Ran the legacy KG
batch on 23 k chunks; it took ~13 min to process 200 chunks (~0.9%).
Projected total: ~76 hours of GPU at 50 W on a travel laptop. Untenable.

**Phase 4 — The inventions: Skein and Skry.** Together with the architect,
we co-invented two new methods to replace the autoregressive-per-chunk
pattern:

- **Skein** — builds an entity-and-relations graph from embeddings using
  *one* LLM call per document (not per chunk) for vocabulary discovery,
  then regex mention-finding, embedding-aggregated entity vectors, top-K
  cosine edges, and predicate-snapping via embedded text-spans against a
  fixed verb vocabulary. ~250× cheaper than llama-per-chunk at comparable
  graph shape.

- **Skry** — query-time entity-neighborhood projection. No precomputation.
  Embed query → top-K chunks → lazy regex NER (optionally filtered by
  Skein's vocabulary) → rank by `count × mean_similarity`. ~100 ms per
  lookup. Always fresh; works the instant a new document is ingested.

Both extracted into their own repositories under `~/ai/skein-kg/` and
`~/ai/skry-kg/`. Both made public on GitHub with full MIT licensing and
prose READMEs. The viewer consumes them as local-path dependencies.

**Phase 5 — Robustness pass.** First major refactor of `viewer.py`:

- DB connection pool via `psycopg_pool` (was: new `psycopg.connect()` per request)
- orjson with `OPT_SERIALIZE_NUMPY` (was: FastAPI's default JSONResponse, ~3× slower on the 17 MB chunk-graph payload)
- Structured logging via `logging` module (was: `print()`)
- `@safely(...)` decorator wrapping every endpoint (was: unprotected; one bad request could 500 the worker)
- `/api/health` endpoint reporting db/ollama/cache state
- Async chunk-graph build via in-process `threading.Thread` with a state-machine status endpoint (replacing blocking-build behavior)
- systemd user unit at `systemd/bifrost.service` with `Restart=on-failure`, memory ceiling, and crash-loop guard

**Phase 6 — Mythic Engineering documents, first pass.** Wrote
`SYSTEM_VISION.md`, `DOMAIN_MAP.md`, `ARCHITECTURE.md`, `PROJECT_LAWS.md`,
and `static/README_AI.md` per the partial spec gleaned from the user's
corpus. Pushed all three projects to public GitHub repos:
- `hrabanazviking/bifrost-viewer`
- `hrabanazviking/skein-kg`
- `hrabanazviking/skry-kg`

**Phase 7 — GPU gauge.** Added `/api/gpu` endpoint (nvidia-smi subprocess
with 1.5 s cache) and a Bifröst widget (bottom-left, above SKEIN) showing
utilization, VRAM, temperature, and power with severity-based coloring.
Same data also wired into the desktop `eww` gungnir-gauges widget under a
new section header *GPU · DAGAZ* (rune of day/breakthrough — the thing
that lights up the screen).

**Phase 8 — URL ingest, three ways.**
- `POST /api/ingest/url` + top-right input field in the viewer, with toast
  notifications and live polling of `/api/ingest/jobs/{id}`.
- `watch.py` extended to handle `.url` (Windows shortcut), `.urls` (line
  list), and `.txt` (line list if every line is an http(s) URL).
- Shell function `inhale` in `~/.bashrc` and `~/.zshrc` for one-keystroke
  ingestion from any terminal.

### The crisis (and the fix)

Late session, the user reloaded Bifröst and saw the loader stuck. The
chunk-graph build (now over 34 k chunks) had run for 8 minutes inside the
`threading.Thread` and HDBSCAN's O(N²) linkage was holding the GIL,
starving the FastAPI request threads. The server was technically alive but
every request timed out.

**Lesson learned (recorded for posterity):** *Python threads do not escape
the GIL for CPU-bound numpy/HDBSCAN work.* Skein had used a subprocess
pattern from the start; Bifröst had used a thread because the build needed
to share the DB pool. That sharing turned out not to be worth the GIL cost.

**Fix:** extracted `build_graph` callable into a standalone subprocess
script `graph_builder.py`. Reworked `kick_off_build` to spawn the
subprocess via `subprocess.Popen` and the build status reporting to write
to `.cache/build_status_<fp>.json` (read by `/api/graph/build-status`).
The viewer now serves requests in 45 ms even mid-build.

### The second crisis (and the second fix)

Restarted the build. New problem: HDBSCAN on 34 k vectors of 768 dimensions
was still O(N²) per core, and the subprocess sat at 99% CPU for 8+ minutes
with no end in sight.

**Fix:** added a chunk-count threshold (`VIEWER_HDBSCAN_SUBSAMPLE_ABOVE`,
default 12 000). Above the threshold, cluster a deterministic 6 000-vector
random subsample (~30 s), then propagate cluster labels to the remaining
vectors by 1-nearest-neighbor in cosine space (<1 s). For 34 826 chunks
the full pipeline now finishes in 2 min 14 s end-to-end, vs the prior
infinite-stall behavior.

### What's in the cache at dusk

- 34 826 chunks across 33 documents (and growing)
- 45 HDBSCAN-equivalent topic clusters
- 276 Skein entities, 855 typed relations
- Bifröst, Skein, Skry — all three repos public

### Invariants discovered or reinforced

1. **The fingerprint is content-addressed.** Built from `(count, max_id)`
   of `chunks`. Any change to the corpus invalidates exactly the right
   caches.
2. **Heavy work must be out-of-process.** Threads cannot save you from the
   GIL when the work is C-extension single-threaded compute.
3. **The loader must always narrate.** A silent loader is a contract
   violation; users assume the worst.
4. **`@safely(...)` is mandatory on every endpoint.** Removing it on even
   one endpoint creates a class of regressions where unhandled exceptions
   bring down the worker.
5. **No `print()` ever.** Logs go through `logging`. Stdout is for systemd
   journal only.

### Decisions not (yet) recorded as ADRs

To be promoted to `docs/decisions/` in a future session:
- Why we chose to keep the legacy llama-per-chunk batch in the repo as a
  "the slow way" comparison artifact rather than deleting it.
- Why Skein's vocabulary discovery uses one LLM call per *document* rather
  than per chunk-cluster (which would have been more semantically
  motivated but harder to explain).
- Why the GPU widget polls every 2 s and the Skein widget every 5 s (UX
  tradeoff: GPU is "live data," Skein is "occasional update").
- Why Skry has *no* batch mode by design (so it can never go stale).

### Open threads for next session

- Auditor pass on `viewer.py`, `graph_builder.py`, `static/index.html`
  per the Mythic Engineering bug-hunt rite. Findings will live in
  `docs/bugs/`.
- Robustness pass: type-hint every function; method-length audit (any
  method >50 lines becomes a refactor candidate); cross-platform audit
  (the Linux assumptions in nvidia-smi, systemd, and tailscale paths).
- Add minimal invariant test scaffold under `tests/` per ME's Prophecy
  Rite.
- Migrate the deprecated `@app.on_event("startup")` to the `lifespan`
  context manager.
- Consider a watchdog for graph_builder subprocesses (currently a stuck
  build is escape-hatched via `pkill -f graph_builder.py`).

---

## 2026-05-18 — Session Two: Full Mythic Engineering Treatment

The architect pointed at the canonical Mythic Engineering repository
(`hrabanazviking/Mythic-Engineering`) and asked for the full doctrine
applied to all three projects — including the formal **bug hunt** and
**robustness** rites.

Work for this session is tracked in the live task list and documented as
each subtask completes. Highlights to be appended here at session close.
