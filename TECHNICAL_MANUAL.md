# Bifröst technical manual

Verified against source on 2026-10-01. For the connected system and backup/restore
procedures, start with [SECOND_BRAIN_MANUAL.md](SECOND_BRAIN_MANUAL.md).
This guide covers the viewer; [ingest](ingest/TECHNICAL_MANUAL.md) owns source
insertion and [security](security/TECHNICAL_MANUAL.md) owns credentials/admission.

## 1. Runtime and folder map

| File or directory | Responsibility |
|---|---|
| `viewer.py` | FastAPI routes, DB pool, search, maintenance and build supervision |
| `local_server.py` | Listener sockets, optional native TLS and Uvicorn configuration |
| `graph_builder.py` | Separate-process chunk/document layout and clustering |
| `inference.py`, `inference.json` | Independent bounded chat routing and policy |
| `runtime_support.py` | Validated/atomic runtime helpers |
| `kg_extract.py` | Legacy/experimental extraction support; not needed for ordinary Skein use |
| `static/` | Viewer and owner security browser interface |
| `security/` | Auth state, gateway, email recovery and durable API worker |
| `ingest/` | Canonical parser with its own frozen dependency runtime |
| `scripts/open_brain.py` | Local owner launcher |
| `scripts/watch_inbox.py` | Trusted inbox supervisor |
| `scripts/setup_append_role.py` | Owner-run restricted DB account provisioning |
| `systemd/` | User-service templates |
| `.cache/` | Disposable layouts/build status, unless relocated |
| `logs/` | Private local build logs, unless relocated |
| `tests/` | Behavioral, invariant and security regressions |

The root runtime requires Python 3.13+ and uv. The dependency configuration expects
`../skry-kg` and `../skein-kg` to exist. The parser runtime is separate so its heavy
format dependencies do not enter the web process. Secure API ingestion requires
Linux Bubblewrap and working user namespaces. Remote browser/API clients can use
other operating systems; the server's hardened worker has a Linux boundary.

## 2. Existing installation: start and inspect

```bash
cd "$HOME/ai/ingest-viewer"
systemctl --user start bifrost.service
uv run --frozen python scripts/open_brain.py
systemctl --user status bifrost.service --no-pager
```

A manual foreground server, when the service is stopped, is:

```bash
uv run --frozen viewer.py
```

Do not run the service and foreground server on the same address/port. The launcher
first starts the user service and then reads the current private owner token.
Graph readiness is independent of listener readiness.

## 3. Fresh installation

Prerequisites: PostgreSQL with pgvector/pg_trgm available, a database owner account,
Ollama with compatible models, uv/Python, and Bubblewrap for HTTP writes. Create
the sibling layout before syncing Bifröst:

```bash
mkdir -p "$HOME/ai"
git clone https://github.com/hrabanazviking/bifrost-viewer "$HOME/ai/ingest-viewer"
git clone https://github.com/hrabanazviking/skein-kg "$HOME/ai/skein-kg"
git clone https://github.com/hrabanazviking/skry-kg "$HOME/ai/skry-kg"
cd "$HOME/ai/ingest-viewer"
cp .env.example .env
chmod 600 .env
uv sync --frozen
uv sync --frozen --project ingest
```

