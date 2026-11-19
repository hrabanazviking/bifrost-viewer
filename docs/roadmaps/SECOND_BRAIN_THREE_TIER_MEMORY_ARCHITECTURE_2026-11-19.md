# Bifröst Second Brain: Immutable Long-Term, Focused Medium-Term, and Ephemeral Short-Term Memory

**Owner decision:** 2026-11-19  
**Status:** Authoritative design requirement, implementation NOT yet deployed  
**Canonical companions:** [Master expansion roadmap](BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md), [additive and multimodal plan](SECOND_BRAIN_ADDITIVE_INCREMENTAL_MULTIMODAL_GATEWAY_2026-11-19.md), [managed raw library and folder provenance](SECOND_BRAIN_MANAGED_RAW_LIBRARY_FOLDERS_2026-11-19.md).

## 1. Owner's three tiers (normative)

**LONG-TERM:** stable, permanent and **immutable after commit**. Neither clients, reinforcement, background workers, reclassification, model changes nor user interface edits may alter an accepted long-term record in place. Historical versions stay exact, with verifiable provenance. New evidence, revisions, retractions or corrections are represented by NEW linked immutable entries; the authoritative-current view may point to a superseding entry without modifying the original record.

**MEDIUM-TERM:** the changing **current focus domains**: active projects, research topics, focus folders, ongoing creative work, current workstreams, and temporary priority/recall relationships. Its focus assignments, weights and memberships are reversible and adjustable. It references existing immutable long-term records through stable IDs; it does not duplicate, rewrite or delete them. Medium-term records can be created or deactivated as focus changes.

**SHORT-TERM:** rapidly changing working memory used only for an immediate conversation, task or processing session. Its content expires and is purged; it does **not** last by default. Working-context state is isolated by session/request, bounded by token/byte budgets and a configurable short TTL, and explicitly cleared at conversation/task end. Avoid persistently recording transient chat content in general logs, audit payloads, permanent graph tables, or backups. Keep diagnostic metadata redacted/non-content-bearing if needed.

A tier describes **retention/mutability**, not a physical directory, model context window, GPU assignment or a new separate full database. All tiers participate in one authenticated read-only knowledge retrieval interface. All authorized Janitor AI/SillyTavern character clients continue to have the SAME broad read-only access to the entire Second Brain with **zero per-character collection/permission configuration**. Medium focus may adjust relevance/ranking, but must not hide the rest of the brain.

## 2. Proposed architecture: one G14 knowledge system

```text
AUTHORIZED CLIENTS: Janitor AI / SillyTavern / other programs
                   |
             Bifröst API Gateway (read only)
                   |
             Memory Composer / Retriever
               |         |          |
               v         v          v
           SHORT-TERM  MEDIUM-TERM  LONG-TERM
            working    focus map    append-only
             context     & links     canonical knowledge
               |         |          |
               +---------+----------+
                   |
          Skry read-only evidence lookup
          Skein derived graph generations
          optional Ravens association enrichment
          optional HugrGate decisions
                   |
        Z13 Gufo optional inference worker
```

**Bifröst Viewer:** memory composition/orchestration, owner UI, authentication, source provenance and append-only policy. **Ingest:** sole canonical source/version writer with immutability enforcement. **Skein:** produces derived graph generations and evidence references, not mutations to archived facts. **Skry:** read-only retrieval. **Ravens:** optional ephemeral/medium associative activity, never mutable canonical long-term content. **HugrGate:** optional confidence-aware triage and promotion candidate recommendation, never unilateral archival commitment. **Gufo:** inference/caption/embedding worker, never DB owner.

## 3. Long-term memory contract: immutable means immutable

- [ ] Write-once committed version: use DB-enforced permissions, append-only history tables and integrity checks so UPDATE/DELETE of accepted content is denied to ordinary application roles, including batch processing or model workers.
- [ ] Versioned, content-addressed immutable sources: `memory_id`, `revision_id`, original source/version ID, raw-byte hash, extracted-content hash, modality, origin/folder reference, ingestion time, evidence IDs, model/extractor schema identity and owner-authorized commit event.
- [ ] Explicit `supersedes`, `corrects`, `contradicts` or `retracts_as_current` links in NEW records. Current retrieval follows an index/manifest of the latest accepted validity without rewriting old record bytes.
- [ ] Preserve original raw asset snapshots as protected immutable versions after archival. The owner may still move/edit files in RawLibrary; any changed content ingested from these mutable filesystem sources yields a NEW immutable long-term revision rather than overwriting prior versions.
- [ ] **Location metadata is intentionally separate from immutable knowledge.** Owner moves/renames a file: change current source-instance path and folder/category association in the mutable provenance ledger, never the archived content snapshot. An original archived path is recorded within the historical snapshot and kept unchanged. Copies into multiple folders retain all current associations.
- [ ] Image descriptions/structured traits and verified corrections are individually versioned. If a new vision model changes its interpretation, archive a new derived annotation linked to the original image; do not silently replace its approved canon.
- [ ] Skein graph and retrieval indexes may be recalculated and republished as derived immutable generations; this does not rewrite long-term fact records. Changed current interpretations link back to which original archived evidence supported them.
- [ ] Backups and restore verify archive content hashes, append-only lineage, previous versions and current supersession index. Logs do not contain raw keys or private text. Immutable does not mean impossible to administratively recover from corruption: owner-controlled repair is a distinct audited disaster-recovery path, never ordinary memory editing.
- [ ] Keep an owner-visible **Archive/Commit to Long-Term** function. Routine ingestion of accepted reference sources may go directly into long-term as new immutable versions, but temporary conversation content is NEVER silently promoted merely because it was discussed.

