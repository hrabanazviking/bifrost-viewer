# Document ingestion technical manual

Verified against the bundled parser and durable supervisor on 2026-10-01.
This folder contains canonical source tracked with Bifröst. Its own `pyproject.toml`,
lockfile and `.venv` isolate parser dependencies from the viewer runtime.
See the [stack manual](../SECOND_BRAIN_MANUAL.md) for backup and recovery.

## 1. Choose the correct entry point

| Workflow | Configuration | Permissions and supervision |
|---|---|---|
| Local CLI | `INGEST_ENV_FILE` or this folder's `.env` | Trusted owner DB; foreground command |
| Inbox watcher | `INGEST_ENV_FILE` plus `INGEST_STATE_DIR` | Trusted local ingestion, durable retry/archive state |
| Bifröst API | Private `VIEWER_API_INGEST_ENV_FILE` | Sandbox, append-only role, quotas and durable serial queue |

Outside AIs should use the [scoped API](../security/TECHNICAL_MANUAL.md), not this
trusted CLI or an owner database credential. The viewer/browser has text and URL
API ingestion; it does not accept arbitrary local filesystem paths.

## 2. Runtime and settings

From the Bifröst repository root:

```bash
cd "$HOME/ai/ingest-viewer"
uv sync --frozen --project ingest
export INGEST_ENV_FILE="$HOME/ai/ingest/.env"
uv run --frozen --project ingest ingest/ingest.py --help
```

The exported path is for the existing installation. For a fresh installation,
copy `ingest/.env.example` to a chosen private file and point `INGEST_ENV_FILE`
there. Restrict it to `0600`. Do not replace the current private `.env` by copying
the example over it. Existing process environment takes precedence over dotenv.
The viewer's root `.env` is not loaded automatically by this CLI; even `--help`
needs required ingest settings because configuration is read at module startup.

| Variable | Default/example | Meaning |
|---|---|---|
| `INGEST_DB_URL` | `postgresql:///knowledge` | Required trusted database connection |
| `OLLAMA_URL` | `http://localhost:11434` | Required embedding-service base URL |
| `INGEST_EMBED_MODEL` | `nomic-embed-text` | Required model compatible with stored embeddings |
| `INGEST_CHUNK_CHARS` | `2000` | Parser chunk target/maximum characters |
| `INGEST_CHUNK_OVERLAP` | `200` | Overlap between neighboring chunks |
| `INGEST_DB_CONNECT_TIMEOUT` | `5` | Connection timeout in seconds |
| `INGEST_EMBED_BATCH_SIZE` | `32` | Embedding batch size |
| `INGEST_STATE_DIR` | bundled project | Parent directory containing `inbox/` |
| `INGEST_PROJECT_DIR` | bundled source | Supervisor's parser code location |
| `INGEST_WATCH_POLL_SECONDS` | `5` | Supervisor scan interval |
| `INGEST_WATCH_SETTLE_SECONDS` | `3` | Minimum mtime quiet period before reading |
| `INGEST_WATCH_RETRY_SECONDS` | `30` | Exponential retry base |
| `INGEST_WATCH_RETRY_MAX_SECONDS` | `3600` | Retry delay ceiling |
| `INGEST_WATCH_JOB_TIMEOUT` | `900` | Trusted child-command deadline |

Configure paths as actual filesystem paths. Source directory and state directory
are independent: changing parser source does not require moving the private inbox.
`INGEST_STATE_DIR` denotes the parent of `inbox`, not `inbox` itself.

## 3. First-time database setup

This section is for a **new empty database**, not repair of an existing corpus.
Install PostgreSQL extensions through your distribution before running it. The
local account needs permission to create the database/extension and source schema.

```bash
createdb --template=template0 knowledge
psql --set=ON_ERROR_STOP=1 -d knowledge -f ingest/schema.sql
```

Run from the Bifröst root. Inspect `schema.sql` first. It creates vector/pg_trgm,
`documents` and `chunks`, full-text and vector indexes and cascading chunk ownership.
Its embedding column is **vector(768)** and its generated full-text column uses
English text search. Match the chosen embedding model to that schema. For another
dimension, deliberately prepare a fresh compatible schema before source insertion;
this file is not an automatic schema migration.

For an existing corpus, inspect without mutation:

```bash
psql -d knowledge -c '\d documents'
psql -d knowledge -c '\d chunks'
psql -d knowledge -c \
  'SELECT vector_dims(embedding), count(*) FROM chunks WHERE embedding IS NOT NULL GROUP BY 1;'
```

Matching dimension alone is insufficient: use the same embedding model/vector
space for all source/query/Skein operations. Back up before a deliberate re-embedding
or schema change. The ordinary CLI does not apply `schema.sql` automatically.

## 4. CLI command reference

Commands below assume the configured `INGEST_ENV_FILE` and Bifröst working directory.

```bash
uv run --frozen --project ingest ingest/ingest.py stats
uv run --frozen --project ingest ingest/ingest.py list --limit 20
uv run --frozen --project ingest ingest/ingest.py add ./notes/example.md
uv run --frozen --project ingest ingest/ingest.py add 'https://example.com/'
uv run --frozen --project ingest ingest/ingest.py search "Odin and wisdom" --k 8
uv run --frozen --project ingest ingest/ingest.py search "Odin" --k 5 --no-hybrid
```

Replace sample sources with documents you intend to keep. `stats`/`list` only read
the database; `search` also calls the embedding model. `add` parses, chunks,
validates embeddings and commits document/chunks together. Parsing/embedding
failure exits unsuccessfully without a half-inserted source document. Embeddings
are computed before the insertion transaction to avoid holding DB locks throughout
model work. Transient model HTTP failures have bounded retries.

