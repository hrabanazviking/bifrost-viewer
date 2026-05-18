# Bug 0009: `POST /api/ingest/url` accepts untyped `dict` payload

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18

---

## Symptom

`ingest_url(payload: dict, ...)` — FastAPI doesn't validate the shape; a malformed body (`{}`, `{"url": null}`, `{"url": 123}`) gets through to the handler. The defensive `(payload.get("url") or "").strip()` masks some cases but accepts e.g. `{"url": 123}` → coerced to string `"123"` → bogus request to the ingest subprocess.

## Expected

A Pydantic `IngestRequest` model with `url: HttpUrl` (or at minimum `url: str`) so FastAPI rejects malformed bodies with a 422 + field-level error.

## Invariant violated

Law of Input Validation — every endpoint validates its inputs and returns clear errors.

## Reproduction

```bash
curl -X POST -H "Content-Type: application/json" -d '{"url": 123}' .../api/ingest/url
```
Currently: 200 with a job ID; subprocess fails.
Desired: 422 with `{"detail": [{"loc": ["body", "url"], "msg": "str type expected", ...}]}`.

## Local or structural

**Local.** Define a Pydantic model and update the signature.

## Fix plan (additive)

```python
from pydantic import BaseModel

class IngestUrlRequest(BaseModel):
    url: str

@app.post("/api/ingest/url")
@safely("ingest_url")
def ingest_url(payload: IngestUrlRequest, _=Depends(require_token)):
    url = payload.url.strip()
    ...
```
Keep the http(s) scheme check (Pydantic's `HttpUrl` is stricter but would also accept ftp etc. — explicit check is clearer).

## Lessons

Pydantic models are the FastAPI-idiomatic way to validate bodies. `payload: dict` is a smell.
