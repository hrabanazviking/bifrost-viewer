# Bug 0004: XSS via toast `innerHTML` with user-derived data

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18

---

## Symptom

`static/index.html`'s `toast(...)` function builds HTML via `innerHTML` and interpolates `head`, `body`, and `url` directly. The `body` field for ingest-job toasts is the last line of the subprocess log (`s.log_tail` from `/api/ingest/jobs/{id}`). The `url` field is the user-supplied URL. If either contains HTML (e.g. an attacker-supplied URL like `https://example.com/x"><script>alert(1)</script>` or a log line containing `<` characters), the browser executes it.

## Expected

All user-derived strings displayed in the UI are inserted as text content, not HTML. No HTML interpretation.

## Invariant violated

Implicit *Law of Faithful Rendering* — Bifröst is a lens, not a script execution sandbox. The corpus content and operator inputs are display data, not executable code.

## Suspected domain

The Face of the World — `static/index.html`.

## Reproduction

In a browser dev console while Bifröst is open:
```js
toast({head: "TEST", body: "<img src=x onerror='alert(1)'>"})
```
Alert fires. Real-world trigger: paste a URL with HTML characters into the ingest field; if any line of trafilatura's output echoes those characters, the resulting toast XSSes the user.

## Hypothesis

`innerHTML` was used to allow the `head` styling. The risk: any user-derived field in the same template inherits the HTML interpretation.

## Local or structural

**Local** — small refactor of one function.

## Fix plan (additive)

1. Add an `escapeHtml(s)` helper that maps `& < > " '` to entities.
2. In `toast(...)`, build the inner HTML with escaped values for `head`, `body`, `url`.
3. Keep the static layout HTML (the `<button class="x">` etc.) inline since those are not user-derived.

## Lessons

Three separate XSS surfaces (this + 0005 legend + 0006 node label) share a root cause: `innerHTML` with interpolation of user-derived strings. A grep for `innerHTML` in the file should be in the Auditor's standard pass forever.
