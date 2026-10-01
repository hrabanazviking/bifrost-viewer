# Maintaining Bifrost

Read TASK_second_brain_resilience.md, PROJECT_LAWS.md and docs/operations.md.
viewer.py owns authentication, read routes, orchestration and maintenance.
graph_builder.py owns disposable graph computation and closes its own pool.
runtime_support.py publishes derived JSON atomically; it does not touch source data.
local_server.py binds the configured listener and loopback without opening a new public interface.
The static frontend starts in document overview and preserves the existing detailed chunk view.
ingest/ owns the published CLI, schema and separate frozen parser environment.
The viewer delegates to it; ingestion source and private runtime data are separate.

The default human workspace is static/workspace.html; `/explore` retains the 3D
viewer. security/connections.py owns discovery, advertised profile and curated
agent schema. clients/ owns a separate locked optional MCP runtime; do not add
SDK dependencies to the viewer or bypass the REST gateway. Read AI_CONNECT.md,
TASK_friendly_connections.md and clients/README_AI.md before changing agent flows.

inference.py owns independent stateless chat routing, private native credential
admission, bounded HTTP responses/concurrency and circuit recovery. inference.json
owns policy. viewer.ollama_chat retains its public name but delegates to this
router; viewer.ollama_embed and downstream ingestion/Skry/Skein embedding identity
stay separate. Read TASK_aesir_backend.md and AESIR_BACKEND.md before changing it.
Provider/model/policy changes require restart; lazy configuration failure must not
stop viewer boot. External AIs continue using the scoped Bifröst gateway.
