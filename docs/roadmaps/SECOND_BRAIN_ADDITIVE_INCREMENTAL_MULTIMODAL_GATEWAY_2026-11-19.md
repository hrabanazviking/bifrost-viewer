# Second Brain Additive Evolution: Incremental Updates, Permanent Keys, Universal Gateway and Multimodal Memory

**Date:** 2026-11-19  
**Status:** Engineering addendum and implementation plan; NOT proof of deployed functionality  
**Authority:** Supplements, does not replace, the [canonical November 4 master expansion roadmap](BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md) and the [cross-repository index](SECOND_BRAIN_CROSS_REPOSITORY_INDEX_2026-11-04.md).

## Decision and mission

Evolve the existing Bifröst Second Brain through optional, versioned, additive modules. Do not rebuild, overwrite, or re-index the entire corpus when an AI client connects, a source is appended, or one relation changes. Existing documents, chunks, embedding identity, working APIs, published Skein graph, installed collectors, application integrations, and owner control must remain intact.

Work spans four coordinated tracks:

1. **Incremental source and knowledge-graph updates**: append/revise only affected source records and derived graph neighborhoods; retain original full-rebuild behavior as a fallback.
2. **Optional never-expiring AI API keys**: a token may remain valid until specifically revoked; time-limited keys remain the default.
3. **Optional second-brain-aware chat gateway**: light on-demand service on the second-brain host; read-only retrieval for all authorized character clients; use an independently running Gufo service on another trusted local inference machine.
4. **Multimodal memories**: add native references and retrieval for image, audio, video, and document layout without discarding the established text corpus.

This is ONE integrated system with feature-gated extensions, not a parallel replacement brain or a new mandatory database stack.

## Verified public repository baseline and outstanding unknowns

- Bifröst Viewer already has a human workspace, Connect an AI flow, scoped API keys, portable REST client, and optional MCP stdio adapter. Start with security/store.py, security/routes.py, security/gateway.py, static/security.html, static/security.js, AI_CONNECT.md, clients/, inference.py, and ingest/.
- Its security SQLite schema already declares an optional expires field. Authentication already accepts a missing expiration for owner credentials; delegated key creation currently requires 1-365 days. A narrow API/form update may be sufficient; **do not migrate security storage without evidence that a schema change is needed**.
- Skein currently documents and implements an atomic, full replacement of its own derived skein_* graph rows. The November 4 master roadmap and skein-kg's local responsibilities propose an opt-in incremental_v2 instead. Existing skein-kg/PROJECT_LAWS.md says the original build has no incremental mode. **Resolve this explicit contract conflict by preserving original build_skein()/CLI behavior and making incremental_v2 a separately named, versioned opt-in public API; do not silently reinterpret the existing law or rewrite original build semantics**.
- Ingest supports several text/document formats and may extract some image contents via optional tooling, but verified image/audio/video understanding and cross-modal retrieval are NOT established by those extraction references.
- The published master roadmap explicitly states that additional connectors may exist on the installed host. Inspect deployed/local state before classifying any component as absent or duplicating it.
- Actual Gufo API route, request/response compatibility, port, service health contract, model capabilities and Janitor AI proxy reachability must be verified in the target environment rather than assumed from architecture sketches.
- Never put runtime secrets, private collection names, live corpus, precise host addresses, private URLs or credential material into public Markdown.

## Track A: additive, resumable knowledge updates (highest priority)

### A0. Audit and safety

- [ ] Inventory installed services, source collectors, queue jobs, DB schema and indexes, baseline build timing, graph count, source and chunk counts, extraction cache, current graph generation, current APIs and actual active branches. **Read-only audit only.**
- [ ] Verify a dated, restorable, consistency-checked backup of canonical Postgres sources plus a separately restorable graph snapshot. Confirm available disk and backup target; do not assume paths or attached drives.
- [ ] Establish gold fixtures covering unchanged, appended, edited, deleted, retitled, renamed, near-duplicate, mixed-permission, malformed, and interrupted inputs.
- [ ] Record current full-build output and retrieval results so semantic/graph drift is measurable.

### A1. Preserve source-of-truth ownership

