# Bug 0008: Auth token logged in plaintext on startup

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18

---

## Symptom

`viewer.py`'s `__main__` block does:
```python
log.info(f"Bifröst on http://{BIND_HOST}:{PORT}/?token={TOKEN}")
```
The full URL — with token — goes to stdout and `logs/bifrost.log`. Anyone reading those (operator, systemd journal viewer, log-aggregation backend if one is added later) sees the secret.

## Expected

The startup log should print the URL with a masked token (e.g. `?token=***`) and tell the operator where to find the real token (in `.env`).

## Invariant violated

Law of Token Discipline (PROJECT_LAWS).

## Reproduction

`tail logs/bifrost.log` or `journalctl --user-unit bifrost`.

## Hypothesis

The convenience of having a clickable URL in the startup log was prioritized over secret hygiene. In a single-operator-on-laptop deployment this is mild; in any shared-machine or shipped-logs scenario it's a leak.

## Local or structural

**Local.** Mask the token in the log line.

## Fix plan (additive)

Print:
```
Bifröst on http://<host>:<port>/?token=***  (token in .env: VIEWER_TOKEN)
```

## Lessons

Convenience-vs-security tradeoffs default toward security in code that might be deployed differently than first envisioned. The mask is small enough to be free.
