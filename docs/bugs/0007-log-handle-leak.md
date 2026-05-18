# Bug 0007: Subprocess log file handles never explicitly closed

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18

---

## Symptom

Three call sites open a log file with `log_file = open(log_path, "w")` and pass it to `subprocess.Popen(stdout=log_file)`. The handle is never explicitly closed in the parent. Python's GC eventually reclaims it, but under sustained ingestion (many URL ingest jobs in a single session) file descriptors accumulate in the viewer process.

## Expected

The parent closes its copy of the file handle immediately after `Popen` returns. The subprocess inherits its own dup'd handle from `Popen`.

## Invariant violated

Law of Fault Tolerance (implicit) — resource exhaustion is a class of failure to guard against.

## Suspected domain

Subprocess-spawning endpoints: `kick_off_build`, `skein_build`, `ingest_url`.

## Reproduction

Trigger 100 URL ingests in a session. `lsof -p <viewer pid> | wc -l` grows by ~100. With the default ulimit (1024) the viewer eventually fails to open new files.

## Hypothesis

`subprocess.Popen` dup's the fd for the child. The parent's reference is held alive by the local `log_file` variable, which is held alive as long as the function's stack frame exists — actually no, the function returns immediately after Popen. So the only thing keeping the parent's handle open is GC laziness on the file object. Still — explicit close is the right thing.

## Local or structural

**Local.** Add explicit `log_file.close()` after `Popen` in each of the three call sites.

## Fix plan (additive)

After each `subprocess.Popen(..., stdout=log_file, ...)`:
```python
log_file.close()
```
The subprocess's copy is unaffected (it has its own dup'd fd).

## Lessons

Subprocess fd handling is one of those things where "it works in practice" hides a slow leak. Explicit close is cheap insurance.
