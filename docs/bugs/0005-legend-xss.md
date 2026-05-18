# Bug 0005: XSS via legend `innerHTML` of document titles

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18

---

## Symptom

`renderLegend()` builds the per-row HTML with `r.title` and `r.color` interpolated into an `innerHTML` template. `r.title` is sourced from `documents.title` (or from cluster name strings). A document with a title like `Notes <script>alert(1)</script>.md` (filenames can contain anything, and trafilatura can pick weird titles off the web) would XSS on viewer load.

## Expected

Titles displayed as text, never as HTML.

## Invariant violated

Same as 0004 — Law of Faithful Rendering.

## Suspected domain

Frontend legend renderer.

## Reproduction

```sql
INSERT INTO documents (source, title, content_type, hash)
VALUES ('test', '<img src=x onerror=alert(1)>', 'md', 'fakehash');
```
Trigger a graph rebuild; reload Bifröst. Legend tries to render the title; XSS fires.

## Hypothesis

Quotes in titles are escaped for the `title=` attribute (`r.title.replace(/"/g,'&quot;')`) but text content of the inner div is not escaped.

## Local or structural

**Local.** Reuse the `escapeHtml` helper from bug 0004.

## Fix plan (additive)

Replace `${r.title||''}` in the inner div with `escapeHtml(r.title||'')`; keep the `title="..."` attribute escaping unchanged (or also route through escapeHtml).

## Lessons

Same root as 0004 and 0006.
