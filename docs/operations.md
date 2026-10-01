# Second-brain operations and recovery

## Boundaries

PostgreSQL owns documents and chunks. The bundled ingest/ CLI owns ingestion.
Bifrost owns authenticated display/search, disposable layouts and supervision.
Skein writes only derived skein tables; Skry remains read-only.

## Access

Use the Bifrost Second Brain desktop launcher, or visit http://127.0.0.1:8731 and
enter the configured token. The launcher reads .env and never prints the secret.
It uses a fragment URL to keep the token out of server access logs. Legacy query
links are still accepted and moved to a fragment by the browser.

## Recovery

The lifespan starts even when PostgreSQL is unavailable. A periodic maintenance
loop retries cache builds when database service returns. Pool creation is locked,
connection waits are bounded, unreadable or wrong-shape caches are rebuildable,
and derived JSON is atomically replaced. Last-good files remain on disk during
rebuilds. A chunk or entity-layout builder whose progress stalls is killed; failed builds retry after a
cooldown. Children use the existing interpreter and are covered by systemd's cgroup.
No live cache files are pruned before a build succeeds.

Chunk edge selection and cluster propagation operate in row blocks. Document
view uses sparse nearest-neighbor edges, avoiding a nearly complete graph. Entity
layout runs in another interpreter so UMAP cannot block web request handlers.

## Bundled inbox supervisor

Use the frozen ingest/ runtime to run scripts/watch_inbox.py. Its source defaults
to the bundled ingest component. INGEST_ENV_FILE selects a private dotenv file;
INGEST_STATE_DIR selects the directory containing the durable inbox. For another
source project, set INGEST_PROJECT_DIR for the watcher and
VIEWER_INGEST_PROJECT_DIR for viewer URL jobs. Keep .env, inbox inputs and retry
metadata outside Git. The installed sibling entry points may forward to this code.

The supervisor retains inputs in inbox/failed and persists exponential retry times
and completed URLs in inbox/.watch-state.json. Restarts resume retries. Archive
collisions receive unique filenames. Empty or invalid URL lists stay retained for
manual correction. Corrected files reset retry metadata; ordinary text files remain
ordinary documents. See ingest/INTERFACE.md for CLI/configuration contracts.

The supervisor waits for file mtime to settle; producers writing huge files should
write a hidden temporary filename and atomically rename it into the inbox when done.
Retries are serialized to avoid multiplying memory/model workloads. Permanent
parse failures can recur at the maximum retry interval until the input is corrected.

## Verification and limits

Run uv run --frozen pytest -q. Check systemctl --user status bifrost ingest-watcher.
Source-row in-place edits are outside the count/max-ID fingerprint; use a forced
rebuild after such edits. No software can guarantee absence of all bugs. The source
corpus is not truncated and no destructive database migration is required here.

NVIDIA availability is optional for correctness. The gauge reports unavailable
rather than crashing if the kernel driver is absent; embeddings/search can use CPU.
