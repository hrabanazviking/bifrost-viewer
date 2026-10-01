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

## Completion evidence

Implemented the human workspace, preserved graph, connection center, clearer owner
controls, validated portable address, bounded public discovery and authenticated
agent OpenAPI with response schemas. Added a separate dependency-free REST client
and locked optional MCP SDK 2 stdio adapter, with seven read tools and two opt-in
append tools. Server authorization and append-only source ownership remain intact.

Verification: 105 viewer tests including four real isolated ingestion checks,
26 portable-client/MCP tests, desktop and 390px mobile browser checks, live REST
and MCP read checks over the configured tailnet listener, scope/revocation checks,
and live schema validation. Documents/passages stayed at 1237/49006. Services run
without restarts after deployment; NVIDIA and Ollama remain available. MD validation
covers ten manuals, 107 local links, 47 Bash blocks and two Python examples.

Remote reachability must be tested from the agent machine. The stdio adapter needs
a compatible local AI host; cloud-only hosts need an authorized REST integration.
The advertised address is metadata and does not configure public TLS or networking.
