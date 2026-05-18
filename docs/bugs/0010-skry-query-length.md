# Bug 0010: `/api/skry` lacks query-length bound

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18

---

## Symptom

The `skry_lookup` endpoint validates `top_chunks` and `top_entities` ranges but not the length of `q`. An attacker (or buggy client) could POST a 10 MB query string; Skry would dutifully embed it via Ollama, which would consume GPU memory.

## Expected

Reject `len(q) > 10000` with HTTP 400.

## Invariant violated

Law of Input Validation.

## Fix plan (additive)

```python
if len(q) > 10000:
    raise HTTPException(status_code=400, detail="query too long (max 10000 chars)")
```

## Lessons

Every untrusted string from the wire deserves a max length, even when the rest of the pipeline "would handle it."
