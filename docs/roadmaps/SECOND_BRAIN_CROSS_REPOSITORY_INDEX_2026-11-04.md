# Bifröst Second Brain: Cross-Repository Roadmap Index

**Published:** 2026-11-04  
**Updated:** 2026-11-19 (additive design update)  
**Status:** Cross-repository planning documents; no runtime features implied by the presence of these files.  
**Scope:** Public integration index. Private repositories are intentionally omitted from this public table.

## Canonical architecture

**[Read the canonical master roadmap](https://github.com/hrabanazviking/bifrost-viewer/blob/main/docs/roadmaps/BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md)**

The original roadmap contains approximately 10,357 words and covers verified backup and restore, truly resumable processing, incremental Skein graph construction, optional local/cloud/hybrid inference, cost controls, Kista as a secret broker, a technically rich Observatory, LibreOffice editing, Google Docs/Drive import/export, project management inside Bifröst and optional external application access.

For each public repository listed below, the **full roadmap has been copied intact** into its own `docs/roadmaps/` directory. Each also has a shorter, repository-specific Markdown file defining its distinct responsibilities and acceptance tests.

## Latest design authority (2026-11-19)

The [newer additive modernization and living visual lore addendum](SECOND_BRAIN_ADDITIVE_INCREMENTAL_MULTIMODAL_GATEWAY_2026-11-19.md) accompanies the canonical master roadmap and supersedes older conflicting design prohibitions, including Skein's original no-incremental rule. **Current code and deployment status must still be verified separately.**

The new capabilities are: ordinary incremental updates by source delta, persistent revocable read-only keys, optional G14 gateway to existing Z13 Gufo inference, mandatory comprehensive image description and visible-trait extraction, owner-curated character/asset visual identity canon for image-generation systems, cross-modal retrieval, and performance testing before selective remote inference offload. Original source documents and the last known-good published graph remain protected.

**Distribution policy:** Bifröst owns the canonical master and full addendum; Skein and Skry each own implementation-specific responsibility addenda; Gufo owns inference-service behavior, not brain data. Dated roadmap mirrors are snapshots and should be reissued deliberately after the canonical plan is reviewed. Consumer repos link to the canonical design rather than becoming competing sources of truth.

## Published public repositories and documents

| Repository | Complete master roadmap | Repository responsibilities | Role |
|---|---|---|---|
| [bifrost-viewer](https://github.com/hrabanazviking/bifrost-viewer) | [Full roadmap](https://github.com/hrabanazviking/bifrost-viewer/blob/main/docs/roadmaps/BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md) | [Local responsibilities](https://github.com/hrabanazviking/bifrost-viewer/blob/main/docs/roadmaps/BIFROST_INTEGRATION_RESPONSIBILITIES_2026-11-04.md) | Main Second Brain UI, orchestration, Google Docs, LibreOffice, backups and Project Longhouse |
| [skein-kg](https://github.com/hrabanazviking/skein-kg) | [Full roadmap](https://github.com/hrabanazviking/skein-kg/blob/main/docs/roadmaps/BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md) | [Local responsibilities](https://github.com/hrabanazviking/skein-kg/blob/main/docs/roadmaps/BIFROST_INTEGRATION_RESPONSIBILITIES_2026-11-04.md) | Incremental relation graph, resumable jobs and inference provider decisions |
| [skry-kg](https://github.com/hrabanazviking/skry-kg) | [Full roadmap](https://github.com/hrabanazviking/skry-kg/blob/main/docs/roadmaps/BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md) | [Local responsibilities](https://github.com/hrabanazviking/skry-kg/blob/main/docs/roadmaps/BIFROST_INTEGRATION_RESPONSIBILITIES_2026-11-04.md) | Fast read-only knowledge neighborhoods and source evidence |
| [kista](https://github.com/hrabanazviking/kista) | [Full roadmap](https://github.com/hrabanazviking/kista/blob/main/docs/roadmaps/BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md) | [Local responsibilities](https://github.com/hrabanazviking/kista/blob/main/docs/roadmaps/BIFROST_INTEGRATION_RESPONSIBILITIES_2026-11-04.md) | Optional scoped encrypted secret provider, never a searchable knowledge store |
| [bifrost](https://github.com/hrabanazviking/bifrost) | [Full roadmap](https://github.com/hrabanazviking/bifrost/blob/main/docs/roadmaps/BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md) | [Local responsibilities](https://github.com/hrabanazviking/bifrost/blob/main/docs/roadmaps/BIFROST_INTEGRATION_RESPONSIBILITIES_2026-11-04.md) | Distinct composite memory-bridge system, optional connection to Bifröst Viewer |
| [RuneForgeAI-Project-Aesir](https://github.com/hrabanazviking/RuneForgeAI-Project-Aesir) | [Full roadmap](https://github.com/hrabanazviking/RuneForgeAI-Project-Aesir/blob/main/docs/roadmaps/BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md) | [Local responsibilities](https://github.com/hrabanazviking/RuneForgeAI-Project-Aesir/blob/main/docs/roadmaps/BIFROST_INTEGRATION_RESPONSIBILITIES_2026-11-04.md) | Optional local model inference backend for the knowledge pipeline |
| [Runa-Agent-Digital-Being](https://github.com/hrabanazviking/Runa-Agent-Digital-Being) | [Full roadmap](https://github.com/hrabanazviking/Runa-Agent-Digital-Being/blob/development/docs/roadmaps/BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md) | [Local responsibilities](https://github.com/hrabanazviking/Runa-Agent-Digital-Being/blob/development/docs/roadmaps/BIFROST_INTEGRATION_RESPONSIBILITIES_2026-11-04.md) | Optional sourced knowledge and project information for Runa |
| [RuneForgeAI-Runmal](https://github.com/hrabanazviking/RuneForgeAI-Runmal) | [Full roadmap](https://github.com/hrabanazviking/RuneForgeAI-Runmal/blob/main/docs/roadmaps/BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md) | [Local responsibilities](https://github.com/hrabanazviking/RuneForgeAI-Runmal/blob/main/docs/roadmaps/BIFROST_INTEGRATION_RESPONSIBILITIES_2026-11-04.md) | Opt-in companion lorebook and research access |
| [RuneForgeAI-Project-Hlidhskjalf](https://github.com/hrabanazviking/RuneForgeAI-Project-Hlidhskjalf) | [Full roadmap](https://github.com/hrabanazviking/RuneForgeAI-Project-Hlidhskjalf/blob/main/docs/roadmaps/BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md) | [Local responsibilities](https://github.com/hrabanazviking/RuneForgeAI-Project-Hlidhskjalf/blob/main/docs/roadmaps/BIFROST_INTEGRATION_RESPONSIBILITIES_2026-11-04.md) | Optional progress, GPU and knowledge observability client |
| [WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model](https://github.com/hrabanazviking/WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model) | [Full roadmap](https://github.com/hrabanazviking/WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model/blob/development/docs/roadmaps/BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md) | [Local responsibilities](https://github.com/hrabanazviking/WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model/blob/development/docs/roadmaps/BIFROST_INTEGRATION_RESPONSIBILITIES_2026-11-04.md) | Optional research evidence for ECS/world modeling |
| [Mythic-Engineering](https://github.com/hrabanazviking/Mythic-Engineering) | [Full roadmap](https://github.com/hrabanazviking/Mythic-Engineering/blob/main/docs/roadmaps/BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md) | [Local responsibilities](https://github.com/hrabanazviking/Mythic-Engineering/blob/main/docs/roadmaps/BIFROST_INTEGRATION_RESPONSIBILITIES_2026-11-04.md) | Cross-project integration protocol and secure agent workflow conventions |
| [Heimdall-SL-Hermes-Agent](https://github.com/hrabanazviking/Heimdall-SL-Hermes-Agent) | [Full roadmap](https://github.com/hrabanazviking/Heimdall-SL-Hermes-Agent/blob/development/docs/roadmaps/BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md) | [Local responsibilities](https://github.com/hrabanazviking/Heimdall-SL-Hermes-Agent/blob/development/docs/roadmaps/BIFROST_INTEGRATION_RESPONSIBILITIES_2026-11-04.md) | Scoped source references for a Second Life agent |
| [Heathen-Emergent-Reality-Engine-Thoughtform-Intelligence-Companion](https://github.com/hrabanazviking/Heathen-Emergent-Reality-Engine-Thoughtform-Intelligence-Companion) | [Full roadmap](https://github.com/hrabanazviking/Heathen-Emergent-Reality-Engine-Thoughtform-Intelligence-Companion/blob/main/docs/roadmaps/BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md) | [Local responsibilities](https://github.com/hrabanazviking/Heathen-Emergent-Reality-Engine-Thoughtform-Intelligence-Companion/blob/main/docs/roadmaps/BIFROST_INTEGRATION_RESPONSIBILITIES_2026-11-04.md) | Independent companion-memory and external knowledge separation |
| [NorseSagaEngine](https://github.com/hrabanazviking/NorseSagaEngine) | [Full roadmap](https://github.com/hrabanazviking/NorseSagaEngine/blob/Development/docs/roadmaps/BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md) | [Local responsibilities](https://github.com/hrabanazviking/NorseSagaEngine/blob/Development/docs/roadmaps/BIFROST_INTEGRATION_RESPONSIBILITIES_2026-11-04.md) | Optional source-supported Norse lore for the RPG |
| [Mythic_Agent_Coder_CLI](https://github.com/hrabanazviking/Mythic_Agent_Coder_CLI) | [Full roadmap](https://github.com/hrabanazviking/Mythic_Agent_Coder_CLI/blob/development/docs/roadmaps/BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md) | [Local responsibilities](https://github.com/hrabanazviking/Mythic_Agent_Coder_CLI/blob/development/docs/roadmaps/BIFROST_INTEGRATION_RESPONSIBILITIES_2026-11-04.md) | Optional project/knowledge registry client for the coding agent |

## Private integrations

Additional copies and local responsibility documents may exist in private project repositories. Their names, paths, credentials, access controls, or implementation details are deliberately not enumerated in this public index. The owner manages those integrations independently.

## Maintenance policy: avoid documentation drift

1. The Bifröst Viewer version is **canonical**; all other full roadmaps are dated snapshots.
2. An agent implementing a feature should read the canonical master, its own repository-specific responsibility file, and its actual current code and architecture rules.
3. If the master changes, the designated cross-repo maintainer should prepare a clear diff, publish a new version/date, and synchronize mirrors without silently overwriting local repository-specific decisions.
4. Mirrored Markdown is documentation only, not source corpus ingestion. It must not create an unbounded set of duplicate knowledge records in the running Second Brain.
5. No automation may use the presence of a roadmap as authorization to alter deployed services or to publish credentials, private corpus contents, account identities, OAuth tokens, API keys, vault data or live database dumps.
6. If a feature is not present in the published repository, audit newer local/deployed versions before classifying it as missing.
7. Validate broken links, API compatibility, SPDX licensing, secret scanning and preservation tests in each repository before implementation.

## Core ownership

- **Bifröst Viewer**: user interface, orchestration, source monitoring, backup operations, Google/LibreOffice integration and Project Longhouse.
- **Ingest inside Bifröst**: authoritative document/chunk writes and source revisions.
- **Skein**: derived knowledge graph, staged generations, inference and checkpointed rebuilds.
- **Skry**: read-only, query-time relationship exploration.
- **Kista**: optionally supplies a precisely scoped credential to a privileged worker. It is **not** a document index, graph storage, or RAG source.
- **Other applications**: opt-in scoped knowledge consumers, preserving independence and requiring owner authorization for writes.

The aim is one trustworthy knowledge ecosystem with modular optional integrations, not a forced monolith and not a new standalone project.
