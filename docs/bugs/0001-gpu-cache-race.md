# Bug 0001: `_gpu_cache` race condition

**Discovered:** 2026-05-18 by Auditor (Sólrún Hvítmynd)
**Status:** RESOLVED 2026-05-18 (additive: added `threading.Lock`)

---

## Symptom

The module-level `_gpu_cache` dict in `viewer.py` is read (`now - _gpu_cache["at"]`) and written (`_gpu_cache["at"] = ...`, `_gpu_cache["data"] = ...`) from the `/api/gpu` request handler without any lock. Under concurrent polling from multiple browser tabs (Bifröst's frontend polls every 2 s), two requests can both observe the cache as stale and both spawn `nvidia-smi` simultaneously, wasting CPU and producing a window where the dict is half-updated.

## Expected

Cache-hit logic should be atomic: either both fields are read consistently, or both are written consistently. Two concurrent stale-cache requests should fold into one nvidia-smi call.

## Invariant violated

PROJECT_LAWS — implicit *Law of Pool Discipline* extended to all shared mutable state. Any module-level dict that is written from request handlers must be guarded.

## Suspected domain

GPU snapshot endpoint (Realm of the Mind — `viewer.py` route layer).

## Reproduction

Open Bifröst in three browser tabs. They each poll `/api/gpu` every 2 s. With the polls naturally drifting in and out of phase, the read-then-update pattern is racy. Empirically observable as duplicate `nvidia-smi` invocations in `ps`; harder to observe a half-updated dict due to GIL atomicity of dict assignment, but the *cache-coalescing* invariant is broken.

## Hypothesis

Standard TOCTOU on module-level state. The check (`(now - _gpu_cache["at"]) < 1.5`) and the update are not atomic.

## Local or structural

**Local.** The endpoint is otherwise sound; the fix is a single `threading.Lock` plus `with` blocks.

## Fix plan (additive)

1. Add `_gpu_cache_lock = threading.Lock()` next to `_gpu_cache`.
2. Wrap the cache read in `with _gpu_cache_lock:` (returns the cached payload if fresh).
3. Wrap the cache write in `with _gpu_cache_lock:` after the nvidia-smi subprocess completes.
4. Do **not** hold the lock across the subprocess call — release it during the slow operation so the cache is briefly stale but the lock isn't held for 3 seconds.

## Verification

After fix: `pytest tests/test_invariants.py::test_gpu_cache_lock_held_at_writes` confirms the lock is acquired. Manual: three concurrent browsers polling, only one `nvidia-smi` per 1.5 s window in `ps` output.

## Lessons

The same pattern applies to every other module-level mutable dict in `viewer.py`: `_skein_build_proc`, `_ingest_jobs`, `_build_proc`. Sibling bug notes 0002 and 0003 cover those. All three got the same treatment in one pass.
