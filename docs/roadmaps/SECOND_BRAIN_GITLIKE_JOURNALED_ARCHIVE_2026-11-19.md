# Bifröst Second Brain: Journaled, Versioned and Branchable Long-Term Memory

**Owner decision:** 2026-11-19  
**Status:** Design specification, NOT a shipped Bifröst feature  
**Canonical predecessors:** [Three-tier memory architecture](SECOND_BRAIN_THREE_TIER_MEMORY_ARCHITECTURE_2026-11-19.md), [managed raw library](SECOND_BRAIN_MANAGED_RAW_LIBRARY_FOLDERS_2026-11-19.md), [incremental/multimodal roadmap](SECOND_BRAIN_ADDITIVE_INCREMENTAL_MULTIMODAL_GATEWAY_2026-11-19.md).

## Owner goal

Add a **journaling/versioned long-term archive with Git-like commits, history, rollback, branches, merges and owner-controlled review**. Model these after standard Git and optionally connect to [RuneForgeAI-Samverk](https://github.com/hrabanazviking/RuneForgeAI-Samverk) as a separate, independently maintained local Git forge. Every accepted long-term fact, image, original document snapshot, visual-lore annotation and canonical metadata version remains **immutable**. Editing a file or correcting a belief creates a **new** immutable version and moves a **mutable reference** to it, never overwrites the earlier version.

Short-term stays genuinely ephemeral and medium-term stays mutable current focus. A journal must NEVER silently turn short-term sessions into permanent memory. All authorized Janitor AI/SillyTavern private characters retain one uniform read-only search of the whole Second Brain, without per-character corpus tuning.

**Explicit terminology:**

1. A **journaling filesystem** (e.g., ext4 filesystem journal) primarily helps recover consistent filesystem metadata after interruption. It does NOT automatically provide a complete source history, branch merges, long-term semantic versioning or reliable backups.
2. A **database WAL** (PostgreSQL write-ahead log) supports crash-safe transactions/PITR when configured. It is not an owner-visible semantic memory journal or a replacement for versioned source identities.
3. An **append-only application event journal** logs who added/corrected/branched/merged/rolled back which immutable memory version, when, and under what authorized action.
4. A **Git-like commit DAG/refs layer** creates snapshot manifests and branch heads. It lets Bifröst show historical views and select current knowledge versions without changing archived payloads.
5. **Filesystem snapshots and real backups** are separate recovery mechanisms. Consider Btrfs/ZFS snapshots only after verifying the actual G14 filesystem and backup consistency; do not assume the G14 uses either. Snapshot alone is not a verified off-device backup.

## How Samverk fits, based on inspected source

Samverk is a clean-room, AGPL-3.0 Git forge. Its public source currently includes **standard Git object/commit reading** (`samverk/objects.py`), **branch references with compare-and-swap** (`samverk/refs.py`), **revert commit generation** (`samverk/revert_git.py`), **merge operations** (`samverk/pull_request_merge.py`), **audit-derived event history** (`samverk/event_store.py`), **LFS storage** (`samverk/lfs_store.py`) and **Git bundle exports** (`samverk/repo_backup.py`). The repository's November 13 README progress audit reported S-304/416 planned slices, meaningful backend test coverage, and an incomplete composed production-facing HTTP application. Reaudit current code and deployment before relying on a Samverk server or workflow.

**Integration decision:** Samverk is an optional Git-native *version-control/review/synchronization provider*, NOT the mandatory Bifröst database, not a replaceable Postgres transaction manager, and not a reason to duplicate the corpus. Bifröst's first implementation can provide the commit DAG/journal in its own source/version metadata tables while allowing optional signed manifest export or integration through supported Git CLI / audited Samverk APIs. Do not import AGPL-licensed Samverk implementation modules into MIT-licensed Bifröst without an explicit license/composition review; a separate process/service or ordinary Git interoperability may be the cleaner boundary.

## Target layout and storage responsibilities

```text
G14 BIFRÖST
├── Owner-managed RawLibrary/                # files may be edited/moved by owner
│   └── nested folder/category hierarchy
├── Protected long-term object archive       # immutable content-addressed originals
│   ├── documents, images, audio, video, visual lore versions
│   └── checksums + original metadata
├── PostgreSQL/pgvector                      # canonical source versions, searchable chunks
│   └── versioned derived Skein graph generations + Skry retrieval
├── Long-term change journal                 # append-only audit of accepted actions
│   ├── journal events and chain commitments
│   └── named checkpoints
├── Memory commit DAG                        # immutable manifests, parent commit IDs
│   ├── main branch -> latest approved canonical view
│   ├── research/* -> alternate hypotheses/interpretations
│   ├── characters/* -> proposed visual lore/identity revisions
│   └── recovery/* -> inspected restore candidates
├── Mutable ref/currentness ledger           # authenticated compare-and-swap branch heads
├── Medium-term focus                       # points to accepted branch and immutable IDs
├── Volatile short-term session contexts    # NOT written to journal or backed up
└── Optional Samverk adapter                 # versioned manifest Git export/review only
```

The physical raw-file folder hierarchy is a user-authored **taxonomy**, not a Git branch by itself. Moving a file updates the live path ledger and folder-category association. The original archived version's bytes, provenance and historically recorded path are never edited. Branches select different **knowledge revisions**, independent of physical folder movement. A source may appear in multiple folders without duplicating content embeddings or archived payload.

## Journal record contract

Each durable *long-term archival event* records an append-only event envelope:

```text
event_id, event_type, actor_id/role, authorized_action_id,
occurred_at, source_instance_id, previous_version_ids,
new_immutable_version_ids, affected_folder_ids, model/extractor IDs,
parent_commit_ids, resulting_commit_id, previous_event_hash,
event_payload_digest, event_hash, validation_status
```

Only explicitly accepted long-term events enter this journal: `archive_source`, `append_correction`, `commit_visual_lore`, `merge_accepted`, `advance_branch`, `revert_view`, `tag_checkpoint`, `restore_verified`. Focus priority changes may use their own medium-term activity log with retention. Do not log short-term transcript, raw model prompts, secrets or temporary personal conversation content as journal payload.

- [ ] Transactions bind archive record creation, journal append and currentness/ref update as one logically atomic operation. When blob/object storage and PostgreSQL span separate mechanisms, stage immutable payloads and use durable two-phase publish/checkpoint protocol with idempotent recovery. No event advertises a nonexistent blob.
- [ ] Journal hashes/checksums, timestamps and monotonic sequence detect accidental corruption, gaps or unauthorized rewrite. Hash chaining alone is not a substitute for external anchoring or access control against an attacker able to rewrite both data and hashes.
- [ ] Audit authorized actor, reason, source provenance, previous and new commit IDs. Validate content hashes before read and after backup restore. Rotate event logs safely without losing verifiable chains.
- [ ] Optional authenticated signatures/checkpoint anchors can establish stronger provenance. Never claim cryptographic immutability merely from SHA-256 hashing.
- [ ] Ensure archive objects are write-once at the app's service-role/DB-trigger level. Recovery/repair is a separate, audited privileged path. Existing read-only API tokens do not gain new commit/edit permissions.

## Commit DAG and branch model

```text
memory_commits(commit_id, parent_commit_ids[], root_manifest_digest,
               journal_event_range, created_at, author, reason, validation)
memory_manifests(manifest_id, entry_ids[], folder_category_state_ref,
                 active_source_version_ref, graph_generation_ref)
memory_refs(ref_name, head_commit_id, ref_generation, updated_at)
memory_ref_events(event_id, ref_name, old_commit_id, new_commit_id, actor, reason)
long_term_versions(version_id, source_id, original_object_hash, model/provenance, accepted_at)
corrections(old_version_id, new_version_id, relation, commit_id)
```

These are *illustrative* shapes to map onto existing Bifröst tables with additive migrations, not a prescription to create a separate Git clone/database for every memory. Commit manifests reference immutable source versions and derived generations, not duplicate source bytes. Avoid storing the full Postgres vector corpus or every frequently changing index in Git.

- [ ] **main:** canonical approved current view. Only explicitly authorized Ingest/owner operations can advance it. Protect against force resets/hidden history rewrites.
- [ ] **topic/research branches:** experimental interpretations, unresolved competing hypotheses or alternate extraction settings. Branch creation is metadata-only; creating a branch does not copy all images/documents/embeddings.
- [ ] **character/visual lore branches:** alternate portrait interpretations, style or identity corrections without mutating owner-approved current canon. Require review before promotion to main.
- [ ] **as-of query:** search historical commit or timestamp, with exact provenance. A view is only valid if its referenced source versions and derived indexes exist or can be reproducibly reconstructed.
- [ ] **merge:** compare changed source-version references, category associations, corrections and canonical trait assertions; detect and show conflicts rather than auto-choosing a winner by model confidence. Make a new merge commit with parents, actor and review evidence.
- [ ] **revert/rollback:** propose a NEW commit on main restoring a previously valid manifest/currentness state. Never delete, rewrite or orphan the original later history. Optionally create a named recovery branch first. Do not confuse rollbacks of a knowledge view with physical rewinding of PostgreSQL via PITR.
- [ ] **compare:** readable changes between commit A and B with added sources, corrected facts, folder movements, image trait modifications, model version changes and affected derived graph edges, linked to original evidence.
- [ ] **concurrency:** branch-head updates require expected-old-head compare-and-swap; stale editors receive a conflict/retry, not last-write-wins.
- [ ] **protected retention:** keep reachable immutable objects and archived superseded versions according to owner long-term permanence. Garbage-collection must NEVER remove history simply because a branch moved. Backups cover all object archive and refs.
- [ ] **permissions:** external character clients see main by default, or an explicitly owner-chosen published view through the SAME broad read-only gateway credential; no per-character collection profiles. Optional branch preview is separately authorized and never defaults to exposing unapproved draft lore through hosted clients.
- [ ] **derived data:** Skein graph generations indexed by canonical commit/manifest, not silently updated in place. Skry must return `commit_id`, `source_version_id`, `graph_generation_id` where available. Incremental graph recomputation examines branch delta and affected entities only. Cached embeddings shared among branches for identical content with same embedding space/model identity.

## Long-term / medium-term / short-term integration

- **Long-term:** objects and accepted versions remain immutable, journal retains accepted changes, branch/currentness pointers change under authorization. Corrections add new immutable entries. A rollback is a pointer/view transition committed to history.
- **Medium-term:** current project/folder focus is mutable and MAY point at a selected long-term branch/commit. Focusing on a subject changes ranking/priority without rewriting content or generating a branch for every fleeting attention change.
- **Short-term:** volatile session buffer, no journal or snapshots, no default persistent event export. It can query approved long-term versions but does not create permanent records. Only explicit owner-authorized promote/archive creates a journaled commit.
- **Ravens:** optional association weights/decay remain auxiliary medium-term state and do not mutate long-term commits/objects. **HugrGate:** optional classification and proposed merge/conflict triage, not authorized to perform irreversible promotion without owner acceptance. **Gufo:** optional inference to propose candidate analyses without writing archived records.

## Three distinct kinds of rollback

1. **Knowledge view rollback (routine):** append a new commit pointing to an earlier accepted manifest; keep all later immutable knowledge in history.
2. **Derived graph/index rollback (automated recovery):** atomically repoint from a failed/new graph generation to a last-known-good compatible generation; no canonical source history changed.
3. **Storage disaster recovery (rare):** consistent PostgreSQL base backup + WAL/PITR, object store backups, journal/ref manifests, cryptographic checksums and full restore drill. If the G14 filesystem supports Btrfs/ZFS, coordinated filesystem snapshots can reduce local recovery time, but neither FS journaling nor snapshots replace backups.

## Samverk optional module architecture

- [ ] Build an independent adapter that exports/imports signed or hashed *manifest/metadata representations* (text/JSON/Markdown), tags, branch/merge metadata and optional owner-selected original source assets through Git/LFS on a separate local Samverk instance.
- [ ] Keep archive main source of truth under Bifröst; Samverk provides optional human-friendly Git history/diffs/reviews, backup/mirror of exported manifests, and a collaborative review interface when its API/UI is actually operational.
- [ ] Use standard Git plumbing directly for an MVP if suitable; it is not necessary to wait for all Samverk server milestones. Any API use must be verified against released/deployed endpoints, not merely classes present in source.
- [ ] Do **not** make Samverk mandatory for Bifröst start, read-only search, ingestion, rollback or recovery. If Samverk is offline, the journal/commit DAG, authenticated API and long-term archive continue to operate.
- [ ] Review AGPL-3.0 (Samverk) / MIT (Bifröst) boundary and attribution before copying or directly importing code. Prefer interoperable Git CLI or separate service boundary unless the owner explicitly chooses a compatible licensing arrangement.
- [ ] Avoid stuffing large binary model files, image generations, videos, PostgreSQL WAL, or pgvector index files into ordinary Git objects. Use content-addressed archive plus only optional references/approved Git LFS assets.
- [ ] Public repo docs contain architecture only, never raw private memories, family data, exact host paths or secret connection info.

## Owner-visible UI

- **Memory History** timeline with commits, actor, reason, source/version counts and affected graph generations.
- **Browse as of** a chosen date/commit; search past knowledge with historical source+visual-lore provenance.
- **Branches** list, create, compare, review, merge, archive proposals; owner can pin verified checkpoints.
- **Rollback Preview** shows current vs target commit, what current knowledge view and folder category associations would change, and what content remains permanently preserved. Requires explicit owner approval.
- **Visual lore evolution** compare original/correction and approved current canon image descriptions/structured traits, with source image references and confidence labels.
- **Recovery** verified backup age, journal chain status, last successful checkpoints, database/object-manifest consistency and restore instructions.

## Acceptance tests, before rollout

1. Three sequential long-term commits: prior original payload bytes and hashes remain unchanged. A correction references a new immutable version, and as-of lookup resolves old/new exactly.
2. Create two branches with competing interpretations of the same image. Both remain accessible for owner review, main stays unchanged until explicit merge, with detected conflicting canonical traits.
3. Merge creates a new commit with two parents and accurate provenance; conflict cannot be silently overridden by LLM output.
4. Roll main to an older verified snapshot: NEW revert/restoration commit created, original later commits still queryable, current view matches target, no source rows or original objects deleted.
5. Make duplicate raw-file copies in two folders and then move one: one shared content-derived representation, all current path associations correct, archived historical path remains unchanged and model calls remain zero.
6. Run an unchanged ingest scan and a medium focus change: zero new long-term commits, zero Gufo calls and zero full Skein graph rebuild.
7. Kill worker between object staging, journal append and ref advancement: recover idempotently with no broken manifest, orphan published head or missing evidence; last known-good view remains available.
8. Two simultaneous writers to the same branch: one compare-and-swap succeeds, other gets actionable stale-ref conflict.
9. Disconnect optional Samverk: Bifröst ingestion, archive, search, branches and rollback work normally.
10. Configure hosted Janitor character gateway and confirm only read-only current main view access unless an owner-approved shared preview policy says otherwise; no exposed write API or private Samverk credential.
11. Expire/clear short-term session: sentinel transcript absent from long-term journal, Git manifests, Samverk exports, snapshots and backups. Verify no implicit promotion.
12. Restore the G14 brain onto an isolated test environment using documented PostgreSQL, object archive, journal, refs, and compatible derived generations; verify checksums, history and current view. A copied filesystem snapshot alone does not pass.

## Rollout sequence

1. Audit actual G14 filesystem/Postgres layout, current source identities, backup state, immutable versioning mechanisms and Samverk repository/app state; gather real benchmarks.
2. Build and test protected append-only source/object archive and semantic event journal with crash-safe publication; source original backups first.
3. Versioned manifests, commits, branch refs and as-of reader with compare-and-swap. Keep existing `main` search and ingestion routes backward-compatible.
4. Incremental branch-aware Skein graph generation and Skry provenance reads.
5. Owner UI history/compare/revert/merge, branch permissions and approved visual-lore proposals.
6. Optional Samverk interoperable Git manifest adapter and verified mirror/restore flow. Bench disk growth, dedup, startup/search latency and resilience.
7. Stage backups and restore drills; production enablement only after explicit owner authorization.

**No live code, installed storage layout, or physical backups are modified by this roadmap.**
