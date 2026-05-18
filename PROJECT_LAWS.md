# PROJECT_LAWS.md — Bifröst
## *Immutable Rules for All Future Contributors (Human and AI)*

> These laws are not preferences. They are the conditions under which this
> project has agreed to exist. A change that breaks a law breaks the project.

---

## Law of the Sacred Source

The `documents` and `chunks` tables are owned by the Ingest project, not by
Bifröst. **Bifröst may read them; Bifröst may not write to them, modify them,
or schema-migrate them.** Bifröst's own tables are `skein_*` (managed by the
`skein-kg` library) and `kg_*` (legacy llama-extraction tables, kept for
comparison). Bifröst writes only to its own tables and to `.cache/`.

## Law of Fault Tolerance

Every endpoint is wrapped in `@safely(...)`. Every subsystem that touches an
external service (DB, Ollama, subprocess) is wrapped in try/except with a
`log.warning(...)` on failure. **Bifröst does not crash on a downstream
failure.** It degrades — reports the failure, keeps serving the rest.

## Law of No Silent Loading

No long-running operation may block the page without reporting progress.
Specifically: any operation that takes more than two seconds **must** be
reachable via a `/api/.../status` endpoint and **must** report a `stage` and
`progress` (0.0–1.0) field. The loader is required to display them.

## Law of Honest Logs

Use `logging`, never `print()`. Every endpoint logs warnings on failure with
a traceback. Background workers log progress at each major stage. Logs go to
both stdout (for systemd journal) and `logs/bifrost.log`.

## Law of Pool Discipline

There is **one** DB pool, opened lazily at first need, closed on shutdown. No
new `psycopg.connect(...)` calls outside `db_conn()`. The pool config is in
`get_pool()`; tune it there only.

## Law of Token Discipline

Every endpoint that exposes data requires `Depends(require_token)`. Token may
arrive via `?token=…` or `Authorization: Bearer …`. The viewer binds to the
tailscale interface, not localhost, but the token is the actual gate — do not
assume the network protects you.

## Law of Fingerprinted Caches

Caches live under `.cache/`. Every cache file is named with a data-derived
fingerprint (e.g. `graph_v2_22952_22952.json`). On rebuild, the writer must
prune cache files with the *same prefix and a different fingerprint*. To
introduce a breaking change in cache contents, bump the version prefix
(`v2_` → `v3_`); never edit an existing fingerprint scheme in place.

## Law of Async Heavy Work

Anything that touches UMAP, HDBSCAN, all-pairs cosine, or a multi-minute
Ollama batch runs in a background thread (in-process) or a detached
subprocess (out-of-process). It does **not** run in the request thread,
under any condition.

## Law of the Companion Repositories

`skein-kg` and `skry-kg` are external libraries with their own homes and
their own laws. Bifröst calls their *public* API. Bifröst does not reach into
their internals. If a Bifröst need would require modifying Skein or Skry, the
correct action is to add a method to their public API in their own repo, cut
a new version, and update the dep.

## Law of the Wyrd Designs

The architect (Volmarr) keeps weird, personal, and esoteric content in this
corpus by intent. Bifröst does not filter, censor, classify-as-problematic,
or visually de-emphasize any content. Every node is rendered with equal
dignity. The viewer is a faithful lens, never a judge.

## Law of Honest Failure

When a build crashes, the status endpoint reports `stage=failed` with the
error string. The frontend shows it in red on the loader. There is no fake
"still working" message that hides a failure. The user always knows the
truth.

## Rite of Preservation (commits)

Use `git commit` with a multi-line message: subject line under 70 chars, a
blank line, then a paragraph describing the *why*. Add
`Co-Authored-By: …` if pair-engineered with an AI craftsman.

## Rite of Return (reverts)

`git revert <sha>` makes a new commit that undoes a previous one — it does
not destroy history. Prefer this to `git reset --hard` on any commit that
has been pushed or is older than this session.

## Rite of Hot Reload

The viewer is a long-running service under systemd. After editing
`viewer.py`, restart with:

```
systemctl --user restart bifrost
```

After editing `static/index.html`, no restart is needed — refresh the page.
The static directory is served live by uvicorn.
