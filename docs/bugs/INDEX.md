# docs/bugs/INDEX.md — Bifröst

> Bug notes from Auditor passes. Open bugs are tracked here. Resolved bugs
> stay in the index with status `RESOLVED` and a link to the fix commit.

**Last Auditor pass:** 2026-05-18 (Sólrún Hvítmynd, session 2)

---

## Open

_none — all P0/P1 from session 2 have been promoted to dedicated notes and
fixed additively this session. P2/P3 items remain in this index._

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

## Deferred (open in index, fix later)

| # | Title | Severity | File | Reason for deferral |
|---|---|---|---|---|
| 0013 | `build_graph` is 203 lines (Iron Law: ≤50) | low | `viewer.py:220-422` | Refactor planned for next session — pure restructuring, no behavior change, large diff. Tracked in next session's GOALS. |
| 0014 | `runSearch` JS function 46 lines | low | `static/index.html:404-448` | Just under limit; refactor when adding a third search mode. |
| 0015 | CDN deps for three.js / 3d-force-graph / three-spritetext lack SRI hashes | medium | `static/index.html:227-229` | Vendoring planned; needs decision on whether to add a build step. ADR forthcoming. |
| 0016 | FastAPI `@app.on_event("startup")` deprecated | low | `viewer.py:1066,1080` | Migration to `lifespan` planned; not blocking. |
| 0017 | No watchdog for stuck graph_builder subprocess | medium | `viewer.py:_do_build` removed; subprocess equiv | Escape hatch is `pkill -f graph_builder.py`. Watchdog is nice-to-have. |
| 0018 | `require_token` has no explicit return | low | `viewer.py:139-147` | Cosmetic; FastAPI dependency convention allows implicit None. |
| 0019 | `db_conn()` lacks return type hint | low | `viewer.py:122-124` | Cosmetic; type can be inferred via context manager. |

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
