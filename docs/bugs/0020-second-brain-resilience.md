# Bug group: second-brain access, resource use and recovery

Discovered: 2026-09-30. Status: resolved with regression and live verification.

Observed failures: localhost refused connections while tailnet worked; token-free
visits stopped at a missing-token screen; corrupt existing caches suppressed builds;
startup depended on database/cache probing; similarity work allocated a corpus-sized
square matrix; document view exposed hundreds of thousands of links; entity UMAP
ran in a web worker; inbox failures had no durable retries; CPU gauge cache corruption
could terminate the collector; keyword-only candidates were lost in hybrid search.

Owning domains and implementation are recorded in TASK_second_brain_resilience.md,
INTERFACE.md and docs/operations.md. Verification covers failed atomic writes,
cache corruption, process crashes, database outage at startup, dense-vs-blocked
neighbors, sparse document view, retry persistence, partial URL success, archive
collisions and keyword search fallback. Source documents remain preserved.
