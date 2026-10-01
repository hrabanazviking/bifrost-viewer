# Task: end-to-end ingestion and build recovery

Date: 2026-10-01. Authorized by Volmarr's request to strengthen ingestion,
database building and additions. Apply Mythic Engineering's Architect, Forge,
Auditor and Scribe roles in this single-agent task.

## Evidence and owning boundaries

- security/queue.py overwrites the payload-path variable with its log path before
  building the sandbox command. Text workers can read their log instead of text.
- scripts/watch_inbox.py captures all child output in RAM, does not explicitly
  terminate descendant processes, has no single-supervisor lock, and trusts retry
  record shapes. Corrupt state resets without a last-good fallback.
- ingest/ingest.py reads required configuration during import, silently skips
  malformed JSONL lines, does not check source stability or target vector dimension
  before insertion, and does not replay transient DB transactions after embedding.
- API job retries treat all nonzero exits alike and expose only queued/running
  progress. Configuration and malformed inputs need different recovery behavior.
- Skein's build can replace a graph after extensive vocabulary-call failures;
  independent CLI builds have no shared lock. Bifröst's entity cache key uses the
  source fingerprint alone, which does not distinguish two builds of one corpus.

## Outcome and scope

1. Correct text mounting and prove exact Unicode content/provenance through the
   real sandbox and a restricted DB role in an isolated integration database.
2. Add a parser reliability domain: validated lazy configuration, safe classified
   failures, progress reporting, stable-input checks, strict malformed-record
   handling, validated/adaptive embedding batches and idempotent DB retries.
3. Add a read-only ingest doctor for configuration/schema/vector/count invariants.
4. Harden inbox state persistence/recovery, singleton execution, child deadlines,
   shutdown and classification of permanent versus transient/configuration failures.
5. Preserve scoped keys and all existing limits while adding honest queue progress,
   terminal error categories and an owner-only bounded deliberate retry action.
6. Serialize Skein builds, retain the previous graph on excessive discovery
   failures, and version entity layouts by actual build generation.
7. Update contracts/manuals, run fault-oriented regressions and isolated live
   integration checks, deploy to existing services and push owning repositories.

## Invariants

No source deletion, silent truncation or automatic source-schema migration.
No widening of AI permissions, sandbox mounts or network policy to owner secrets.
No resetting credentials or database to repair a queue. Existing idempotency,
atomic document/chunk insertion, restricted SQL role and payload/rate ceilings
remain intact. Test inputs belong in an isolated database; preserve real inputs,
credentials and source rows. Do not run a costly full live Skein build for testing.
Back up private state and record source counts before service deployment.

## Verification and deployment

Completed the owning-domain changes and updated component/interface/architecture
manuals. Default viewer tests pass (85; four opt-in integration checks skipped);
with the dedicated test DB all 89 pass. The separate parser suite passes 19 checks.
Skein 0.1.1 passes 47 checks. Live integration uses actual Bubblewrap, PostgreSQL
and Ollama: exact Unicode/newline payload and server provenance, idempotent replay,
forbidden UPDATE/DELETE/schema alteration, all-or-nothing malformed JSONL, and
shared Skein build exclusion. Ruff, JavaScript syntax and diff checks pass.

Backed up private state before stopping services. Deployed/restarted Bifröst and
the inbox watcher; health reports DB/Ollama/cached graph ready, API supervisor
running, inbox idle with no failed files. The read-only doctor reports 1,237
documents and 49,006 chunks, zero missing/zero vectors, orphans, empty documents
or broken chunk sequences. Source counts/IDs are unchanged from the baseline.

Historical audit found one old diagnostic sandbox canary falsely marked successful
with different stored text. Marked only its private queue result failed with
historical_payload_mismatch; preserved original source/payload and the revoked
test key policy. Another duplicate canary is correctly present under its original
source provenance. No source deletion or synthetic repair was performed.

Integration data and its restricted role live only in a separately named test
database; private configuration is outside Git. No full production Skein rebuild
was run merely to test recovery. Cooperative build locks require upgraded builders;
source content mistakes/corruption require owner-reviewed correction rather than
automatically invented knowledge.

Generated-layout cleanup follows successful atomic publication, preserving old
layouts on a failed replacement. Two regressions verify that boundary.
