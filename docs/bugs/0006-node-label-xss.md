# Bug 0006: XSS via 3D node-label `innerHTML` of names and snippets

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18

---

## Symptom

`Graph.nodeLabel(...)` returns an HTML string that 3d-force-graph injects into the hover tooltip. The string contains `n.name` (Skein entity name), `n.doc_title`, `n.kind`, and `n.snippet` — all user-derived. Any HTML in those fields executes when the user hovers over the node.

The snippet already does `(n.snippet||'').replace(/</g, "&lt;")` (one-character escape) but the *other* fields (name, doc_title, kind) do not.

## Expected

All four fields HTML-escaped (and the partial escape on snippet promoted to full escape).

## Invariant violated

Same as 0004, 0005 — Law of Faithful Rendering. Plus: the canonical Mythic Engineering RULES.AI implicit "no execution of corpus content" principle.

## Suspected domain

Frontend 3D node label callback in `loadGraph()`.

## Reproduction

Have a Skein entity named `Test <img src=x onerror=alert(1)>`. Switch to ENTITIES level. Hover the node. XSS fires.

## Hypothesis

`innerHTML` of a templated string with multiple interpolated fields; partial escape on one field, none on the others.

## Local or structural

**Local.** Apply `escapeHtml` consistently.

## Fix plan (additive)

Escape every interpolated field via `escapeHtml(...)`. Remove the now-redundant `.replace(/</g, "&lt;")` on snippet (the helper covers it).

## Lessons

Three XSS surfaces, one helper. The Auditor's checklist now includes: "every `innerHTML` site is reviewed and every interpolation uses `escapeHtml` unless explicitly justified."