- [ ] Ingest alone creates, versions, and updates canonical documents/chunks. Use stable source ID, revision, normalized content hash and collection-wide change manifests.
- [ ] Treat reconnecting an AI client as a permissions/network event, **not an ingestion or graph-rebuild trigger**.
- [ ] Treat connector scans with zero source deltas as NO-OP, without needless inference, embedding, or graph computation.
- [ ] Make changed sources version-aware and diff-aware; don't silently delete originals when upstream sources disappear.
- [ ] Reuse original compatible text embedding space; do not combine embeddings from unrelated model versions or dimensions.

### A2. Incremental Skein as a versioned extension

- [ ] Preserve build_skein and the current full-build CLI as the tested, reproducible fallback. Do not switch current callers to incremental mode implicitly.
- [ ] Add optional incremental_v2 public API and feature flag with a stable, versioned stage contract and durable job identity.
- [ ] Persist content-addressed per-document extraction results using source revision, chunk checksum, extractor/model, prompt, schema and embedding-space identity.
- [ ] Compute a real source manifest; detect changed/deleted/replaced content (not merely row counts and maximum IDs).
- [ ] Retract stale evidence when a document changes while preserving facts/evidence supported by other sources.
- [ ] Recompute only affected entities, mention sets, relation candidates, embeddings and graph neighbors. Account for existing entities displaced from nearest-neighbor top-K.
- [ ] Stage a complete validated new derived generation and publish through an atomic pointer after quality and provenance tests. On failure the previous known-good generation stays queryable.
- [ ] Make stages checkpointable, bounded, quiet/pause compatible and crash-resumable. No partial corrupted graph advertised as complete.
- [ ] Introduce explicit owner-controlled full reconciliation, rollback and a comparison/quality report, but no mandatory full rebuild for small changes.

### A3. Connector add-ons

- [ ] Follow existing Source Watchtower adapter proposal: discover, list, get_metadata, fetch, delta_cursor, health, test, dry_run, schedule, pause, resume and optional export.
- [ ] Integrate existing GitHub/blog/local-file collectors where present rather than writing competing crawlers.
- [ ] Keep connector adapters isolated behind public contracts; changing a connector or connecting an AI client should not require replacing the Bifröst server or reprocessing unchanged knowledge.
- [ ] UI exposes New / Changed / Unchanged / Failed / Pending graph and a simple owner action: Update My Brain.

**Acceptance A:** Ten new documents process without repeated extraction of all unchanged documents; editing/deleting one document adjusts attributable evidence without erasing unrelated graph facts; reconnecting a client invokes zero corpus processing; SIGKILL and restart preserve completed checkpoints and the old published graph; full-build fallback still works.

## Track B: optional tokens that never expire

**Ownership:** bifrost-viewer security module and Settings UI. Keep backward compatibility with the existing 1-365 day API payload.

- [ ] Add an explicit opt-in "Never expires (until revoked)" selector alongside existing 1-365 day choices. Default remains 30 days.
- [ ] Prefer an additive boolean request field such as never_expires=true and keep days semantics unchanged for existing callers. Validate contradictory inputs; do not infer permanence from missing or malformed days.
- [ ] On explicit permanence, store expires=NULL. Audit existing authenticate/list_keys logic against NULL and revocation, and ensure revoked keys are rejected immediately.
- [ ] Keep delegated scopes limited to read or read+ingest; never delegate owner/admin privileges. All character clients using the shared gateway have read-only access to all second-brain knowledge through one gateway-owned read key; no per-character collection selection or setup required.
- [ ] Continue hashed-at-rest token storage, display-once issuance, per-key quotas, named key listing, last-used audit metrics and straightforward revocation. Avoid recording raw keys in logs.
- [ ] Create tests: omitted new field, finite 1/365 days, explicit never, expired, revoked permanent, invalid field values, legacy keys, UI refresh, gateway key rejection.
- [ ] Keep externally exposed Janitor/client gateway credential **separate** from the G14's permanent internal read-only Bifröst credential; compromised gateway access must not yield an owner/admin key.

**Acceptance B:** Owner can issue a named permanent read-only key, list it as never expiring, use it after mocked future dates, revoke it instantly, and issue ordinary finite-duration keys unchanged.

