# Bug 0002: `_skein_build_proc` race condition

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18

---

## Symptom

`/api/skein/build` checks `_skein_build_proc["proc"]` without a lock, then spawns a new subprocess if no current build is running. Two concurrent POSTs to `/api/skein/build` can both pass the "already running" check and spawn two competing builds — both writing to the same `skein_*` tables.

## Expected

At most one Skein build subprocess at a time. The second concurrent request should return `{"ok": false, "reason": "already running"}`.

## Invariant violated

PROJECT_LAWS — *Law of Fault Tolerance* and *Law of Idempotent Builds*. Two concurrent builds racing on the same DELETE+INSERT transaction can corrupt or partially populate `skein_*`.

## Suspected domain

Realm of the Mind (`viewer.py` route layer); Companion Realm (skein-kg) is the victim.

## Reproduction

```
curl -X POST .../api/skein/build &
curl -X POST .../api/skein/build &
```
Both return `{"ok": true}` with different `pid`s. Two `skein build` processes appear in `pgrep -f skein`.

## Hypothesis

`_skein_build_proc` is a plain dict accessed without synchronization. The check (`if p is not None and p.poll() is None: return …`) and the subsequent `subprocess.Popen + dict update` are not atomic.

## Local or structural

**Local.** Add a lock; mirror the pattern already used for `_build_proc` (graph builder).

## Fix plan (additive)

1. Add `_skein_build_proc_lock = threading.Lock()`.
2. Wrap the `proc is None or proc.poll() is not None` check + `subprocess.Popen` + dict update all inside one `with _skein_build_proc_lock:`.
3. Wrap the read in `skein_status` similarly.

## Lessons

Same root as 0001 (`_gpu_cache`) and 0003 (`_ingest_jobs`). Three locks added in one pass.
