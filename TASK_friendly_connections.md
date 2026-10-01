# Friendly human workspace and authorized AI connections

## Problem and outcome
The graph-first interface obscures everyday search, reading and append operations.
Network agents have REST endpoints but lack a complete discovery contract, portable
client and connection instructions. Build a responsive default workspace, retain
the graph at `/explore`, provide a connection center and improve owner onboarding.

## Ownership and architecture
Bifröst owns pages, authentication metadata, discovery and REST contracts. A
separate portable client and optional standard MCP stdio adapter run on the agent
machine and call the existing scoped REST gateway. No second network write path.
Skein and Skry remain libraries, and ingestion retains source-table ownership.

## Invariants
- Knowledge remains authenticated; read and append clients cannot administer.
- Preserve original sources and existing graph/search/ingest API behavior.
- Keep all quotas, durable idempotency, expiry, revocation and worker isolation.
- No credentials in discovery, generated documentation, logs or browser storage.
- Published connection URLs are validated metadata, never a proxy or fetch target.
- Browser forms and job states report real failures, pending work and retry delays.
- Network client retries are bounded; repeated writes retain the same request key.

## Deliverables and verification
Responsive workspace and connection pages; friendlier owner controls; discovery,
curated OpenAPI, Python REST client and MCP adapter; AI_CONNECT.md and component
manual updates. Verify authorization, profile URL validation, retries, redirect
refusal, scope-limited tool contracts, browser desktop/mobile behavior and existing
regressions. Deploy and verify live read-only service health, preserve corpus and
push implementation to the owning GitHub project. Package updated public manuals.

## Authorization
Volmarr requested implementation, network agent access, human usability and MD
instructions, with prior explicit authorization to push improvements to GitHub.
Routine implementation, verification and deployment continue within that scope.
