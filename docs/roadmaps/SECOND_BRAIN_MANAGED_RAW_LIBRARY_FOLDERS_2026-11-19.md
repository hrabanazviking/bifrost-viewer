# Bifröst Second Brain: Managed Raw Library, Folder Categories and Delta Ingestion

**Date:** 2026-11-19  
**Status:** Proposed additive design and test specification; NOT a deployed feature  
**Authorities:** [November 19 modernization addendum](SECOND_BRAIN_ADDITIVE_INCREMENTAL_MULTIMODAL_GATEWAY_2026-11-19.md), [canonical master roadmap](BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md).

## The owner's requested experience

The G14 Second Brain gains an ordinary owner-managed, nested raw-file library. The owner creates folders and copies or edits source files there. Bifröst offers **Ingest New Files**: a manual, recursive, incremental scan that discovers new files, reconciles previously seen files, incorporates changes, captures their folder hierarchy as additional knowledge categories, and updates changed file locations. It NEVER clears or rebuilds the entire corpus merely because the library was rescanned. Original files remain where the owner placed them.

**The owner explicitly requires all three:**
1. **Duplicate recognition:** identical data found again should not cause repeated embedding, parsing, visual analysis, LLM extraction or graph reconstruction.
2. **Changes-only processing:** for edited content, identify the changed parts and reprocess only affected segments and dependent relationships. Unchanged segments/cache are reused when extraction semantics allow it.
3. **Folder/path awareness:** if the same file appears in another folder, update its recorded file location(s) and category relations, not its existing content-derived knowledge. Never lose the old location if two independent copies still exist.

The system must distinguish **moved** files (a previous path disappeared and a newly detected path holds the same identity/content), **copied** files (old and new paths both exist), **edited** files (existing identity/path, new content), and **new independent files with identical bytes** (different provenance, same reusable content payload). Do not guess a move or delete a source merely because a drive is temporarily disconnected.

## Three-tier relationship to this raw library

Folder-organized source files are **user-managed mutable inputs**. A file may be edited, copied or moved without mutating the **long-term immutable archived version** previously accepted into the brain. New file content produces a **new versioned immutable long-term entry**; current source-instance paths and categories are mutable provenance pointers. Folder/project subtrees can activate **medium-term focus domains** without duplicating permanent knowledge. A newly scanned file is not a temporary **short-term session** merely because it was recently seen; short-term holds only volatile task/conversation context and is purged. All principles and gates: [Three-Tier Memory Architecture](SECOND_BRAIN_THREE_TIER_MEMORY_ARCHITECTURE_2026-11-19.md).

## Connection to immutable journal and branches

The owner approved [Git-like Journaled Long-Term Memory](SECOND_BRAIN_GITLIKE_JOURNALED_ARCHIVE_2026-11-19.md). RawLibrary files are editable/movable physical inputs while archive versions are immutable. Changed bytes or newly accepted interpretations add new archived versions and journaled commits, preserving previously committed evidence. Unchanged duplicate scans/moves create **no new content commit**, but legitimate path/category reference updates may be recorded in a separate mutable source ledger/audited metadata event. Branches represent different knowledge-view heads; branches are NOT filesystem folders. Rollback to a previous known-good *view* adds a restoring commit, never destroys original content. Exclude temporary short-term sessions from the permanent journal.

## Existing repository reality

- `scripts/watch_inbox.py` currently polls the inbox with top-level `iterdir()`, calls the existing ingest CLI, and moves completed jobs into `processed/`. Preserve this workflow unchanged.
- `ingest/ingest.py` deduplicates using a SHA256 of extracted chunk text, then `ingest/schema.sql` enforces uniqueness on `documents.hash`. Existing `documents.metadata` is JSONB. Thus the current source table cannot on its own represent every path/category association for multiple identical files. Adding another path string to the document metadata alone is insufficient.
- The master roadmap's Source Watchtower already proposes revision-aware sources, stable identity and deltas. Extend that architecture instead of creating a competing watcher or a new database by default.

## Proposed owner-facing filesystem

Illustrative, user-configurable location (NOT a discovered current filesystem path):

```text
SecondBrain/
  RawLibrary/
    Norse_Paganism/
      Runes/
        runic_notes.md
      Seidhr/
        ritual.pdf
    AI_Development/
      Gufo/
        gufo_notes.md
      Agents/
    Characters/
      Yrsa/
        Portraits/
          reference_01.png
        Lore/
          character.md
    Music/
    Images/
    Videos/
```

Folder depth is arbitrary within defined limits. The system preserves **path, immediate parent, all ancestors, original filename, extension, source UUID, source-version identity, file hash and extracted-content hash**. Folder paths are user-authored metadata: a file in `Characters/Yrsa/Portraits` can be linked to category nodes `Characters`, `Yrsa`, `Portraits`, without asserting an inference about real-world identity or sharing scopes.

### New user controls