## Track C: built-in optional universal chat gateway

**Host:** Bifröst second-brain machine. **Inference:** existing Gufo service on a separate trusted Linux inference machine across Tailscale.

- [ ] Build a separate optional module/service under Bifröst ownership that can start on demand (systemd socket activation if compatible with the chosen ASGI server and public ingress). It must not hold a GPU model or duplicate the inference engine.
- [ ] Expose a minimal OpenAI-compatible chat-completions interface for supported clients, with model listing and streaming only after interoperability tests. Preserve character system instructions, role ordering, stop handling, context budgets and distinct sessions.
- [ ] Authenticate the public-facing gateway and constrain request size, concurrency, timeouts, stream duration and retrieval/context budget. Publish HTTPS only through an owner-approved, verified transport. Never expose Gufo, PostgreSQL or internal Bifröst credentials publicly.
- [ ] Retrieve passages and graph evidence only using the existing authenticated read API/Skry contracts, not with direct writes to source or derived DBs.
- [ ] Give ALL authorized characters the same read-only search coverage across the entire second brain. No per-character collections, new memory indexes, permissions profiles or connection-by-character setup. Retrieved passages remain attributed untrusted data, never system instructions.
- [ ] Feed only relevant retrieved excerpts into Gufo prompts, not wholesale corpus dumps. Preserve a record of retrieval provenance and separate sourced facts from heuristic graph edges.
- [ ] Keep Gufo model loading, upgrades, failure recovery and model IDs under its current service owner. Failure should return a truthful bounded error, not silently substitute a cloud model.
- [ ] Verify from Janitor AI's actual request origin whether its custom proxy is server-side, what HTTPS route/stream format it requires, and whether character data transits Janitor or another provider. Do not promise end-to-end local privacy when hosted clients participate.
- [ ] Reuse the same gateway for SillyTavern and future authorized companions as far as their interface capabilities permit.

**Acceptance C:** A Janitor test character retrieves a sourced fact through G14 Bifröst and receives a Gufo-produced reply from the other local machine; a different character needs no memory configuration; network loss/revocation/restart do not permit unauthorized reads or corrupt the source; optional gateway can be disabled without affecting existing Bifröst API/search.

## Track D: multimodal memory without re-ingesting all text

### D1. Data and provenance contracts

- [ ] Add optional derived asset/segment records referencing stable existing document/source IDs, with asset type, MIME type, original location, size, content hash, extractor/model/version, timestamp/time span/page/region, permissions, provenance and processing state.
- [ ] Keep originals in an owner-chosen local asset store with content-addressed immutable references; derived descriptions/transcriptions/embeddings must be regenerable without mutating original files.
- [ ] Use migrations that are additive, transactional, reversible or rolled back by verified backup; avoid coupling every search request to missing optional modality tables.
- [ ] Maintain separate model-vector-space identities for text, image, audio and video; allow a tested joint embedding model to offer text-to-image/video/audio retrieval. Do **not** assume existing text vectors and new visual/audio vectors can be directly compared.
- [ ] Choose Postgres/pgvector extension tables or another optional adapter only after benchmark and maintenance review; new separate vector database must not be a prerequisite for ordinary text access.

### D2. Modality phases

1. **Images and PDFs**: image metadata, thumbnails, perceptual duplication assistance, optional local captions/visual embeddings, page/diagram/table extraction with page/region citations; OCR errors labelled as machine output.
2. **Audio**: local transcription with timestamps and speaker label confidence, audio segments, track/song metadata, optional audio embeddings and links from transcript to the exact audio offsets.
3. **Video**: bounded scene/keyframe sampling, audio-to-transcript alignment, scene timestamps and optional joint video-text retrieval; avoid indexing every frame as a redundant document.
4. **Cross-modal retrieval**: one query may return passages, images, audio intervals and video scenes as a provenance-rich result set, ranked with calibrated per-modality scores.
5. **Client-specific response adaptation**: text-only Janitor character receives faithful textual descriptions and citations; clients that explicitly support media can receive links or native media outputs with authorization. Retrieval does not magically grant a client native image/audio/video display.

