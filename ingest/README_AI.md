# Bundled ingest ownership

This component owns parsing, chunking, embedding and documents/chunks writes.
The parent viewer remains a reader and delegates ingestion through this CLI.
ingest.py is the canonical source; schema.sql describes the compatible initial
schema and is never automatically applied to an existing database.
watch.py is the optional entry point to scripts/watch_inbox.py in the parent repo.
pyproject.toml and uv.lock define the independent parser runtime. Keep heavy parser
dependencies out of the viewer process. Tests mock DB/model boundaries.

INGEST_ENV_FILE selects private configuration; INGEST_STATE_DIR selects durable
inbox storage for scripts/watch_inbox.py. Neither belongs in Git. Legacy local
entry points may forward here. Read INTERFACE.md before changing CLI contracts.
