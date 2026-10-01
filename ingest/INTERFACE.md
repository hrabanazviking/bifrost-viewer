# Ingest CLI contract

Run ingest.py with the frozen dependencies in this directory. Commands remain
add SOURCE, search QUERY, stats, list, doctor [--json] and delete DOC_ID. add accepts a local file
or HTTP(S) URL; it exits unsuccessfully when parsing, embedding or persistence
fails, and treats an existing content hash as successful duplicate ingestion.
delete is an explicitly invoked destructive CLI command, never called by the
watcher or viewer during recovery.

Configuration comes from process environment and the dotenv file selected by
INGEST_ENV_FILE, defaulting to this directory's .env. Required keys are
INGEST_DB_URL, OLLAMA_URL and INGEST_EMBED_MODEL. Environment takes precedence.
The bundled schema uses 768-dimensional embeddings; existing databases must match
the selected model. No command applies schema.sql automatically.

Embedding batches must have complete cardinality, consistent dimensions, finite
values and nonzero vectors. Transient HTTP failures retry. Embeddings are computed
before opening the insertion transaction; document and chunk rows commit together.
Content hashes prevent duplicates, including concurrent workers.

scripts/watch_inbox.py invokes this CLI in a child process. Its INGEST_PROJECT_DIR
selects source code; INGEST_STATE_DIR independently selects inbox/processed,
inbox/failed and durable retry metadata. Defaults use this bundled directory.

Recovery settings live in recovery.json with INGEST_<UPPERCASE_KEY> overrides.
Embedding splits preserve input order/cardinality and share a bounded per-batch
request budget. Local identity/size/mtime changes defer insertion. Malformed JSONL
aborts the whole input, with no partial records. API text uses character chunks
without normalizing its whitespace. Fixed target vector dimension is preflighted.
Transient SQL operations use fresh connections; prepared inserts replay safely
without re-embedding, including ambiguous commits through hash deduplication.

CLI exit classification: 20 temporary dependency/storage, 21 input, 22
configuration, 1 unexpected. Supervisors report 124 for deadline expiration.
Help does not require credentials. doctor is read-only and performs no repair.
Progress uses BIFROST_PROGRESS JSON log markers; INGEST_PROGRESS_FILE is an optional
trusted-local output only. The isolated API worker never receives that setting.
