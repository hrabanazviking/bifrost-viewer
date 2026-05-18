# Bug 0011: `graph_builder.py` uses `print()` instead of `logging`

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18

---

## Symptom

`graph_builder.py` calls `print(...)` for status (lines 52, 85, 92). The subprocess's stdout is redirected to `logs/graph_build_*.log` so the data isn't lost — but it doesn't go through the `logging` module, doesn't carry timestamps in the same format as `bifrost.log`, and can't be filtered by level.

## Expected

Use `logging` with the same handler config as `viewer.py` so all logs (main + subprocess) look uniform.

## Invariant violated

PROJECT_LAWS — Law of Honest Logs ("never `print()`").

## Fix plan (additive)

Replace each `print(...)` with `log.info(...)` or `log.error(...)`. Add the same `basicConfig` boilerplate at the top of `graph_builder.py`.

## Lessons

Subprocesses are easy to forget when sweeping for `print` calls. The Auditor's checklist now includes "grep `print(` across the whole project."