## 4. Medium-term memory contract: current focus domains

- [ ] Focus records identify `focus_domain_id`, title, associated folder subtree or project/category, linked long-term evidence/visual references, current priority, activation strength, optional focus expiration, owner-pinned status and revision times.
- [ ] Change domain weights, project focus, membership and associations freely without altering long-term corpus. Use named actions such as `set_focus`, `pin_focus`, `deactivate_focus`, `link_evidence`, `change_priority`.
- [ ] Discover candidate focus domains from owner folder categories, active work and recent consensual interactions; suggest rather than silently turning inferred sensitive/personal text into permanent canon.
- [ ] Retention is **bounded and configurable**: active focus persists while useful and may be manually pinned; inactive items decay or retire according to owner-selected rules. No arbitrary fixed number of days is imposed as the universal definition of "medium".
- [ ] Ravens/Muninn (optional) co-activation and Hebbian strength/decay can enhance focus ranking and association suggestions. It MUST NOT decay, change, prune or delete canonical long-term records. The association ledger is an auxiliary mutable state, separate from the archive.
- [ ] Folder categories are explicit owner taxonomy and can be active focus domains without per-client collection restrictions. Reparenting categories affects focus/context lookup only, not content re-embedding.
- [ ] Changing the current focus never triggers a corpus rebuild. It updates a small mutable table/materialized view or cache.

## 5. Short-term memory contract: do not last

- [ ] Session/request scoped working memory only: recent turns, current user goal, immediate task state, scratch observations and transient retrieval traces.
- [ ] Default process memory or bounded volatile store with TTL and explicit purge on end/reset; if restarts occur, short-term memory disappears by default. Any opt-in durable session recovery must be clearly distinct and separately consented to, not silently enabled.
- [ ] Separation by session ID to avoid one character conversation leaking into another; the same read-only second-brain access rights still apply to all authorized characters.
- [ ] Short-term state never becomes canonical through passive reinforcement, cache flush, trace collection, event replay, error logs or automatic backup. If data is promoted to medium or long term, do so via a separate explicit owner-approved action and record its source/context.
- [ ] Retain only non-content-bearing operational metrics where necessary; no raw ephemeral prompts or responses in long-lived system logs.
- [ ] A hosted external platform, such as Janitor AI, may independently retain its own chats; this plan guarantees only the behavior of Bifröst-managed short-term storage, not third-party services.
- [ ] On expiration, purge plaintext and session-specific caches where supported; separate retrieval cache policy must never preserve the complete session transcript indefinitely.

## 6. Promotion, demotion, correction and retrieval semantics

| Transition/action | Allowed system behavior |
| --- | --- |
| Short-term expires | Purge transient context; no promoted record created |
| Short-term becomes medium focus | Create a new mutable focus-domain/working-summary entry ONLY after an explicit approved promotion action |
| Medium focus becomes long-term | Archive NEW owner-approved immutable evidence/version; linked original source. Never move a mutable object into archive with unrestricted UPDATE access |
| Long-term becomes medium focus | Add a pointer/category/priority in medium tier; do not copy or edit the archived item |
| Medium focus deactivates | Remove or decay focus weights; long-term evidence remains fully searchable |
| Long-term evidence is corrected | Create a new immutable correction/supersession entry; current search resolves active validity while preserving historical record |
| Original RawLibrary file moves | Update mutable path ledger and category links, not the archived content |
| Original file changes | Detect delta; create new immutable source version, reprocess changed segments, publish new derived graph generation |
| Same raw content in another folder | Share compatible content-derived work; add independent current folder association |
| Visual image updated/re-captioned | Version the analysis, preserve original image and owner-approved identity canon |

**Search merge policy:** Short-term context first for immediate coherence; medium-term focus boosts relevance; long-term archive supplies stable grounded facts and evidence. Do not allow recent unverified working context to silently override accepted long-term truth. Present contradictions with clear provenance and supersession; expose `tier`, `source_id`, `revision_id`, `last_revised`, `expiry` (when applicable), `currentness`, and `confidence` where available.

