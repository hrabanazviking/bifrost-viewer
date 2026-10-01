# Bifrost HTTP contracts

All /api routes require the existing bearer token or legacy query token.
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
INGEST_ENV_FILE selects private CLI configuration inherited by the subprocess.
The watcher separately uses INGEST_PROJECT_DIR and INGEST_STATE_DIR.
