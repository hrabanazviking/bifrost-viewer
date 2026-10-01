---

![https://raw.githubusercontent.com/hrabanazviking/bifrost-viewer/refs/heads/main/336860c7-24fa-4e82-80ea-933c5f3a67c5.jpeg](https://raw.githubusercontent.com/hrabanazviking/bifrost-viewer/refs/heads/main/336860c7-24fa-4e82-80ea-933c5f3a67c5.jpeg)

---

# Bifröst

## Detailed manuals

- [Second-brain user and operations manual](SECOND_BRAIN_MANUAL.md) — all components,
  daily use, GPU checks, services, backup/restore and moving machines.
- [Bifröst technical manual](TECHNICAL_MANUAL.md) — installation, configuration,
  browser controls, HTTP routes and build recovery.
- [Security and outside-AI manual](security/TECHNICAL_MANUAL.md) — email recovery,
  editable settings, scoped keys, safe submissions, quotas and transport.
- [Document ingestion manual](ingest/TECHNICAL_MANUAL.md) — trusted CLI, inbox formats,
  retained inputs, retry state and first-time schema setup.

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

![https://raw.githubusercontent.com/hrabanazviking/bifrost-viewer/refs/heads/main/Screenshot_20260518_173244.png](https://raw.githubusercontent.com/hrabanazviking/bifrost-viewer/refs/heads/main/Screenshot_20260518_173244.png)

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
- **Safe AI access and ingestion** — issue expiring read/append keys; a durable bounded queue adds text or public web URLs using an append-only database role.
- **Owner recovery** — verify a configurable email address and exchange a short-lived, single-use emailed code for a replacement owner credential. TLS SMTP settings stay private.
- **Async builds** — heavy graph rebuilds run in a subprocess so the server stays responsive. The loader shows live stage + progress; no silent hangs.

## Aesthetic

Cyber-Viking. Deep space-blue background, glowing neon rainbow on the title (literally Bifröst the rainbow bridge), HSL-distributed hues for entity kinds, glass-blur panels with cyan borders. The corpus deserves drama.

---

## Prerequisites

- **Linux with Bubblewrap (`bwrap`) and user namespaces** for isolated HTTP ingestion. It fails closed if isolation is unavailable.
- **Python 3.13+**
- **Postgres 14+** with the `vector` and `pg_trgm` extensions, and tables that match the standard ingest layout:
  ```sql
  documents (id, title, content_type, source, ...)
  chunks    (id, document_id, chunk_index, text, embedding vector(N), tsv tsvector, ...)
  ```
  The bundled [ingest component](ingest/README.md) includes the CLI, schema and
  separate frozen parser runtime. Any pipeline that fills these tables also works.
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
$EDITOR .env            # point DB/Ollama at your hosts; leave migration token blank for a new install
uv sync
uv run viewer.py
```

Run `uv run --frozen python scripts/open_brain.py` or use the Bifröst Second Brain desktop launcher. It opens with the strong owner credential from private user state. Open **Security & recovery** to configure SMTP, verify the recovery address, and issue AI keys. The optional old `VIEWER_TOKEN` becomes read-only for one day after migration.

See [security/README_AI.md](security/README_AI.md) for append-role setup, email, HTTPS, quotas and portable state.
See [ingest/README.md](ingest/README.md) to install document/URL ingestion and retain
an existing private inbox.

## Run as a systemd user service

```bash
mkdir -p ~/.config/systemd/user
cp systemd/bifrost.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now bifrost.service
```

`Restart=on-failure` + a memory ceiling keep it well-behaved on laptops.

---

![https://raw.githubusercontent.com/hrabanazviking/bifrost-viewer/refs/heads/main/2045f97c-0b92-4c8b-aecb-904f69ccdc3c.jpeg](https://raw.githubusercontent.com/hrabanazviking/bifrost-viewer/refs/heads/main/2045f97c-0b92-4c8b-aecb-904f69ccdc3c.jpeg)

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
- Display/search/layouts shall **never** update or delete source `documents` or
  `chunks`; intentional additions belong to the separate ingest boundary.
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

Data API routes require a scoped token; prefer `Authorization: Bearer …` over
compatible query tokens. Static login/security pages and the bounded recovery
routes are public. Administrative builds/settings require owner access. See the
[complete security contract](security/INTERFACE.md).

---

## Status

Co-built by [Volmarr Wyrd](https://github.com/hrabanazviking) and Claude during a single session in May 2026. The methods Skein and Skry were invented in the same session and live in their own repos. Open to becoming a real, polished project if useful to others. PRs welcome.

---

![https://raw.githubusercontent.com/hrabanazviking/bifrost-viewer/refs/heads/main/MIT_license_Rune_Forge_AI.jpeg](https://raw.githubusercontent.com/hrabanazviking/bifrost-viewer/refs/heads/main/MIT_license_Rune_Forge_AI.jpeg)

---

## License

MIT License

Copyright (c) 2026 Volmarr Wyrd

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## ☕ Support the Project

If you enjoy my open-source projects and want to help support continued development, research, testing, and experimentation, you can leave a tip through PayPal:

**[Support my work on PayPal.Me](https://www.paypal.com/paypalme/volmarrwyrd)**

Support is always appreciated, but never required. Using, sharing, testing, contributing to, or starring the projects helps too. 🖤⚙️ᚱ

---

![https://raw.githubusercontent.com/hrabanazviking/bifrost-viewer/refs/heads/main/IMG_0666.jpeg](https://raw.githubusercontent.com/hrabanazviking/bifrost-viewer/refs/heads/main/IMG_0666.jpeg)

---

![https://raw.githubusercontent.com/hrabanazviking/bifrost-viewer/refs/heads/main/IMG_0665.jpeg](https://raw.githubusercontent.com/hrabanazviking/bifrost-viewer/refs/heads/main/IMG_0665.jpeg)

---




## Resilience update (September 2026)

Open the desktop launcher or http://127.0.0.1:8731 and enter your existing access
token. Document overview loads first; CHUNKS retains full detail. Both layouts
report progress. Database outages and corrupt caches recover through periodic
maintenance. Graph neighbor calculations use row blocks and document edges are
sparse, reducing memory and browser load. Semantic-search outages fall back to
clearly identified keyword matches. See [operations](docs/operations.md).