**Uniform access:** No per-character memory collection selection. One gateway policy and one read-only bearer credential grant the same searchable archive and focus to all authorized private characters. Session short-term buffers are isolated by conversation for correctness, **not** separate collection permissions.

## 7. Read/write isolation and permissions

- Read-only external characters can query all authorized tiers but cannot create, edit, expire, promote or delete any tier's records through the gateway.
- Dedicated internal Ingest/owner workflows can append new immutable long-term versions; ordinary model endpoints cannot. Service-to-service long-lived API tokens may be revocable but never-expiring.
- Medium focus can be managed by owner and explicitly authorized trusted internal orchestration; never confuse its changes with source content edits.
- The G14 controls all memory storage. Gufo on the Z13 receives only needed prompts/media data for authorized inference; it does not store or reassign tier policy.
- HugrGate may classify a candidate and abstain, but may not bypass archive approval. Ravens may update its own co-activation store through trusted internal jobs; such updates are not available on read-only external character endpoints.
- Cross-tier audit must log safe identities, actor, action, timestamp and reason without persisting short-term chat contents.

## 8. Proposed implementation schema (illustrative only)

```text
lt_memory_versions(id, source_id, revision_id, content_hash, modality,
                   origin_id, archived_at, provenance_manifest, immutable_payload_ref)
lt_correction_links(id, from_version_id, to_version_id, relation_type, recorded_at)
lt_currentness_index(source_id, current_version_id, evaluated_at)
mt_focus_domains(id, title, status, priority, pinned, active_since, expires_at)
mt_focus_links(domain_id, source_id, memory_version_id, folder_id, weight, updated_at)
mt_associations(domain_a_id, domain_b_id, strength, last_activated)
st_sessions(session_id, deadline, bounded_volatile_context)   # volatile only
```

Prefer integrating these concepts into existing schema and APIs using additive migrations, not making the illustration into a mandate for seven independent tables. Long-term accepted payload rows are write-once; correction links and currentness pointers are append-only or separately mutable metadata, not modifications to immutable payloads.

## 9. Owner-facing interface

- **Memory Atlas:** three tiers visibly distinguished, with long-term locked, medium-term editable focus, short-term TTL/clear.
- **Long-Term Archive:** browse sources, image lore, immutable snapshots, revisions and explicit supersessions.
- **Current Focus:** add/remove/pin project domains, select existing folder categories, adjust priority, and see what changed without rebuilding.
- **Working Context:** show active session memory, short retention setting, "Clear Short-Term Now", expiration and no-persistence state.
- **Promote:** explicit selected facts/media from working context or focus to immutable archive, review preview and provenance.
- **Tier health:** total stored immutable records, active focus domains, volatile session count, conflict and supersession notices; do not expose temporary content in persistent telemetry.

## 10. Acceptance and adversarial testing

1. An immutable archived record rejects ordinary UPDATE/DELETE through all public/worker service paths, including a compromised read-only gateway token.
2. Correction and supersession preserve the bytes/hash of the old archive version; current view references the newer accepted version.
3. Change/move/copy of a RawLibrary file updates only delta-derived source/version/path metadata; archived source snapshots remain unchanged.
4. Medium focus is changed, pinned, deactivated and reactivated with no graph rebuild and no archive write.
5. Short-term working context expires and clears, does not survive a default restart or leak through backed-up files, logs or unrelated sessions.
6. Same read-only gateway supports two different Janitor/SillyTavern characters without separate memory collection permissions, while individual short-term session state remains isolated.
7. Ravens decay/reinforcement affects only authorized mutable association data and leaves long-term payload untouched.
8. HugrGate abstention or uncertain labels cannot silently write accepted archive facts.
9. Visual lore retrieved for image generation respects owner-approved immutable canonical reference versions; generated image outputs are not promoted automatically.
10. Backup/restore preserves original archived versions, currentness links, medium-term focus as configured, and proves ephemeral short-term content is excluded.
11. Full-text, embedding and graph retrieval continues to work with optional three-tier module disabled; initial migration does not destructively rewrite existing Postgres source data.

## 11. Rollout and documentation distribution

Owner-approved new requirements supersede contradictory older assumptions while preserving current working API compatibility. **No automatic code deployment** from a planning document.

Work in Bifröst Viewer/Ingest first: audit existing schemas/retrieval, backup+restore, data-model constraints, API versioning, UI and migration design. Add a **thin, optional composition adapter** for Ravens, not a new full knowledge DB, and optional HugrGate judgment gates. Extend Skein/Skry only as needed for tier tags, immutable source-version evidence and focus-aware read-only queries. Benchmark correctness and latency on actual G14/Z13 machines, then roll out with explicit owner approval and tested rollback.

**Single canonical source of truth:** this Bifröst Viewer design. Other project repos link here and document their own narrowly scoped responsibilities. Avoid copying full master documents across projects or treating roadmap presence as proof of deployed features.
