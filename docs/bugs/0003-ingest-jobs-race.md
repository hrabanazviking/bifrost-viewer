# Bug 0003: `_ingest_jobs` race condition

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18

---

## Symptom

`_ingest_jobs` dict is written from `/api/ingest/url` and read from `/api/ingest/jobs/{id}` and `/api/ingest/jobs` without consistent locking. The lock `_ingest_lock` exists and IS used in `_ingest_job_state` and one write — but the **list/iteration** in `ingest_jobs_list` iterates outside the lock and could observe a dict mid-mutation.

## Expected

All reads and writes of `_ingest_jobs` happen under `_ingest_lock`.

## Invariant violated

Pool-discipline extension (any module-level shared dict must be lock-protected on read AND write).

## Suspected domain

URL ingest API (Realm of the Mind).

## Reproduction

A POST to `/api/ingest/url` runs at the same moment another browser is polling `/api/ingest/jobs`. Python's dict iteration is not safe under concurrent mutation; can raise `RuntimeError: dictionary changed size during iteration` on extreme cases.

## Hypothesis

`ingest_jobs_list` snapshots keys inside the lock but then calls `_ingest_job_state(i)` for each id outside it. Between the snapshot and the per-id call, an entry could be evicted (currently we don't evict, but the pattern is fragile).

## Local or structural

**Local.** Acquire the lock once around the whole list construction; or accept that per-id calls re-acquire (fine since `_ingest_job_state` already locks).

## Fix plan (additive)

Audit `_ingest_job_state` to ensure all field reads from the job dict happen inside its lock acquisition (currently they do). Tighten `ingest_jobs_list` to do all work inside the lock by inlining the state-build, OR document that the per-id re-acquisition is safe.

Choice taken: inline the state-build into a single lock scope in `ingest_jobs_list`.

## Lessons

Race conditions on module-level mutable state are easy to miss because they don't manifest in single-user testing. The Auditor's job is to find them by reading the code, not by running it.
