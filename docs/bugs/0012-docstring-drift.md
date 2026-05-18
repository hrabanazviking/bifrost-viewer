# Bug 0012: Module docstring's Endpoints list is stale

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18

---

## Symptom

`viewer.py`'s module docstring lists endpoints, but several added later are missing:
- `POST /api/ingest/url`
- `GET /api/ingest/jobs/{job_id}`
- `GET /api/ingest/jobs`
- `GET /api/gpu`

(And the legacy `GET /api/kg/status` is present in code but not in the docstring.)

## Expected

Every registered route appears in the docstring.

## Invariant violated

Implicit: documentation must reflect code.

## Fix plan (additive)

Add the missing endpoints to the docstring. No code change.

## Lessons

The Scribe's job at session close includes reading the routes block and the docstring side-by-side.
