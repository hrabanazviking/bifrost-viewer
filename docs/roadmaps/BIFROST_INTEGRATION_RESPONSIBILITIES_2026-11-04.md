# Bifröst Viewer: Canonical Coordinator and Integration Owner

**Date:** 2026-11-04  
**Repository:** `hrabanazviking/bifrost-viewer`  
**Status:** Design tasks only, no implementation changes.

## Sources of authority

- [Canonical 10,357-word master roadmap](https://github.com/hrabanazviking/bifrost-viewer/blob/main/docs/roadmaps/BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md)
- [Full local roadmap copy](BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md)
- Existing project source/architecture/compatibility tests. Do not mistake roadmap proposals for implemented behavior.

## Mission

Own the cross-repository roadmap, orchestrate work safely and serve the versioned API while preserving the source-write ownership of Ingest and graph ownership of Skein.

## This repository's implementation work

1. Maintain one canonical roadmap and a published manifest of participating repositories and their mirrored copies.
2. Implement verified source inventory and dated backup/restore to the dedicated document drive before risky processing upgrades.
3. Add durable job controller, quiet pause/resume and real multi-stage progress telemetry.
4. Coordinate incremental Skein graph generation through its public API, rather than mutating Skein private code.
5. Implement optional local/cloud/hybrid provider routing with budget, rate, privacy and retries.
6. Add source watchtower and review existing installed GitHub/blog collectors instead of duplicating them.
7. Provide versioned drafts and LibreOffice integration through Ingest-approved source changes.
8. Implement Google Docs/Drive file/multiple/folder sync with per-user consent and conflict reviews.
9. Keep project Longhouse inside Bifröst; expose versioned scoped knowledge and project interfaces to apps.
10. Implement optional Kista adapter for specific secrets, never general vault retrieval.
11. Build expansive accurate live/history/next/observatory screens while preserving simple default UI.

## Acceptance gates

- [ ] No changes to canonical source except by Ingest
- [ ] Safe restore demonstrated and quiet pause real
- [ ] Every connector opt-in with authorization tests
- [ ] No secrets in Git, logs, corpus or agent prompts

## Mandatory safety boundaries

- Keep project behavior, original data, and tested APIs unchanged unless an explicitly approved migration is staged, benchmarked and reversible.
- The Bifröst Viewer server owns the knowledge API, Ingest owns source writes, Skein owns derived graphs, and Skry remains read-only.
- All integrations must be optional, independently authenticated, scoped and resilient to server outages.
- Never commit live credentials, Google OAuth tokens/client secrets, API keys, Kista vault values, personal account information, downloaded private documents, full DB dumps, or runtime logs.
- Use sanitized fixtures and error/credential canary tests. Public descriptions of integrations are not claims of working connections.

## First safe engineering step

Inventory the existing implementation and any newer unpublished local work, then write a small versioned integration interface and associated synthetic tests. Maintain independent project development and review operational changes before deployment.

## Owner-required managed raw library extension (2026-11-19)

Bifröst coordinates a user-managed nested RawLibrary and **Ingest New Files** button, extending rather than replacing the existing inbox. Ingest tracks source instances, normalized folder ancestry, file move/rename history, raw content hashes and stable versions; it reads only owner-approved filesystem roots. A duplicate in a second folder gets a separate association but no duplicate embeddings or image descriptions. A moved unchanged file updates location/category metadata only; edited files trigger only affected extraction and graph updates. Bifröst exposes folder/category browsing and read-only search through its existing API with universal AI access unchanged.

Full acceptance details: [Managed Raw Library and Delta Ingestion](SECOND_BRAIN_MANAGED_RAW_LIBRARY_FOLDERS_2026-11-19.md). The [latest combined modernization plan](SECOND_BRAIN_ADDITIVE_INCREMENTAL_MULTIMODAL_GATEWAY_2026-11-19.md) remains design-only until tested and deployed.

## Owner-required three-tier memory separation (2026-11-19)

[Bifröst Three-Tier Memory Architecture](SECOND_BRAIN_THREE_TIER_MEMORY_ARCHITECTURE_2026-11-19.md) is the owner-approved new governing plan: accepted long-term archive entries are **immutable**; corrections are added as new linked immutable versions, while the mutable RawLibrary path ledger tracks moves/copies separately. Medium-term memory stores editable active folder/project focus, importance and optional Ravens associations; it MUST NOT modify canonical archived evidence. Short-term memory is bounded, session-isolated, volatile and expires without persisting in backups/logs by default. Read-only authorized character clients search all approved knowledge uniformly with zero per-character collection setup. Model backends, HugrGate and Raven activation cannot write canonical content; only privileged Ingest/owner archive workflows append after approval. Test write denial, correction history, focus updates without rebuild, TTL expiry and multi-session isolation. Documentation only.
