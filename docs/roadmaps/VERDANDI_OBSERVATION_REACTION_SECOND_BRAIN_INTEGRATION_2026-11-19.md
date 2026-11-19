# Optional Verðandi Observation and Reaction Layer for Bifröst Second Brain

**Owner direction:** 2026-11-19  
**Status:** Architecture and G14 integration plan only; the dedicated Verdandi repository has a limited optional code slice, **no Bifröst deployment or connected runtime**  
**Source-project plan and first code changes:** [Verdandi's HugrGate and Metacognitive Observation Roadmap](https://github.com/hrabanazviking/Verdandi/blob/feat/hugrgate-fast-reflex-metacognition-2026-11-19/docs/VERDANDI_HUGRGATE_METACOGNITION_SECOND_BRAIN_ROADMAP_2026-11-19.md).  
**Canonical companions:** [Three-tier memory](SECOND_BRAIN_THREE_TIER_MEMORY_ARCHITECTURE_2026-11-19.md), [Git-like journal and branches](SECOND_BRAIN_GITLIKE_JOURNALED_ARCHIVE_2026-11-19.md), [Yggdrasil 2.0 cognitive layer](YGGDRASIL_2_ESOTERIC_COGNITIVE_ARCHITECTURE_SECOND_BRAIN_2026-11-19.md), [raw library and incremental processing](SECOND_BRAIN_MANAGED_RAW_LIBRARY_FOLDERS_2026-11-19.md).

## Decision and boundaries

Verðandi is an existing **real-time local event nervous system**, not a replacement knowledge corpus or a necessarily conscious entity. It already has a Unix-domain socket bus, heartbeat health checks, a reactor, explicit owner-granted reflexes, an HG-T4/HugrGate judgment binding and safety rails. Modernize and reuse it as an **OPTIONAL metacognitive observation and reaction-proposal layer** for the G14 Second Brain.

Its proper role is **"What is happening now, how are the different subsystems behaving, and what safe response might help?"** HugrGate performs bounded judgment when the data warrants it. Yggdrasil 2.0 is optional deep reflective interpretation. Bifröst remains the authoritative archive and source writer; Skein owns derived graph versions; Skry handles read-only search; Ravens provides independent mutable associations; Gufo on Z13 supplies tested high-compute inference.

**Critical historical collision:** Verdandi's normal `nerve_feed.jsonl` and the existing conversation logger are persistent operational logs, while Bifröst's **short-term** layer must **expire without becoming durable**. **Do not wire raw Janitor/SillyTavern conversations or temporary thinking into Verdandi's standard persistent feed**. Require an isolated, metadata-only event stream and explicit allowlist/rotation/TTL. Separate non-content operational history from long-term accepted knowledge events.

## Integration architecture

```text
G14 BIFRÖST CORE
  RawLibrary / Ingest  --> events: scan summary, source IDs, job status
  Skein incremental    --> events: graph generation, validation, errors
  Skry retrieval       --> events: retrieval quality, missing evidence
  Long-term archive    --> events: accepted commit IDs, branch updates only
  Medium focus         --> events: focus-domain changes and suggestions
  Short-term sessions  --> events: expiry/status counts, NEVER chat content
  Gufo bridge to Z13   --> events: queue/latency/model failure counters
       |
       v
Verdandi optional observer sidecar on G14
  fast source allowlist / schema validation / basic rate limits
  |-- normal UDS notification, no LLM in publish hot path
  |-- sliding-window metacognitive patterns / drift / error trends
  |-- HugrGate: optional inexpensive judgment and abstention
  |-- Yggdrasil 2.0/Mímir: optional *deep* reflection on selected events
       |
       v
Typed observation + suggested action
  --> owner-visible observatory + diagnostics
  --> Bifröst authorized internal reaction workflow (not Janitor token)
  --> optional existing, declared, granted Verdandi reflex action
       |
       v
Record safe outcome/check postcondition; never auto-rewrite archive
```

**One read-only credential for all characters** to the entire permitted Second Brain, with zero per-character folder/collection tuning. This broad *retrieval* ability does not give characters control of infrastructure or owner-only action endpoints.

## Valuable use cases, prioritized

1. **Pipeline self-monitoring and efficient recovery:** detect repeated failing image/text extraction, stalled incremental graph generation, missing or incompatible embedding model, failed checkpoint or repeated job retry. Suggest pause/retry/resource relocation or graph rollback, but let the existing trusted owner-reviewed Bifröst/Skein workflow do the actual change.
2. **Metacognitive research signals:** detect many unanswered questions, contradictions between retrieved sources, unsupported synthesis or insufficient visual reference evidence; recommend deeper Skry retrieval or bounded Yggdrasil 2.0/Mímir analysis. Don't manufacture new archive facts.
3. **Adaptive model resource stewardship:** observe Z13 Gufo queue saturation and G14 job latency, route expensive background analyses to idle windows and preserve foreground chat priority. HugrGate classifies only ambiguous situations; deterministic pressure thresholds remain fast.
4. **Active medium-term focus:** observe project-domain signals and suggest reversible focus boosts. Ravens activation is optional and may not erase long-term knowledge.
5. **Living visual lore quality:** detect changed reference images with inconsistent traits versus owner-approved canonical character sheet; flag owner review. Separate source/original-pixel changes from folder-only moves and duplicate copies.
6. **Branch/journal integrity:** verify new accepted memory commits, compare historical views and flag branch-head conflict or orphaned derived generation. Only Bifröst/Samverk authorized owner workflows may merge/revert.
7. **Short-term expiry:** monitor session TTL/limits using opaque IDs and counts; ensure transient text never reaches persistent logs, model traces, Git exports or backups.
8. **Observability and safe notification:** summarize repeated anomalies once, respect quiet hours, prevent alert floods and allow manual review. Don't launch background runaway jobs.

## Proposed G14 event contracts

Use **non-sensitive, content-minimized, versioned metadata**:

```text
SecondBrainNerveEvent {
  version, event_id, occurred_at, component, kind, severity,
  opaque_source_or_job_id, correlation_id?, duration_ms?,
  status?, queue_depth?, model_id?, source_version_id?,
  graph_generation_id?, journal_commit_id?, memory_tier?,
  privacy_class="metadata-only", data_digest?
}
VerdandiObservation {
  event_ref_ids, pattern, source, severity, evidence_refs?,
  recommendation, confidence_if_calibrated?, observed_or_inferred,
  expires_at, hugrgate_trace?, acted=false
}
```

No transcript, image bytes, personal names, sensitive absolute source paths or secret tokens by default. Store only safe aggregate event metadata if explicitly configured, and guarantee short-term text is excluded. Use stable IDs so source movement doesn't require reprocessing. Use natural source/event timestamps for ordered correlations; heartbeat clocks only for local cooldown/TTL. Be careful with network reorder and event ID idempotence across G14/Z13.

## Expected relationship to the Three Norns

- **Urðr:** Bifröst's **append-only, immutable accepted knowledge** and journaled version history. Verdandi's ordinary operational event feed must NOT be treated as permanent canonical truth.
- **Verðandi:** present monitoring, changes in current focus and ephemeral resource/health state. This is the proposed sidecar's primary role.
- **Skuld:** bounded scenario/prediction/proposed reactions, not certainty, no unauthorized automatic future action.
- **Mímir/Yggdrasil 2.0:** optional deeper reflective synthesis only when selected by low-cost HugrGate/deterministic policy; no mandatory nine-world cycle for routine event delivery.

## Integration and owner-consent rules

- Optional module **disabled by default** until tested, configured and owner-authorized. Never directly bind a raw UDS from Raspberry Pi to Internet or accept unrestricted external publisher events.
- Deploy local G14 observer sidecar or module with dedicated least-privilege OS user/sockets. If needed, remote G14/Z13/Pi connections use a separate authenticated transport and precise event allowlist; Tailscale private network alone is not a substitute for message validation and actor authorization.
- Declarations, owner grants, quiet state, rate limits, cooldowns, global kill switch, failure self-disable, no unknown action names, explicit trace and postcondition checks. No event text should become shell arguments or arbitrary subprocess commands.
- **No automatic "fix the repo", Git push, database edit, delete, model swap, long-term archive commit/rollback, or hosted network activity** from an observational verdict. Existing Verdandi heartbeat modules may have such capabilities already; isolate those modules and require explicit owner approval for Bifröst integration.
- A failure in HugrGate/Gufo/Yggdrasil observer must not slow or crash core Bifröst retrieval or event publishing. If unavailable, return operational "not judged" status, avoid dangerous actions and keep diagnostics.
- Avoid turning all event data into a new long-term source corpus or duplicating the whole Second Brain database inside Verdandi.
- Existing Bifröst read-only gateway keeps its uniform source search rights without per-character collection profiles, but exposes **no** write/control actions through those tokens.

## Incremental phases and acceptance

1. **Read source projects and verify deployed reality.** Audit Verdandi actual code, legacy feed persistence, HG-T4 availability and current Bifröst G14 schema; establish existing baseline.
2. **Implement internal allowed event emitters** for safe synthetic/test Bifröst tasks and use an isolated metadata-only observation stream. No raw short-term conversation.
3. **Prove opt-in fast predicate prefilter** and source-event schema validation on synthetic streams. Confirm accuracy and latency vs baseline, not a hypothetical throughput boast.
4. **Implement observer sidecar** with bounded windows, idempotent event IDs, real state drift/correlation, remediation-outcome feedback and no model by default.
5. **Connect tested HugrGate judgment** for uncertain cases, verify schema, local endpoint security, on/off fallback and correct never-fire policy.
6. **Add read-only Second Brain observatory** with recent observations, proposal basis, source evidence, time budgets, pause/disable controls and review status.
7. **Integrate optional Yggdrasil 2.0** for evidence-based metacognitive reflection on selected complex anomalies and historical change, not every event.
8. **Allow only explicitly approved internal reactions** using narrow grants and reversibility; preserve first five Verdandi reflex behaviors as independently tested. Add no privileged actions to Janitor/SillyTavern API.
9. **Benchmark:** p50/p95 event-to-observation and event-to-authorized-response, avoided judgment/model calls, false positives/negatives, overhead on G14, Z13 interactive interference, memory/CPU/resource use and archive immutability.
10. **Recovery:** disable Verdandi, HugrGate and Yggdrasil adapters mid-run; Bifröst still ingests, searches, queries and preserves committed evidence. Short-term content sentinel absent from durable files, logs and Git/Samverk backups.

**Status evidence:** The Verdandi PR changes fast judgment gating and a bounded synthetic metacognitive observer. No running local G14 Second Brain integration, full HG-T4 performance benchmark, owner-reviewed auto-remediation, or working observatory is implied by this plan.

**Design refrain:** *Let the nervous system perceive, the gate discern, the World Tree reflect, and the keeper decide what becomes permanent.*
