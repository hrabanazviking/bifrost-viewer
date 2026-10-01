# Maintaining Bifrost

Read TASK_second_brain_resilience.md, PROJECT_LAWS.md and docs/operations.md.
viewer.py owns authentication, read routes, orchestration and maintenance.
graph_builder.py owns disposable graph computation and closes its own pool.
runtime_support.py publishes derived JSON atomically; it does not touch source data.
local_server.py binds the configured listener and loopback without opening a new public interface.
The static frontend starts in document overview and preserves the existing detailed chunk view.
