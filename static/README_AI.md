# static/ — README_AI.md

This directory is **The Face of the World** (see `../DOMAIN_MAP.md`). It
contains everything the browser sees.

## What's here

- `index.html` — the entire viewer UI. Single file: HTML + CSS + JS. No build
  step, no bundler, no framework. It is intentionally one file so that any
  contributor (human or AI) can read and reason about it in one pass.

## What it knows

- Browser APIs (`fetch`, `URLSearchParams`, the DOM).
- The shape of `/api/*` responses (defined in `../viewer.py`).
- `three.js` (loaded from CDN) for 3D scene primitives.
- `3d-force-graph` (loaded from CDN) for force-directed layout.
- `three-spritetext` (loaded from CDN) for cluster labels.

## What it does NOT know

- The database schema.
- The cache layout.
- Ollama. (All LLM interaction goes through `/api/search?hyde=1` and friends.)
- Any secret beyond the URL-supplied `?token=`.

## How to make changes

1. Edit `index.html`. Save. **Refresh the browser.** No restart required —
   uvicorn serves the static directory live.
2. If you find yourself wanting to add a build step, a bundler, or a
   JavaScript framework: don't. Add a `<script>` tag for a CDN-loaded library
   if you genuinely need one, and document it here.
3. If you need new data from the server: add the endpoint in `../viewer.py`
   first (with `@safely` wrapper, in the same style as existing routes),
   document it in the module docstring, then call it from here.

## The async build contract

This frontend depends on a specific contract with the backend:

- `GET /api/graph?level=chunk` returns `200 OK` with the payload **or**
  `202 Accepted` with `{pending: true, ...}` if no cache exists yet.
- On `202`, the frontend calls `/api/graph/build-status` in a polling loop
  and updates the loader's `.ghost` element with the current `stage` and
  `progress` percentage.
- The polling loop exits when `cache_exists && !running`.
- If `error` is non-null, the loader turns red and shows the error verbatim.

This contract is enforced by `waitForChunkGraphBuild()` in `index.html` and
the corresponding backend logic in `_do_build()` in `../viewer.py`. Changing
one side requires changing the other in lockstep.

## The Skry contract

When the SKRY checkbox is checked, `runSearch()` calls `/api/skry` instead of
`/api/search`. The result is displayed in the side panel rather than pulsing
nodes in the graph. If the user is also in the ENTITIES level, matching
entities get highlighted in the 3D view.

## The cluster-naming contract

Cluster names are lazily computed by the backend on first request to
`/api/cluster-names`. The frontend shows a button that triggers the request
and replaces `Cluster <id>` labels with the LLM-generated names once they
arrive. Names are cached server-side keyed by the chunk-graph fingerprint.

## Aesthetics

The visual language is **cyber-Viking**: deep space-blue background, neon
rainbow gradient for the BIFRÖST title (mirroring the actual rainbow bridge),
HSL-distributed hues for entity kinds and document colors, panel-style
glass-blur surfaces with cyan borders. Keep this. Sparkly, glowing,
constellation-like. The corpus deserves drama.
