# Bifröst

> *the shimmering bridge between the realm of raw knowledge and the realm of human sight*

Bifröst is a self-hosted, browser-based **3D viewer for a local pgvector knowledge base**.
It takes any Postgres database with the standard `documents` + `chunks(embedding vector)`
schema and projects it into a navigable galaxy: every chunk a glowing node,
every cosine-similarity edge a glowing thread, every document a constellation.

It's the third in a family of small Norse-themed tools that operate over the
same database, each with one job:

| | |
|---|---|
| **[Bifröst](https://github.com/hrabanazviking/bifrost-viewer)** | the bridge — 3D visualization, search, navigation |
| **[Skein](https://github.com/hrabanazviking/skein-kg)** | the loom — builds a knowledge graph from embeddings without LLM-per-chunk extraction |
| **[Skry](https://github.com/hrabanazviking/skry-kg)** | the seer — query-time entity-neighborhood projection |

---

## What you get

- **Chunk-level constellation** — every chunk in your corpus as a 3D node, UMAP-projected, colored by source document, edges drawn by cosine similarity, hover for snippet, click to read the full chunk text.
- **Document-level overview** — aggregate one node per document; cross-doc similarity edges show which sources talk to which.
- **Entity-level graph (via Skein)** — once you've built the Skein KG, switch to ENTITIES mode and see typed-relation edges between named things (Odin —[wields]→ Gungnir).
- **Hybrid search** with optional HyDE — semantic + keyword fused via reciprocal-rank-fusion; HyDE generates a hypothetical answer first and embeds *that*, which often beats raw query embedding for vague questions.
- **Skry mode** — type an entity name, get an instant ranked list of co-occurring entities with evidence chunks.
- **Semantic path-finder** — shift+click any two chunks to render the shortest similarity-graph path between them.
- **LLM cluster naming** — HDBSCAN topic clusters, named on-demand by a local llama.
- **GPU gauge** — live nvidia-smi readout in the corner so you can watch utilization, VRAM, temp, and power as builds run.
- **URL ingest** — paste a URL into the top-right field and the page fetches it via [trafilatura](https://trafilatura.readthedocs.io/), chunks it, embeds it, and adds it to the corpus.
- **Async builds** — heavy graph rebuilds run in a subprocess so the server stays responsive. The loader shows live stage + progress; no silent hangs.

## Aesthetic

Cyber-Viking. Deep space-blue background, glowing neon rainbow on the title (literally Bifröst the rainbow bridge), HSL-distributed hues for entity kinds, glass-blur panels with cyan borders. The corpus deserves drama.

---

## Prerequisites

- **Python 3.13+**
- **Postgres 14+** with the `vector` and `pg_trgm` extensions, and tables that match the standard ingest layout:
  ```sql
  documents (id, title, content_type, source, ...)
  chunks    (id, document_id, chunk_index, text, embedding vector(N), tsv tsvector, ...)
  ```
  (A typical ingest layout that produces these tables: [pgvector docs](https://github.com/pgvector/pgvector). The companion ingest project that originally generated this schema isn't published, but any pipeline that fills those tables will work.)
- **[uv](https://github.com/astral-sh/uv)** for dep management
- **[Ollama](https://ollama.com/)** running locally (or on your tailnet) with at minimum an embedding model (e.g. `nomic-embed-text`). A chat model (e.g. `llama3.2:3b`) is needed for HyDE search and cluster naming.
- **Optional but recommended:** `skein-kg` and `skry-kg` cloned as siblings (`../skein-kg`, `../skry-kg`) for entity-graph features.

## Install

```bash
git clone https://github.com/hrabanazviking/bifrost-viewer ~/ai/ingest-viewer
git clone https://github.com/hrabanazviking/skein-kg     ~/ai/skein-kg
git clone https://github.com/hrabanazviking/skry-kg      ~/ai/skry-kg

cd ~/ai/ingest-viewer
cp .env.example .env
$EDITOR .env            # set VIEWER_TOKEN to a real secret, point DB/Ollama at your hosts
uv sync
uv run viewer.py
```

Open **http://localhost:8731/?token=YOUR_TOKEN_HERE** in a browser.

## Run as a systemd user service

```bash
mkdir -p ~/.config/systemd/user
cp systemd/bifrost.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now bifrost.service
```

`Restart=on-failure` + a memory ceiling keep it well-behaved on laptops.

---

## Architecture & doctrine

Bifröst is built under the **Mythic Engineering** convention. See:

- [`SYSTEM_VISION.md`](SYSTEM_VISION.md) — the soul: what this exists to do
- [`DOMAIN_MAP.md`](DOMAIN_MAP.md) — realm boundaries and forbidden crossings
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — bones, rivers of flow, key connectors
- [`PROJECT_LAWS.md`](PROJECT_LAWS.md) — immutable rules (fault tolerance, no silent hangs, sacred source, etc.)
- [`static/README_AI.md`](static/README_AI.md) — notes for anyone editing the frontend

The short version of the laws:
- The bridge shall **never** block in silence — every long operation reports live progress.
- The bridge shall **never** mutate the source `documents` or `chunks` tables.
- All heavy work runs **out-of-process** so the FastAPI server stays responsive.
- Every endpoint is wrapped in fault-tolerant `@safely(...)`.
- All logging via the `logging` module — no bare `print()`.

## Endpoints (summary)

```
GET  /                              static page
GET  /api/health                    liveness + db/ollama/cache check
GET  /api/graph?level=chunk|document   cached graph payload
GET  /api/graph/build-status        live progress of subprocess builder
POST /api/graph/build               trigger a rebuild
GET  /api/chunk/{id}                full chunk text
GET  /api/search?q=…&hyde=0|1       hybrid search (+ HyDE toggle)
GET  /api/path?a=ID&b=ID            shortest path through similarity graph
GET  /api/cluster-names             LLM-named HDBSCAN clusters
GET  /api/skein/status              Skein KG state
POST /api/skein/build               trigger a Skein rebuild
GET  /api/skein/graph               entity graph (3D-ready)
GET  /api/skry?q=…                  query-time entity neighborhood
POST /api/ingest/url                start a URL ingest job
GET  /api/ingest/jobs/{job_id}      job status
GET  /api/gpu                       nvidia-smi snapshot
```

All endpoints require a token via `?token=…` or `Authorization: Bearer …`.

---

## Status

Co-built by [Volmarr Wyrd](https://github.com/hrabanazviking) and Claude during a single session in May 2026. The methods Skein and Skry were invented in the same session and live in their own repos. Open to becoming a real, polished project if useful to others. PRs welcome.

## License

MIT
