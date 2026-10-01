# Bifrost HTTP contracts

All data /api routes require a scoped bearer token or the compatible query token.
Public recovery routes expose generic request acknowledgements and accept only
single-use expiring confirmation codes. See security/INTERFACE.md.
GET / returns the static page with an access-token form. The local launcher places
its token in a URL fragment, which is never part of the HTTP request URL.

Graph routes return 200 with the existing graph shape when ready. Chunk/document
and entity routes return 202 with pending=true and build_state while a subprocess
computes the layout. Entity layout failures return 503 with a retryable error until
its retry cooldown expires. The frontend handles both graphs' pending states.
The v3 chunk cache retains chunk/document/node/link shapes, selects sparse exact
cosine neighbors for document edges, and is atomically published after computation.

GET /api/search retains query, hyde_used, hyde_doc and hits. Each hit adds doc_id.
search_mode is hybrid or keyword; degraded identifies keyword-only outage fallback.
Keyword candidates are included even when absent from the semantic candidate set.
HyDE failures use the raw query and report hyde_used=false.

Maintenance retries database connections and absent/corrupt graphs without requiring
an open browser. Failed builds have a cooldown; obsolete builds are superseded when
new corpus rows change the fingerprint. Fingerprints use row count and maximum ID,
so editing existing source rows in place still requires a forced rebuild.

POST /api/ingest/url now delegates to the bundled ingest/ subproject with its
frozen environment. Its job/status response shape is unchanged.
VIEWER_INGEST_PROJECT_DIR optionally selects another source project;
VIEWER_API_INGEST_ENV_FILE selects the separate append-only configuration for
HTTP workers. Their environment is allowlisted and their filesystem/processes
are isolated with Bubblewrap. INGEST_ENV_FILE selects trusted local CLI configuration.
The watcher separately uses INGEST_PROJECT_DIR and INGEST_STATE_DIR.

Ingestion worker stages/exit/retry contracts are documented in ingest/INTERFACE.md
and security/INTERFACE.md. Owner diagnostics/retry routes are scoped admin-only.
Entity layouts use v2_build<build-id>_<source-fingerprint> keys. Each entity/edge
read uses one repeatable-read snapshot and rejects a changed generation. Starting
a Skein rebuild retains the previous cached layouts until successful replacement.

## Friendly workspace and connection contract

`GET /` is the human workspace; `GET /explore` is the original graph; `GET /connect`
is the AI setup page. `GET /AI_CONNECT.md` downloads credential-free instructions.
`GET /api/overview` requires read scope and returns documents/chunks counts from
the shared pool without loading a graph. Job records add optional `title` for
human activity labels; existing job fields and ownership remain compatible.

`GET /.well-known/bifrost.json` is bounded public metadata. `GET /api/capabilities`
and `/api/auth/me` retain previous fields and add principal-specific quotas and
protocol/retry descriptors. `GET /api/ai/openapi.json` requires read and excludes
administration. Owner-only GET/POST `/api/admin/connection` controls name/base_url;
URLs are validated origins, never fetched or used to change listener security.
Allowed cross-origin callers can read Retry-After on errors as well as successes.
See AI_CONNECT.md and clients/README_AI.md for operational contracts.

## Additive chat health contract — 2026-10-01

GET /api/health adds inference with configured_provider, fallback_provider,
last_provider, last_error, circuit, retry_after_seconds, ready and
embeddings_provider. Existing DB/Ollama/cache/build fields remain. Configuration
errors report safe ready=false/last_error=configuration without private paths.
Readiness is cached ten seconds. Native success requires the configured model,
CUDA backend and EOS/length completion; Ollama requires the configured model,
done=true and stop/length. Partial text is discarded. HyDE/raw-query and keyword
fallback response fields retain their existing meanings. Provider selection is
private operator configuration, not a new external model or admin API.
See AESIR_BACKEND.md and inference.json for explicit circuit/response limits.