Edit `.env` before starting. Create the source schema only for a new empty database
using the [ingest procedure](ingest/TECHNICAL_MANUAL.md#3-first-time-database-setup).
Configure a trusted ingest dotenv and matching model. Existing databases should
be backed up and inspected, not reinitialized. Leave `VIEWER_TOKEN` blank for a
new installation; first startup creates strong owner access in private state.

Provision the restricted worker with the viewer stopped:

```bash
uv run --frozen python scripts/setup_append_role.py
```

This requires the owner DB role to create/manage the restricted role. It rotates
that role's password and writes private worker settings. It does not initialize
source tables. If the database lives elsewhere, review the security manual before
provisioning; the default worker is TCP to `127.0.0.1`, not an owner Unix socket.

For service installation:

```bash
mkdir -p "$HOME/.config/systemd/user"
cp systemd/bifrost.service "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now bifrost.service
```

Edit the service paths if the checkout is not `~/ai/ingest-viewer`. Installing the
watcher is separate; its template assumes private config/inbox at `~/ai/ingest`.
Do not enable it before those paths are configured.

## 4. Configuration reference

Settings come from the root `.env` and process environment; existing environment
values take precedence. `INGEST_ENV_FILE` points to the trusted parser's separate
configuration. Do not shell-source a dotenv as a substitute for the loader.
Use real absolute values for relocated state paths, rather than assuming every
path setting expands `~`. Restart the relevant service after settings changes.

| Setting | Default/example | Effect |
|---|---|---|
| `VIEWER_DB_URL` | `postgresql:///knowledge` | Owner/viewer DB connection; private secret if password-bearing |
| `VIEWER_OLLAMA_URL` | `http://localhost:11434` | Model service; current installation uses Gungnir |
| `VIEWER_EMBED_MODEL` | `nomic-embed-text` | Must match the corpus embedding space |
| `VIEWER_CHAT_MODEL` | `llama3.2:3b` | HyDE and cluster names |
| `VIEWER_CHAT_BACKEND` | `ollama` | Select Ollama or authenticated local Aesir chat |
| `VIEWER_CHAT_URL` | Backend-dependent origin | Chat only; does not change embedding origin |
| `VIEWER_CHAT_API_KEY_FILE` | Required for Aesir | Private current-owner regular key file |
| `VIEWER_CHAT_FALLBACK` | `none` | Explicit Ollama fallback for an Aesir primary |
| `VIEWER_INFERENCE_POLICY` | root `inference.json` | Bounded admission, HTTP and circuit policy |
| `VIEWER_TOKEN` | blank on new install | Optional one-day read-only migration credential |
| `VIEWER_BIND_HOST` | `127.0.0.1` | Main bind; explicitly configured Tailscale address for private remote use |
| `VIEWER_LOOPBACK_HOST` | `127.0.0.1` | Local listener/launcher fallback |
| `VIEWER_PORT` | `8731` | Listening port |
| `VIEWER_DB_TIMEOUT` | `5` | Connection/pool wait control |
| `VIEWER_RECOVERY_INTERVAL` | `30` | Maintenance interval in seconds |
| `VIEWER_BUILD_RETRY_DELAY` | `120` | Failed layout retry cooldown in seconds |
| `VIEWER_BUILD_STALL_AFTER_SEC` | `600` | No-progress watchdog threshold |
| `VIEWER_EDGE_TOP_K` | `4` | Chunk similarity neighbors |
| `VIEWER_EDGE_MIN_SIM` | `0.55` | Similarity threshold |
| `VIEWER_EDGE_BLOCK_SIZE` | `256` | Row-block calculations; lower values reduce peak memory |
| `VIEWER_HDBSCAN_MIN_CLUSTER` | `8` | Minimum cluster size |
| `VIEWER_EDGE_LABEL_TERMS` | `4` | Terms used in similarity edge labels |
| `VIEWER_CACHE_DIR` | project `.cache/` | Disposable graph/build cache location |
| `VIEWER_LOG_DIR` | project `logs/` | Build logs location |
| `VIEWER_SECURITY_DIR` | XDG state `bifrost/` | Private durable auth/mail/queue state |
| `VIEWER_API_INGEST_ENV_FILE` | private state `ingest.env` | Restricted API worker configuration |
| `VIEWER_API_DB_HOST` | `127.0.0.1` | Owner provisioning script's restricted TCP database host |
| `VIEWER_RECOVERY_EMAIL` | unset | Initial unverified recipient seed; verified settings are managed in the UI |
| `VIEWER_INGEST_PROJECT_DIR` | bundled `ingest/` | Canonical API parser runtime location |
| `INGEST_ENV_FILE` | trusted private dotenv | Trusted CLI/watch config and provisioning model defaults |
| `VIEWER_ALLOWED_HOSTS` | explicit additional hosts | Approved DNS/Host values |
| `VIEWER_ALLOWED_ORIGINS` | explicit HTTPS origins | Browser client origins; no wildcard |
| `VIEWER_TLS_CERT`, `VIEWER_TLS_KEY` | unset | Both required for native TLS |
| `VIEWER_LIMITS_FILE` | unset | Reviewed partial override of security defaults |

Security limits, remote transport and email settings are covered in the
[security manual](security/TECHNICAL_MANUAL.md). Graph tuning affects resource
usage and readability; it does not truncate the source corpus. Force a graph
rebuild after deliberately changing its tuning.

## 5. Browser workflow

- **DOCS**: compact overview, one node per document; default opening view.
- **CHUNKS**: passage nodes, full text inspection, similarity paths.
- **ENTITIES**: derived Skein graph and evidence; requires a successful Skein build.
- **BY DOC / BY CLUSTER**: presentation modes, not source modifications.
- **HYDE**: chat-assisted query expansion followed by retrieval.
- **SKRY**: query-time entity neighborhoods instead of ordinary search hits.
- **ADD URL**: queue a safe public page using owner/append permission.
- **rebuild graph**: force a disposable layout refresh; owner only.
- **BUILD SKEIN**: launch the sibling project build; owner only.
- **NAME CLUSTERS**: on-demand chat naming; owner only.
- **security & recovery**: owner mail, address and delegated-key administration.

Read-only keys can explore the corpus but cannot run owner controls. Browser
credentials stay in memory, so reload requires the launcher or sign-in again.
The viewer has no browser file-upload or bulk database-delete function.

## 6. HTTP reference

Use bearer headers; compatible query tokens can leak into copied URLs and should
not be a new integration's authentication mechanism. See the security guide for
copyable request examples without putting a key into shell history.

| Route | Permission | Inputs/behavior |
|---|---|---|
| `GET /api/auth/me` | read | Identity ID and scopes, never the credential |
| `GET /api/capabilities` | read | Active limits and append routes |
| `GET /api/health` | read | DB/model/cache/build health |
| `GET /api/graph` | read | `level=chunk` or `level=document`; 202 while building |
| `GET /api/graph/build-status` | read | Stage/progress/current fingerprint |
| `POST /api/graph/build` | admin | `force=true` by default |
| `POST /api/refresh` | admin | Forced layout refresh and cluster-name invalidation |
| `GET /api/chunk/{id}` | read | Text, document/source information; 404 if absent |
| `GET /api/search` | read | `q`, `k=1..100` (default 12), `hyde=0/1`; query max 10,000 chars |
| `GET /api/path` | read | Integer `a`/`b` chunk IDs; 409 if graph unavailable |
| `GET /api/cluster-names` | admin | Uses configured chat model/cache |
| `GET /api/skein/status` | read | Build state, counts and last build |
| `POST /api/skein/build` | admin | Starts sibling build, reports already-running state |
| `GET /api/skein/graph` | read | Entity layout; 202 pending, 503 retryable failure |
| `GET /api/skry` | read | `q`, `top_chunks=1..500`, `top_entities=1..200` |
| `POST /api/ingest/text`, `/api/ingest/url` | ingest | Queue accepted payload; poll returned job ID |
| `GET /api/ingest/jobs`, `/api/ingest/jobs/{id}` | read | Owner sees all; delegated key sees its jobs |
| `GET /api/gpu` | read | Cached NVIDIA snapshot or unavailable state |

Search responses include `search_mode=hybrid|keyword`, `degraded`, `hyde_used`,
`hyde_doc` and `hits`. When embeddings are unavailable, the web route can return
keyword hits with `degraded=true`; Skry and CLI semantic operations do not promise
that same fallback. Retrieve actual chunks for evidence rather than interpreting
a similarity score or generated label as proof.

## 7. Builds, caches and recovery behavior

Layouts run in child processes and publish JSON atomically. Chunk similarity
calculation uses blocks; document edges are sparse. Last-good files remain on
disk during a replacement build. Missing/corrupt/stale caches can rebuild;
database outages do not require recreating the whole installation.

The source fingerprint uses row counts/max IDs. A new document/chunk changes it;
an in-place edit may not. Maintenance checks every configured recovery interval,
retries failed work after cooldown and terminates stalled layout processes.
Do not erase `.cache` as the first troubleshooting action; inspect build status
and logs, then use the owner rebuild control if necessary.

Skein's derived tables and its 3D entity layout are different layers: a good
Skein graph can exist while the entity layout is still computing. Skein rebuilding
is deliberately initiated by an owner, not automatically on every small append.

## 8. Logs, tests and maintenance

```bash
journalctl --user -u bifrost.service -n 100 --no-pager
uv run --frozen pytest -q
git status --short
```

Build-specific logs live in the configured log directory; API worker logs live
in private security state and are not returned raw to clients. Treat both as
sensitive. Tests may use temporary state and test doubles; live health and sample
reads are needed separately. Do not deliberately append a test document unless
you intend to retain it in your knowledge base.

Use the [stack backup/restore and migration procedures](SECOND_BRAIN_MANUAL.md).
Source updates do not back up the database. Never publish `.env`, private security
state, retained inbox data or credential-bearing logs. For implementation contracts
and maintenance constraints, see [INTERFACE.md](INTERFACE.md),
[PROJECT_LAWS.md](PROJECT_LAWS.md) and [docs/operations.md](docs/operations.md).

Generated graph/entity layouts are reclaimed only after a replacement has been
atomically published and flushed. Failed builds retain previous cached files.
Cleanup only touches the same generated-layout prefix and preserves status files
and concurrently published newer layouts.

## Friendly workspace and AI connection center (2026-10-01)

The default home is now a responsive human workspace with searchable passage
excerpts, a reader, note/page append forms, service status and import progress.
The existing 3D viewer is under **Explore graph** (`/explore`). The desktop launcher
opens the new workspace using its private owner token as before.

**Connect an AI** (`/connect`) provides a three-step setup, the advertised server
address, REST/MCP templates, a credential-free MD handoff download and a read-only
AI-key check. **Settings** groups recovery, key issuance, advanced quotas, the
portable advertised address and retained import recovery. A new key is shown once
and has a copy button. Saving an advertised address changes metadata; listeners,
allowed Hosts, DNS and TLS still need appropriate deployment configuration.

Read [AI_CONNECT.md](AI_CONNECT.md) for complete network, authentication,
REST, idempotency, polling and MCP instructions; see the
[portable client guide](clients/README_AI.md) for Python integration.
All agent tools use the same scoped REST gateway. Append MCP tools require an
explicit client opt-in and an ingest-scoped key. No additional public MCP listener
or database access is introduced. Browser activity polling pauses when hidden and
honors server retry delays. Lost submissions keep their original operation ID
while the page stays open; check activity before reloading. Secrets and drafts
are never persisted in browser storage.

## 10. Independent Aesir/Ollama chat routing

[AESIR_BACKEND.md](AESIR_BACKEND.md) is the complete operator/maintainer guide.
The human Knowledge services card and authenticated health expose selected chat,
readiness and circuit status separately from the original embedding service.
The current default remains measured faster Ollama. Native Aesir is supervised
and explicitly selectable for same-host work; its private service key is separate
from owner and external-AI credentials. Scoped read/append clients continue using
Bifröst and do not receive or need the native service key. No source re-embedding
or database migration accompanies chat selection.
