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
