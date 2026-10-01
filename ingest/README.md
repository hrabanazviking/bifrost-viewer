# Bifröst ingest component

Read the [technical manual](TECHNICAL_MANUAL.md) for CLI commands, private settings,
file/URL formats, inbox supervision, schema prerequisites and troubleshooting.

The complete document/URL ingest pipeline now lives in the Bifröst repository.
It uses an independent frozen Python environment so parser dependencies remain
outside the viewer process. The original local inbox and credentials can stay
where they are.

From the repository root:

```bash
uv sync --frozen --project ingest
cp ingest/.env.example ingest/.env
```

Edit ingest/.env for your PostgreSQL connection and Ollama embedding model, or set
INGEST_ENV_FILE to an existing private dotenv file. Configure that same variable
in the viewer's .env for URL-ingest jobs. Run commands from the repository root:

```bash
uv run --frozen --project ingest ingest/ingest.py stats
uv run --frozen --project ingest ingest/ingest.py add path/to/document.md
uv run --frozen --project ingest python -m unittest discover -s ingest/tests -v
uv run --frozen --project ingest scripts/watch_inbox.py
```

Set INGEST_STATE_DIR to the directory containing your existing inbox to preserve
processed/failed inputs and retry state. INGEST_PROJECT_DIR overrides the watcher
source directory; VIEWER_INGEST_PROJECT_DIR separately overrides the viewer's
source directory. Both source defaults point here. The provided systemd unit
uses the existing sibling directory only for private configuration and inbox data.
Adjust its environment lines for another installation.

For a new empty database, schema.sql describes the documents/chunks tables and
indexes expected by the viewer. Inspect it before applying it. It is not an
upgrade script and is never run automatically. Its vector dimension is 768;
choose a matching embedding model or deliberately adapt a fresh schema.

Failed inputs remain retained. Retries resume after restarts, completed URLs are
not repeated, and archives never overwrite an earlier input. Configuration,
inbox contents and runtime environments are ignored by Git.

HTTP ingestion now uses a separate restricted PostgreSQL role and isolated worker.
See [security operations](../security/README_AI.md); trusted local inbox configuration
is not inherited by API workers. API text preserves its UTF-8 text, uses a generated
payload path, and records server-assigned client/job provenance. URL fetching uses
safe_fetch.py: public addresses/ports only, pinned sockets, validated redirects,
verified TLS and bounded uncompressed responses. Source-table ownership stays here.
