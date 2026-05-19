# docs/bugs/INDEX.md — Bifröst

> Bug notes from Auditor passes. Open bugs are tracked here. Resolved bugs
> stay in the index with status `RESOLVED` and a link to the fix commit.

**Last Auditor pass:** 2026-05-18 (Sólrún Hvítmynd, session 2)

---

## Open

_None. As of session 3 the entire known bug backlog is closed — 19/19
resolved across two same-day sessions._

## Resolved (Session 2 — 2026-05-18)

| # | Title | Severity | File | Note |
|---|---|---|---|---|
| 0001 | `_gpu_cache` race condition | high | `viewer.py:947-985` | [bug](0001-gpu-cache-race.md) |
| 0002 | `_skein_build_proc` race condition | high | `viewer.py:751-815` | [bug](0002-skein-build-race.md) |
| 0003 | `_ingest_jobs` race condition | high | `viewer.py:858-895` | [bug](0003-ingest-jobs-race.md) |
| 0004 | XSS in toast via innerHTML | high | `static/index.html:619-622` | [bug](0004-toast-xss.md) |
| 0005 | XSS in legend titles via innerHTML | high | `static/index.html:303-307` | [bug](0005-legend-xss.md) |
| 0006 | XSS in node label entity names | high | `static/index.html:535-544` | [bug](0006-node-label-xss.md) |
| 0007 | Subprocess log file handles never explicitly closed | high | `viewer.py:483,811,953` | [bug](0007-log-handle-leak.md) |
| 0008 | Token logged in plaintext on startup | medium | `viewer.py:1092` | [bug](0008-token-in-logs.md) |
| 0009 | POST /api/ingest/url uses untyped `dict` payload | medium | `viewer.py:942` | [bug](0009-ingest-payload-validation.md) |
| 0010 | Missing query-length bound on /api/skry | low | `viewer.py:899` | [bug](0010-skry-query-length.md) |
| 0011 | `graph_builder.py` uses `print()` | low | `graph_builder.py:52,85,92` | [bug](0011-graph-builder-print.md) |
| 0012 | Module docstring endpoint list is stale | low | `viewer.py:1-23` | [bug](0012-docstring-drift.md) |

## Deferred

_None. All P2/P3 items from session 2 closed in session 3 (same day) —
see the Resolved table below. **The backlog is empty.**_

## Resolved (Session 3 — 2026-05-18, "kill the backlog")

| # | Title | Severity | File | Note |
|---|---|---|---|---|
| 0013 | `build_graph` was 203 lines | low | `viewer.py` | Refactored into 8 named phase helpers (each ≤50 lines): `_load_chunk_rows`, `_normalize_unit`, `_project_umap_3d`, `_cluster_chunks` + subsampled/full variants, `_compute_term_sets`, `_build_top_k_edges`, `_build_chunk_payload`, `_build_document_payload`. Orchestrator now ~50 lines. Behavior identical; all invariant tests still pass. |
| 0014 | `runSearch` JS 46 lines | low | `static/index.html` | Extracted `_focusCameraOnNodes`, `_runSkrySearch`, `_runStandardSearch`. `runSearch` is now a 10-line dispatcher. |
| 0015 | CDN deps lacked SRI | medium | `static/index.html` | `integrity="sha384-..."` + `crossorigin="anonymous"` on all three scripts. Pin recipe in HTML comment. |
| 0016 | `@app.on_event` deprecated | low | `viewer.py` | Migrated to `lifespan` async context manager. Deprecation warnings gone. |
| 0017 | No subprocess watchdog | medium | `viewer.py` | `_watchdog_check()` runs inside `graph_build_status`: if the build's status JSON hasn't been updated in `VIEWER_BUILD_STALL_AFTER_SEC` (default 600 s) the subprocess is killed and `stage` is marked `stalled`. |
| 0018 | `require_token` implicit return | low | `viewer.py` | Explicit `return None` + docstring. |
| 0019 | `db_conn()` no type hint | low | `viewer.py` | Docstring now documents the `psycopg_pool.PoolConnectionContext` → `psycopg.Connection` contract. |

---

## Categories of issues found this session

- **3 race conditions** on module-level mutable state → all fixed with `threading.Lock`
- **3 XSS surface areas** in the frontend via `innerHTML` of user-derived data → all fixed with escape helper
- **1 resource leak** (subprocess log file handles) → fixed with explicit close after Popen
- **1 secret-leak-by-logging** (token in startup line) → fixed by masking
- **1 input-validation gap** (untyped POST body) → fixed with Pydantic model
- **1 doc-drift** in module docstring → fixed

These are the kinds of issues the Auditor lives to find: silent, structural,
and only visible when concurrent load or motivated attacker shows up. None
of them caused failures in normal single-user testing.