- **Choose Raw Library Root** (owner-only; multiple explicitly approved roots optional).
- **Ingest New Files**: one-shot recursive delta scan of those roots, dry-run preview counts then start/pause/resume.
- **Review Changes**: New / Modified / Moved / Copied / Unchanged / Missing / Unavailable / Failed / Pending derived updates.
- **Folder Browser** with category tree, direct file and full descendant matches, path history, source version and cross-folder references.
- **Reconcile Folder Locations** for manual resolution when multiple identical files make a move ambiguous. No automatic destructive merge.
- **Enable automatic watching** separately and explicitly; off by default. Do not start endless recursive polling merely by configuring a root.
- **Correct Categories**: rename/move/reparent folders without re-embedding content; folder metadata links recompute cheaply.
- **Restore or retry** selected jobs with safe bounded retry and no duplicate work.

## Provenance/data model (illustrative migration only)

Retain canonical `documents` and `chunks`. Add normalized, versioned source-instance and folder association data, not a rival copy of the knowledge corpus. A candidate schema:

```text
managed_roots(root_id, display_name, configured_path_secret_ref, filesystem_id,
              active, last_scan_id, last_success_at, scan_policy)
folder_nodes(folder_id, root_id, parent_folder_id, relative_path, label,
             normalized_key, observed_at, missing_state)
file_instances(instance_id, root_id, relative_path, parent_folder_id,
               device_id, inode_or_file_id, size, mtime_ns,
               source_raw_sha256, extracted_hash, document_id,
               source_version_id, seen_at, status)
file_instance_paths(instance_id, root_id, relative_path, first_seen, last_seen,
                    current, relationship_type)
content_artifacts(content_id, raw_hash, extracted_hash, parser_version,
                  embedding_space_id, image_analysis_version, stored_artifact_ref)
source_versions(instance_id, revision_id, raw_hash, extracted_hash,
                parser_version, first_seen, superseded_at)
folder_document_links(folder_id, document_id, instance_id, evidence_type,
                      first_seen, last_seen, active)
scan_runs(scan_id, root_id, started_at, completed_at, manifest_checksum,
          files_seen, new_count, changed_count, moved_count, copy_count,
          duplicate_count, errors, status)
```

Use stable IDs and transactional uniqueness constraints: physical path uniqueness per active root, source-instance IDs independent of raw hashes, and one stored content-derived artifact per verified compatible hash/model/version combination. Keep owner privacy: absolute paths and file names may be sensitive and must not be added to public logs, prompts or GitHub. Prefer relative paths + root IDs for portable provenance and user-facing categories.

**Do not blindly bind identity to inode alone:** it can change after copies, backups, moves across filesystems or restore. Use device+inode within a trusted root as one signal, raw hash, previous source/metadata, location evidence, and owner review for ambiguities. Prefer a persisted metadata/sidecar source ID if owner opts in; never modify raw originals solely to invent IDs without explicit consent.

## Recognition and reconciliation algorithm

### 1. Safe scan

- Resolve only owner-approved root paths. Recursive traversal must enforce file-count/size/depth bounds, hidden-file policy, symlink policy (default no follow), root containment, permitted extensions/MIME, and inaccessible-file handling.
- Require file stability (two unchanged stat reads or safe snapshot) before parsing. Ignore incomplete uploads and temporary files. State metadata must be crash-safe, versioned and replayable.
- Compute cheap candidate fingerprints (path, size, mtime_ns) for fast unchanged detection, but confirm with cryptographic content hashes when needed; never declare identical contents based solely on name/size/time. Record root mounted/unmounted health to distinguish deletions from offline storage.

### 2. Reconcile changed placement and content

| Observed state | Required behavior |
| --- | --- |
| Same path, same verified content | No-op; retain associations and completed embeddings, captions, extractions and graph evidence |
| Same path, content changed | New source revision; compare chunk/segment hashes; embed/extract only changed segments; retract superseded evidence; update affected graph |
| Prior path missing, new path same stable file ID/content | Update current path and ancestor folder links; record move history; **no content reprocessing** |
| Prior path still exists, second path identical content | Record a second source instance and both folder paths/categories; **one reusable content representation**; no duplicate vectors or LLM work |
| Two independently named files have identical extracted text but different originals | Preserve both source and folder identity; reuse text embeddings only when parser/model compatibility holds; keep distinct original/media associations |
| Source file becomes inaccessible or root unmounted | Mark unavailable/pending verification; never delete canonical source/graph evidence automatically |
| File removed after verified successful scan | Mark missing/tombstoned instance; present explicit retention/delete policy; never silently erase the canonical material |
| Folder renamed or source moved across different volumes | Reconcile by identity/hash plus completed manifest; if ambiguous, request owner decision; update folder graph without content extraction |
| Image copied into new character visual-lore folder | Preserve image's existing exhaustive caption and vectors; add folder/category associations; no visual analysis repeat |
| Old file and new file share filename but differ in bytes | Treat as distinct content/version; don't conflate based on basename |
| Identical content used by two conceptual categories | Store one content representation and **two independent category/provenance links**; search can return both associations |

### 3. Delta semantics