The content hash covers extracted chunk text. An existing hash is a successful
duplicate; it does not overwrite an existing title, source or provenance. Concurrent
workers use the unique hash constraint. Different extraction/chunking may produce
a different hash even for a similar original file.

The explicit `delete DOC_ID` command **permanently removes that document and its
chunks** through the source schema's cascade. It is owner-only maintenance, not
an automatic repair action and not available remotely. Back up, confirm the exact
ID and inspect derived references before deliberately using it. No deletion
command is part of these routine examples.

## 5. File formats and public web pages

- Markdown/plain text and other formats use `unstructured` partitioning/chunking.
  PDF/office/image extraction can depend on external system tools and OCR resources;
  verify a representative file rather than assuming every format is available.
- `.json` is preserved as formatted Unicode JSON text; it is not executed.
- `.jsonl` is read as records and transformed to text. Blank/invalid JSON lines
  are skipped, so validate important input first if every record must be retained.
- Web sources use bounded public fetch followed by trafilatura article extraction
  and Markdown parsing. Login-only/JavaScript-only pages may yield no useful text.
- URL policy is shared with the secure API: only public HTTP(S) on ports 80/443,
  validated redirects/DNS, pinned connections and verified TLS, a 2 MiB uncompressed
  response ceiling. Credentials/private hosts/compressed responses are rejected.

Trusted files can be larger than API payload limits, but still require available
memory, parser tools, model capacity and reasonable child timeouts. Parser chunking
divides content; it is not an instruction to truncate original source files.
Change batch size or timeout only after identifying the resource bottleneck.

## 6. Inbox formats and workflow

Current private structure:

```text
~/ai/ingest/
  .env
  TECHNICAL_MANUAL.md
  inbox/
    .watch-state.json
    new-document.md
    processed/
    failed/
```

The watcher recognizes URL containers as follows:

| Extension | Format |
|---|---|
| `.urls` | One HTTP(S) URL per nonblank, non-comment line |
| `.url` | Internet shortcut-style `URL=https://...` lines |
| `.txt` | URL list only when every non-comment line is a valid URL; otherwise a normal text document |

Use `.urls` for an unambiguous URL list. Empty/invalid explicit URL containers are
retained for correction and marked permanent until their size/mtime changes.
Successfully completed URLs in a partially failed list are recorded, so ordinary
retries do not re-fetch them. Global source hash deduplication is a second safeguard.

For documents, place the finished file at the top level. Do not put a still-writing
file there and rely on a three-second settle delay to prove completion. Write a
hidden temporary file on the same filesystem and atomically rename it when finished.
The scan is not recursively watching arbitrary folders.

On success, the original moves to `processed`. On failure, it moves/stays in `failed`
and exponential retry state is persisted. Archive-name collisions get unique names,
so earlier originals are preserved. A corrected file's size/mtime resets its retry
record. Ordinary parser failures can retry indefinitely at the maximum delay;
the watcher does not automatically fix a malformed source. Keep failed inputs
until diagnosed, corrected or deliberately archived.

## 7. Service operation

The supplied watcher unit uses canonical source/runtime with private data at
`~/ai/ingest`. For a different installation, edit its `INGEST_ENV_FILE` and
`INGEST_STATE_DIR` lines before installing:

```bash
cp systemd/ingest-watcher.service "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now ingest-watcher.service
systemctl --user status ingest-watcher.service --no-pager
journalctl --user -u ingest-watcher.service -n 100 --no-pager
```

This command block is run from Bifröst root after creating the user-unit directory.
For foreground debugging, stop the watcher service first and run exactly one
supervisor:

```bash
export INGEST_ENV_FILE="$HOME/ai/ingest/.env"
export INGEST_STATE_DIR="$HOME/ai/ingest"
uv run --frozen --project ingest scripts/watch_inbox.py
```

Do not run two supervisors on the same inbox. Stop the foreground process and
restart the service afterward. Bifröst's API queue is separate from this trusted
watcher; each serializes its own jobs, so both can consume Ollama concurrently.

## 8. Diagnosing failures

| Symptom | Check |
|---|---|
| Missing ingest variable | Correct dotenv path and required names; viewer config is separate |
| DB connection error | Service, authentication/permissions, connection host and timeout |
| Dimension mismatch | Stored column/vector dimension and identical configured model |
| Empty extraction | Format tools, source encoding, inaccessible/dynamic web article |
| Long embedding phase | Ollama health, GPU/VRAM, batch size, concurrent workloads |
| File never picked up | Hidden/empty file, wrong state parent, settle time, nonrecursive location |
| Repeated `failed` retry | Read the local journal; fix the source or dependency instead of resetting all state |
| Duplicate reported | Content hash already exists; inspect list/search rather than forcing a copy |

Detailed watcher errors may contain source paths or private data; redact before
sharing. Back up the **entire inbox including `.watch-state.json`** and private
dotenv together with the database. Follow the [stack backup guide](../SECOND_BRAIN_MANUAL.md#back-up-and-verify).

## 9. Developer checks and contracts

```bash
uv run --frozen --project ingest python -m unittest discover -s ingest/tests -v
```

Run from Bifröst root. This checks regression behavior without replacing live
schema or source inputs. See [INTERFACE.md](INTERFACE.md), [README_AI.md](README_AI.md)
and [security worker setup](../security/TECHNICAL_MANUAL.md#7-worker-isolation-and-database-permissions).