### D3. Incremental multimodal processing

- [ ] On each addition or revision, process only missing/changed assets, segments and dependent embeddings/graph evidence.
- [ ] Keep original text search working if a visual model, transcription worker or video processor is unavailable.
- [ ] Schedule heavyweight extraction separately from interactive inference, respecting available CPU/GPU, disk, power and quiet periods.
- [ ] No external processing or upload of private media without explicit owner opt-in and clear provider/retention visibility.

**Acceptance D:** Existing text index remains unchanged and searchable; one new image, audio track or video produces queryable, correctly attributed multimodal assets; unchanged files cause no duplicate embedding or graph rebuild; missing models degrade gracefully; deletion/revision updates only the relevant derived references.

## Cross-repository implementation boundaries

| Owner | Implementation responsibility |
| --- | --- |
| bifrost-viewer | API admission, permanent-token UI/API, job orchestration, optional gateway, multimodal query response, public connection guide |
| bifrost-viewer/ingest | Canonical source and revision writes, multimodal extraction/asset metadata, content deduplication and watcher bridge |
| skein-kg | Opt-in incremental graph generation, extraction caches, provenance, staging, checkpoint and fallback |
| skry-kg | Read-only hybrid and cross-modal query-time relationships through versioned APIs |
| RuneForgeAI-Project-Aesir / Gufo service owner | Independently managed local inference; model/service integration compatibility, not a takeover of the Bifröst corpus |
| kista (optional) | Precisely scoped secret references where owner enabled, never searchable secret material |
| Other connected agents | Optional consumers of documented read-only API; preserve independent character logic |

Consult each repository's own README_AI, PROJECT_LAWS, domain map, master-roadmap mirror and repository-specific BIFROST_INTEGRATION_RESPONSIBILITIES before editing its code.

## Execution order and release gates

- [ ] **0 Discovery/backup**: installed state, existing works-in-progress, real restore drill, baseline benchmark and tests.
- [ ] **1 Minimal additive key capability**: permanent read-only key through API, Settings UI, docs and tests; no implicit change to existing credentials.
- [ ] **2 Incremental Skein prototype**: a separate feature flag and cloned/synthetic DB tests; preserve original API and full build.
- [ ] **3 Staged incremental source-to-graph pipeline**: manifest, evidence retraction, checkpoint/rollback, quality comparison and UI status.
- [ ] **4 G14 optional Gufo gateway**: read-only Bifröst API, separate public auth, HTTPS, bounded retrieval, real Janitor compatibility test.
- [ ] **5 Multimodal foundation**: asset records and image pilot, followed by audio then video and fused retrieval.
- [ ] **6 Deploy by explicit owner approval**: backup, release notes, feature toggle, health monitoring, disabled-by-default migration behavior and tested rollback.

## Evidence and status rules

This addendum is a design and test specification. **No running feature is proven implemented by committing this document**. Keep roadmap status separate from merged code, passing tests and actually deployed versions. Do not push credentials, runtime dumps or private user data. Never run destructive database operations or update the live server based solely on the existence of this plan. Any conflict with the current implementation or project laws must be surfaced, resolved, reviewed and regression-tested before merge or deployment.

## Source-of-truth links

- [Canonical master roadmap](BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md), especially sections 3, 5, 8 and 13.
- [Cross-repository index](SECOND_BRAIN_CROSS_REPOSITORY_INDEX_2026-11-04.md).
- [Bifröst implementation responsibilities](BIFROST_INTEGRATION_RESPONSIBILITIES_2026-11-04.md).
- [Skein implementation responsibilities](https://github.com/hrabanazviking/skein-kg/blob/main/docs/roadmaps/BIFROST_INTEGRATION_RESPONSIBILITIES_2026-11-04.md).
- [Skein's original immutable project laws](https://github.com/hrabanazviking/skein-kg/blob/main/PROJECT_LAWS.md).
- [Bifröst security technical manual](../../security/TECHNICAL_MANUAL.md) (relative path from this addendum; check rendered link).
- [Bifröst AI connection guide](../../AI_CONNECT.md) (relative path from this addendum; check rendered link).