- Keep separate **raw byte hash** and **normalized parsed-content hash**. Parsed content can remain the same while binary/image metadata or file identity changes; do not falsely skip media extraction when original pixels changed.
- For text: stable chunk boundaries and overlap-aware invalidation prevent one insertion from re-embedding the rest of the document where possible. Reuse only chunks with compatible tokenizer/parser/version/context; otherwise provide truthful wider invalidation when necessary.
- For images: digest original asset and stage a new full-image analysis when pixels actually change; region analysis may be incremental if model supports it. A folder-only move/copy never requires a new caption or multimodal embedding.
- For audio/video: preserve timestamp segment IDs and transcriptions; reprocess only changed time windows when reliably identified, otherwise mark whole-asset reprocessing explicitly, never quietly fabricate unchanged spans.
- For Skein: update only affected source evidence, entities, relations and affected neighboring graph nodes. Folder/category edges update independently from content embeddings. Preserve immutable prior known-good graph generation until staged deltas are verified.
- New files and changes may be queued to Z13 vision/text/embedding workers via Gufo's **verified compatible** API, but the G14 remains authoritative for source identity and transactional DB commits.

## Folder-aware knowledge retrieval and living visual lore

- Expose `folder.tree`, `folder.children`, `folder.search`, `source.locations`, `source.history` and optional folder-scoped filters through read-only Bifröst APIs.
- Treat the hierarchy as owner-defined categories/taxonomy with explicit `contained_in`, `child_of`, `has_source` and `also_found_in` relationships. Folder labels are contextual hints, not automatic claims of truth.
- Folder moves reparent/relabel category links with a cheap metadata/graph delta; this cannot trigger a full vector rebuild.
- A visual reference in `Characters/Yrsa/Portraits` should be discoverable under Yrsa's visual lore **when that entity association is owner-established**, while images in other categories can share the same content hash and still have separate usage contexts.
- **No per-character permission tuning.** All authorized private character clients through the uniform read-only gateway can search the entire brain; folders add retrieval/navigation categories, not restrictive access silos. The API credential remains read-only and never exposes database-write tools.
- On hosted clients, transmit only the context the user intended. Path metadata and private source bytes are never embedded blindly into Janitor prompts.

## Security and recovery invariants

- Only trusted G14 ingestion services may read owner-selected local file roots; do not accept arbitrary filesystem paths from remote API clients.
- No symlink traversal outside root by default; protect against traversal, device files, mount disappearance, path race, zip bombs and huge binary input. Use explicit owner exception controls only when justified.
- Never let the scanner modify, rename or move raw library files (except user-approved file-management operations).
- Back up original files, relative folder tree, source/placement ledger, content-addressed outputs, manifests, checkpoints, PostgreSQL canonical data and derived graph with tested restore and path relocation.
- Make scan and DB writes retryable, idempotent, transactional and restart-safe. On partial failure, retain the last successful manifest and do not publish invalid graph generations.
- Read and preserve current live/import workflows, public APIs, project laws, author attribution, and file permissions before implementation.

## Test/acceptance suite

1. Scan 100 files, then scan unchanged: no new document rows, text embeddings, visual captions, LLM extraction calls, or Skein rebuild. Preserve path/category results.
2. Edit a single paragraph in one file: only affected text segments and graph evidence reprocess; other 99 unchanged files are untouched.
3. Move one file into another folder: same content representation, updated current path, prior path history, new folder category, no inference call.
4. Copy the same file into a second folder: both paths are shown, category search discovers both, but no redundant content indexing.
5. Remove original after copying: remaining path stays indexed, move/copy state reconciles, no inadvertent canonical deletion.
6. Modify copied file independently: retains distinct source revision and associations without corrupting original version.
7. Mount loss, permission errors, crash mid-scan, rename while reading, filename collision, symlink escape and duplicate hashes never erase data.
8. Move an image with rich caption to another character-lore folder: prior visual identity is never silently rewritten; associations change only as authorized.
9. Restore on a fresh G14 replacement with relocated library root: root/path mapping restores while stable IDs, categories, knowledge provenance and de-duplication remain valid.
10. Verify every API and owner action still works when the optional managed library module is disabled.

## Implementation ownership, delivery and rollout

- **Bifröst Viewer:** owner folder browser/scan UI, folder-aware retrieval and canonical plan; optional read-only API.
- **Bifröst Ingest:** preserve old inbox; implement managed-library scan/manifest, source-instance ledger, revision delta parser, duplicate association handling and canonical source changes using versioned migrations.
- **Skein:** optional source- and folder-attributed incremental graph updates with exact provenance, retractions, staging and rollback.
- **Skry:** read-only retrieval of folder/category relations and source-instance evidence; no canonical writes.
- **Z13 Gufo:** only optional inference/embedding for actual changed media/segments; does not own database writes.

**Release order:** Audit current local watchers and source identities → backup/restore drill → schema/lineage design → hidden/synthetic fixture test of dedup and location updates → UI/manual scan → optional Z13 integration → staged incremental Skein/Skry links → approved production enablement. No live implementation is claimed by adding this document.
