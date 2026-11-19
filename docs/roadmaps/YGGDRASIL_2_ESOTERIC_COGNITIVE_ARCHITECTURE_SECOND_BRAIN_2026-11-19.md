# Yggdrasil 2.0: The Esoteric Cognitive World Tree for Bifröst Second Brain

**Owner decision:** 2026-11-19  
**Status:** Detailed design and implementation roadmap, **NOT** a deployed module or benchmarked performance claim  
**Authority:** Extends the [Bifröst master roadmap](BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md) and [modernization addendum](SECOND_BRAIN_ADDITIVE_INCREMENTAL_MULTIMODAL_GATEWAY_2026-11-19.md), alongside the [three-tier memory model](SECOND_BRAIN_THREE_TIER_MEMORY_ARCHITECTURE_2026-11-19.md), [branchable permanent archive](SECOND_BRAIN_GITLIKE_JOURNALED_ARCHIVE_2026-11-19.md), and [managed raw library](SECOND_BRAIN_MANAGED_RAW_LIBRARY_FOLDERS_2026-11-19.md).

## 0. Newer owner vision supersedes the early Yggdrasil assumptions

The original Yggdrasil in [NorseSagaEngine](https://github.com/hrabanazviking/NorseSagaEngine) was created during the owner's first AI-assisted development period. Its first manifesto says every decision should use OpenRouter, and its early Nine-World design largely divides work among task-routing and simulation roles. **The owner's newer design replaces that historical architectural rule**, not the existing source code by fiat:

> Build a significantly more sophisticated, **esoteric and psychological Yggdrasil** in which the Nine Worlds express complementary *functions and modes of mind*. Use HugrGate to select the least expensive sufficient decision mechanism and activate only genuinely relevant perspectives. Make the improved core reusable both by NorseSagaEngine and, as a wholly OPTIONAL module, by the G14-hosted Bifröst Second Brain. Preserve the original RPG implementation, source identity, stable data and compatibility until a tested adapter or new API is ready.

The esoteric world mappings below are **user-defined symbolic correspondences** for a modern cognitive system, not an assertion that historical pre-Christian Norse texts explicitly describe nine computational brain modules. The engine may explore mystical interpretation as such, while retaining separate provenance for sourced history, user-affirmed metaphysics, inferred ideas, hypothetical possibilities, and original fiction.

**Critical distinction:** Yggdrasil orchestrates *how knowledge is contemplated, reflected upon and synthesized*. **It does not replace** the Bifröst source library, PostgreSQL/pgvector, Ingest, Skein, Skry, Ravens, HugrGate, Gufo, or Samverk.

## 1. Architecture ownership and optional runtime

```text
USER / AUTHORIZED SECOND-BRAIN CLIENT
              |
       Bifröst Reader + API (G14)
              |
       [Optional Yggdrasil 2.0]
              |
        HugrGate: bounded judgment
         /        |           \
   direct answer  rule/ML     activate relevant worlds
         \        |           /
          Evidence-aware cognitive DAG
           |       |        |
      Skry/Skein   Ravens   Bifröst three-tier memory
           |       |        |
         Review / synthesis / temporary possibilities
                  |
            Gufo (Z13, via private network)
                  |
      read-only cited output OR owner-review proposal
```

- **Bifröst G14**: canonical data, immutable long-term archive, current medium-term focus, ephemeral per-session working state, source/folder provenance, authenticated read-only gateway, orchestration and permitted owner-only commit operations.
- **Skein KG**: derived source-backed graph generations, changed-evidence processing, historical lineage.
- **Skry KG**: read-only relevance, source/evidence traversal and optional branch-aware retrieval.
- **Ravens (Huginn/Muninn)**: optional retrieval and mutable *associative activation* tied to stable Bifröst IDs. Association decay NEVER deletes immutable long-term sources.
- **HugrGate**: optional confidence/calibration-aware **decision** layer: deterministic rule → cheap classifier/embedding → bounded model as needed → abstain. It is not a world and not automatically a full LLM.
- **Gufo (Z13)**: existing independently managed inference engine for costly synthesis, visual cognition or compatible embedding/vision workloads; never authoritative for G14 memory writes.
- **Samverk (optional)**: reviewed long-term history/export/branch interoperability, not the knowledge database.
- **Yggdrasil 2.0**: optional *cognitive-control and metacognition module*. It may be implemented as an application-neutral core with adapters for Bifröst and NorseSagaEngine. Its own caches and task state must respect three-tier retention.
- No compulsory nine-agent swarm, nine LLM instances, nine memory databases, extra full-corpus index, public service, dependency on OpenRouter, or automatic second-brain re-ingestion. No per-character permission/collection setup: all authorized characters retain the same broad **read-only access** to the entire brain.

## 2. The Nine Worlds become complementary functions of mind

Each world is a **distinct cognitive operation/perspective**, with machine-readable purpose, request and result schemas, evidence requirements, compute budget and fallbacks. A world is NOT guaranteed an LLM call. Some execute simple retrieval, comparison or an ordinary algorithm. Several can participate when useful; none is required for every query.

| World | Esoteric/psychological correspondence (proposed) | Specific cognition | Candidate Second Brain operations |
| --- | --- | --- | --- |
| **Ásgarðr** | Higher perspective, intention, metacognition | Reflect upon goals, understanding, planning and quality | Plan a complex inquiry; estimate whether a response is complete; select a review objective |
| **Vanaheimr** | Harmony, emotional/situational resonance, organic connection | Relevance, salience, integration and mutually supporting patterns | Understand which current focus domains relate; suggest meaningful association links, including Raven activation |
| **Álfheimr** | Intuition, subtle pattern recognition, symbol and imagination | Exploratory analogy and symbolic interpretation | Compare rune motifs, artistic styles, visual symbols, metaphors and conceptual similarities with explicit uncertainty |
| **Miðgarðr** | Present awareness, grounded observation, embodied context | Parse current input, attach modality, time, source, observational status | Understand a newly ingested image or research text as an observation, not a generated fact |
| **Jötunheimr** | Wild perspective, challenge, disruption of assumed patterns | Test alternatives, counterexamples, hidden premises and uncertainty | Examine contradictions, alternate explanations, neglected associations or ways an assumption may be wrong |
| **Svartálfaheimr** | Inner craftsmanship, symbolic forming, intellectual construction | Build synthesis, conceptual models, structured artifacts and visual lore | Produce a literature synthesis, taxonomy proposal, character design-sheet proposal or interoperable structured analysis |
| **Niflheimr** | Quiet, discernment, conservation, epistemic restraint | Verify claims, provenance, uncertainty, consistency and memory-boundary compliance | Validate citations, distinguish speculation from evidence, abstain, recommend archival review without writing |
| **Múspellsheimr** | Transformation, creative fire, intellectual metamorphosis | Recombine existing material, seek creative breakthroughs and useful reframings | Draft new concepts or artistic directions as *hypotheses*, never automatically accepted archive facts |
| **Helheimr** | Depth, historical continuity, ancestral recollection and hidden context | Retrieve historical and long-term evidence, version lineage, forgotten conceptual threads | Search immutable archive, past Git-like commits, ancestor categories, older source revisions and provenance |

### Separation that preserves the worlds' meaning

Ásgarðr should ask **"What is the real question and how should we know?"** Helheimr asks **"What has actually been recorded?"** Niflheimr asks **"What is supported, uncertain or contradicted?"** Álfheimr asks **"What symbolic patterns might connect?"** Jötunheimr asks **"Which assumptions could be challenged?"** Svartálfaheimr asks **"What can be built from these findings?"** Múspellsheimr asks **"What transformative possibility emerges?"** Vanaheimr asks **"How does this relate to present meaning, focus and other relationships?"** Miðgarðr asks **"What are we observing right now?"**

This distinction is functional, not cosmetic. A world's contract should have a clear test proving that it contributes something *different* from existing Bifröst/Skry methods and other worlds. Collapse redundant responsibilities rather than multiplying unnecessary stages.

## 3. The Norns: temporal cognition without predestination claims

Use the mythic triad as a **symbolic model of relationships among historical record, active change and possible futures**, not a claim that software can know fate or prophecy.

- **Urðr: what has become.** Read immutable accepted long-term versions, archived images, original sources, old graph generations, correction links and memory commits. Can compare states "as of" a past commit. Cannot rewrite the archive.
- **Verðandi: what is becoming.** Read changing medium-term focus, recent active projects, mutable association strength, presently observed inputs and authorized currentness refs. May propose focus changes; no unilateral archive mutation.
- **Skuld: what may unfold.** Reason about scenarios, uncertain hypotheses, counterfactuals and alternative knowledge branches. Use bounded simulations or owner-reviewed draft branches for substantive hypotheses. A prediction or mystical interpretation is never stored as a verified historical fact without separate supporting evidence and archival approval.

**Norns API proposal:** `norns.history(commit_or_time, evidence_ids)`; `norns.current_focus(domain_ids)`; `norns.possibilities(question, bounded_context, budget)`; `norns.compare(branch_a, branch_b)`. Read-only to long-term sources; only privileged owner-approved Bifröst operations may commit a reviewed interpretation. Branch creation is NOT required for every conversation or fleeting thought; default Skuld reasoning stays ephemeral, and substantive proposals may be prepared in an explicitly approved draft branch.

## 4. Mímir: reflective synthesis and metacognition

Mímir is **a service coordinating evaluation**, not another independent archive or omniscient oracle.

- Maintain a clear, provenance-aware distinction among `observed`, `source_asserted`, `corroborated`, `user_defined_canon`, `interpreted`, `hypothesized`, `fictional`, `unknown` and `contradicted` statuses.
- Ask whether a synthesis answers the question; what evidence is missing; whether the system has overgeneralized; whether concepts from different traditions have been conflated.
- Support multiple epistemic frames, e.g. academic history, lived mystical interpretation, artistic symbolism and systems engineering, without forcing one to masquerade as another.
- Produce a **grounded answer** with evidence pointers, confidence appropriate to the decision method, contradictions and optional follow-up investigation proposals.
- Retain uncertainty and explanation as fields; don't fake numerical probability just because HugrGate supports it. Calibrated confidence requires representative testing for that task.
- Use Niflheimr to verify attribution and Jötunheimr to challenge assumptions only where that expenditure is useful, not automatically for every response.
- Each synthesis may stay in volatile short-term memory or inform mutable medium focus. Nothing generated becomes immutable long-term knowledge without the existing explicit owner/Ingest archival workflow.

## 5. Concrete use cases surveyed and prioritized

### A. Highest value / first pilots

**A1. Metacognitive research reflection.** Given a question and Skry/Skein evidence, diagnose coverage, missing sources, support vs contradiction, uncertainty and next research actions. Distinguish a genuine missing fact from absent retrieval. Start with an evidence-only, read-only mode.

**A2. Cross-domain knowledge synthesis.** Detect cross-topic relationships among research, Norse esoteric ideas, AI architectures and creative work. Use Skein evidence and Raven associations as *candidate leads*, not as fabricated facts. Separate sourced parallels from mystical interpretation and newly generated concepts.

**A3. Changing medium-term focus.** Connect live project/folder categories, authorized goals, recently activated links and owner-pinned domains. Suggest or explicitly apply owner-approved focus boosts without changing the permanent archive, regenerating embeddings or assigning per-character collections.

**A4. Research gaps and contradictions.** Generalize `yggdrasil/cognition/gap_analyzer.py`, which currently spawns narrative LLM tasks from heuristic missing fields. For Bifröst, a missing fact **cannot be manufactured**. Use graded actions `retrieve_more`, `ask_owner`, `flag_uncertain`, `draft_hypothesis`, `defer`; no silent invented lore and no automatic graph/source writes. Use bounded recursion and task count.

### B. High value / later pilots

**B1. Temporal knowledge comparison.** Norns ask how understanding changed from source commit A to B; trace correction lineage and hypothetical branches. Git-like history is already owned by Bifröst; no second version store inside Yggdrasil.

**B2. Living visual lore understanding.** Work with image descriptions, pixel/reference-asset provenance and structured traits produced by Bifröst's vision pipeline. Distinguish a character's pinned identity/canon from outfit/scene/style variants, produce prompt/reference composition suggestions, and flag uncertain detail as unverified. Do not auto-promote newly generated images to canon. Integrate with Gufo vision on Z13 only for tasks requiring vision/model inference.

**B3. Creative/esoteric inquiry.** Compare symbolic, mythic and philosophical patterns. Return a labeled `esoteric_interpretation` artifact distinct from academic evidence or immutable historical fact; no automatic reclassification of published sources.

**B4. Bounded inquiry plans.** Asgard creates a DAG only for genuinely complex work, with resource/time budgets and abort rules; cheap direct questions must not incur a Nine-World workflow tax.

**B5. Focus-aware associative memory.** Ravens supplies co-activation and weak/strong connections. Yggdrasil uses them to explore insights, but Ravens decay updates auxiliary association weights only, never long-term accepted evidence.

**B6. Knowledge-branch and scenario exploration.** Skuld explores alternate interpretations on short-term scratch or owner-approved draft branches, including comparisons with approved main. Require conflict and provenance review for any eventual merge.

### C. Low/no added value: never introduce a new cognitive tax

SHA-256 exact duplicate detection; file move/rename reconciliation; basic path/category traversal; original file ingestion; PostgreSQL transaction/WAL; ordinary hash-matched incremental updates; straightforward keyword retrieval; authentication/authorization; token expiration; simple queue dispatch; image format detection. Keep deterministic code as currently owned by Bifröst/Ingest/Skry, not a forced HugrGate/LLM/Nine-World round trip.

## 6. HugrGate: judgment *within and between* the worlds

HugrGate is **not a tenth world**, not a source of factual authority, and not a reason to invoke probabilistic judgment for basic calculations. It provides an optional typed decision interface used only where ambiguity/cost warrants it.

Candidate `DecisionSpec` families:

| Decision | Options / output | Default |
| --- | --- | --- |
| `cognition_needed` | direct_answer, targeted_retrieval, bounded_worlds, deep_inquiry, abstain | Simple deterministic guards first |
| `realm_selection` | ranked subset of Nine Worlds; per-world marginal benefit | Never all Nine by default |
| `query_epistemic_mode` | historical_evidence, symbolic_interpretation, creative_generation, systems_analysis, mixed | Preserve mixed labels |
| `evidence_gap` | retry_retrieval, request_source, propose_hypothesis, no_action | No synthetic fact insertion |
| `model_escalation` | rules, classifier, existing_text_search, local_small_model, Gufo_strong_model, abstain | Cheapest sufficient, user-approved transport |
| `medium_focus_suggestion` | ranked focus category IDs and reversible boost | Do not hide other knowledge |
| `verification_need` | no_extra_check, provenance_check, independent_check, human_review | Hard archival gate remains deterministic |
| `visual_analysis_depth` | cached_caption, lightweight_metadata, deep_vision, owner_review | Never rerun unchanged asset |

- Every DecisionSpec uses a bounded, validated schema, explicit backend choice, cancellation, typed error/refusal, max latency and tokens, confidence/calibration metadata where actually supported, and an explanation trace without leaking transient conversations.
- Use a **short circuit**: deterministic current source hash and direct high-confidence evidence retrieval bypass both HugrGate model backends and world orchestration; decisive simple classifications may use light HugrGate rules.
- No probabilistic override of **permissions, archival immutability, expiry/purge, source identity, hard evidence truth status, branch protection or private-data transmission**.
- When HugrGate is absent/slow/misconfigured, fall back to existing Bifröst/Skry retrieval and established Yggdrasil deterministic routing, not a fatal failure or clandestine cloud request.
- Don't assume active HugrGate server or Gufo-compatible backend solely from repository documentation; verify the actual running service/API before implementation.
- Disable or redact any HugrGate decision/episode logs for short-term content so `short-term does not last` remains true.

## 7. Cognitive DAG execution with costs, limits and provenance

An invocation is an owner-configured `CognitiveRequest` rather than nine unconditional LLM messages.

```text
CognitiveRequest {
  request_id, session_id, query_or_source_ids, epistemic_mode,
  source_commit_id?, current_focus_version?, modality,
  max_world_steps, max_model_calls, max_tokens, max_wall_ms,
  allow_branch_draft=false, allow_archive_write=false
}
CognitiveResult {
  result_kind, content, evidence_refs[], uncertainty[],
  proposed_focus_changes[], proposed_research_tasks[],
  candidate_branch_diff?, world_trace[], decision_trace[],
  token_costs, elapsed_ms, persistence_tier="short"
}
```

- Entry defaults to read-only and `allow_archive_write=false` **always for external character clients**. Owner-approved archive/promotion is a separate authenticated Bifröst workflow, not a boolean trusted from an untrusted API request.
- Build DAG tasks only for relevant worlds, with dependencies, memoized stable read retrieval, cancellation and bounded recursion. Reuse original DAG/realm abstractions only where contracts fit an application-neutral API; don't import RPG world-state behavior into Bifröst.
- GPU-heavy inference stays on the Z13's independently running Gufo and is invoked only after optional latency/capability checks; G14 keeps DB, user focus, Raven refs and orchestration.
- Token budgets, end-to-end wall-time budgets, concurrency, model-memory admission, quiet periods and priority rules prevent background cognition from starving normal character chat or ingestion.
- Normalize `CognitiveResult` across local rules, HugrGate calibrated decisions and Gufo LLM. Include model IDs, graph generation, source IDs/versions, retrieved context and citations. Return partial/abstained outcomes when evidence or models are missing; do not present them as certain.
- Cache reusable **content-addressed evidence analyses** according to their immutable source/model/schema identity. Never preserve raw short-term queries, dialogue buffers or private prompt text in long-lived caches or telemetry.
- No automatic continuous "thinking" loop on the G14: optional one-shot owner request, opt-in scheduled reflection or bounded trusted agent request only. Disable entire optional module without impairing ordinary second-brain search.

## 8. Integration with the existing three-tier memory and journal

| Memory layer | Yggdrasil role | Non-negotiable boundary |
| --- | --- | --- |
| **Immutable long-term** | Helheimr/Urðr traverse versioned archive, Mímir synthesizes evidence, Skuld previews accepted branch history or proposes candidate changes | Archive writes and corrections are new immutable owner-approved versions, never an LLM edit |
| **Mutable medium-term** | Verðandi/Vanaheimr inspect changing project focus and Raven associations; owner can pin/adjust suggestions | Focus changes may change retrieval ranking but cannot hide the rest of the brain or mutate original facts |
| **Ephemeral short-term** | Miðgarðr contextualizes the question, Alfheimr/Jötunheimr explore, Mímir composes temporary insight | Expire at session end/TTL; no implicit journal, database record, auto-consolidation, replay or private log retention |

- Git-like Samverk branch integration is optional. A brain memory branch is a knowledge-view commit DAG, not a physical raw-file folder. Short-term proposals need not become branches and branch previews must not be publicly exposed to hosted character clients.
- Newly accepted long-term evidence is *append-only* and cites the original source and approved transformations. An incompatible or speculative synthesis is a review candidate, not an archive replacement.
- Skry retrieval remains read-only and Bifröst's universal character gateway retains uniform whole-brain read access for all characters (session-specific short-term state is isolated only to avoid cross-dialogue mixing).
- Do not create competing G14 databases, mutable duplicates of immutable source records or a mandatory second model vault.
- Folder-category identity influences focus/context, but a folder move alone triggers **zero new LLM/caption/embedding calls**.

## 9. Implementation order (separate, reversible phases)

### Phase 0: contemporary audit / owner decision reconciliation

- [ ] Inspect actual NorseSagaEngine `Development` branch: `yggdrasil/core/world_tree.py`, `core/bifrost.py`, `router.py`, `router_enhanced.py`, `core/dag.py`, `core/llm_queue.py`, `cognition/gap_analyzer.py`, `memory_orchestrator.py`, `ravens/`, `worlds/`. Check the actual G14 deployment and current HugrGate/Gufo API contracts.
- [ ] Explicitly supersede the older `YGGDRASIL_MANIFESTO.md` mandate that every decision must call OpenRouter. Preserve the old manifesto as historical context. Define current decision authority: deterministic-first, HugrGate as optional escalation, independently configured local Gufo, cloud only when owner explicitly permits it.
- [ ] Capture baseline correctness/costs for representative work, and tests showing current game and Second Brain behavior. Confirm installed models rather than infer from public documentation.

### Phase 1: application-neutral cognitive contracts

- [ ] Specify `CognitiveRequest`, `CognitiveResult`, `RealmOperation`, `EpistemicLabel`, `EvidencePointer`, `MemoryTier`, `NornsPerspective`, `ModelBudget` and optional `HugrGateDecisionAdapter`.
- [ ] Keep world-specific RPG simulation adapters separate. Publish a versioned minimal interface that can run with no RPG data, no network and no Gufo.
- [ ] Tests for ABI/schema, dependency-free fallback, read-only privilege, correct evidence provenance, bounded recursion and no per-character config.

### Phase 2: first practical Bifröst pilots, no model required

- [ ] Evidence-only **Mímir coverage/contradiction report** using existing Skry/Skein retrieval.
- [ ] **Urðr historical-as-of comparison** and Niflheimr evidence validation over approved immutable memory/commit pointers.
- [ ] **Verðandi current focus** analyzer using mutable folder and medium-tier metadata, with owner-reviewed reversible focus changes.
- [ ] Compare against current Bifröst direct retrieval to establish measurable extra value. Don't move original DB or build a second index.

### Phase 3: selective HugrGate execution

- [ ] Introduce explicit feature-flagged `cognition_needed` and `realm_selection` DecisionSpecs using existing deterministic heuristics as baseline.
- [ ] Record calibration/abstention on representative domain requests; prove task-selection gains without untrue certainty. If no gain, retain simple routing.
- [ ] Limit extra world activations and model escalation with query-level budgets. Pure keyword/DB work should not have to contact HugrGate server.

### Phase 4: Z13 Gufo-backed synthesis and guarded gap investigations

- [ ] Add authorized private Gufo adapter with verified endpoint schema, model capability and scheduling; use no cloud by default.
- [ ] Add Jötunheimr counterexample and Álfheimr symbolic comparison on scoped evidence; Svartálfaheimr/Múspellsheimr can synthesize original proposals.
- [ ] Refactor old Void Walker behavior: missing evidence invokes search or labeled hypotheses, not permanent fabricated facts.
- [ ] Ground every material factual statement with versioned cited sources; mark claims of spiritual meaning as interpretive and creative stories as original generation.

### Phase 5: Norns, visual lore and reviewed branches

- [ ] Connect Urðr/Verðandi/Skuld to Bifröst journaled immutable archive, medium focus and ephemeral hypothetical state.
- [ ] Add version-aware comparison and optional owner-approved draft knowledge branch proposals using existing Samverk/Bifröst APIs, not raw Git pushes from general reader clients.
- [ ] Add optional visual-lore symbolic/semantic exploration and cross-modal synthesis with pinned character identity preserved. Verify generated outputs are not promoted without owner approval.

### Phase 6: optional user experience, instrumentation and deployment

- [ ] Owner-only **Cognitive Observatory**: which world answered and why, evidence/focus provenance, prompt and token budgets, abstentions, limitations, and option to examine branch proposal. Displays honest instrumentation rather than invented mental-state claims.
- [ ] Toggle module, select modes (direct, reflective, research, esoteric, creative), clear short-term state, choose budget, review proposed focus/archives; no unnecessary giant onboarding or per-character collection mapping.
- [ ] Synthetic tests and restored backups; shadow-mode comparisons; owner-approved staged enablement on G14 and optional Z13 inference; rollback path. Retain baseline when disabled.

## 10. Benchmark and acceptance requirements

**Measure actual improvement, do not promise a fixed multiplier.** On G14/Bifröst and Z13/Gufo collect median/p95 end-to-end latency, number of model calls, input/output tokens, queue wait, peak memory, quality of citation grounding, factual mistakes, unsubstantiated relationships, retrieval recall, branch correctness, model/fallback availability and user-rated utility.

Suggested test corpus: repeated simple lookup, source contradiction, missing historical claim, esoteric comparison, multi-domain research, folder-only move, medium-focus-only change, a visual identity/outfit question, optional research branch alternative and two simultaneous character sessions.

**Must pass:**
1. A direct answer that already has adequate evidence uses no unnecessary new LLM call; it must not be slower than baseline beyond a small benchmarked bound.
2. A multi-domain inquiry returns materially better evidence-aware synthesis in a blinded, predefined comparison, or the more expensive route is not adopted.
3. Missing source evidence yields `unknown`, explicit retrieval retry or labeled hypothesis, NEVER an invented source fact inserted into immutable archive.
4. Each world shows a distinct purpose and a test proving its marginal utility; activating fewer than nine worlds is normal.
5. Gufo is unreachable: existing Bifröst retrieval, deterministic cognition and authorized character gateway still function, with honest partial status.
6. HugrGate is disabled: fallback remains correct and read-only; no forced remote model call.
7. Changing medium focus never modifies archived data/embedding models; short-term context disappears on expiry, with no content-bearing persistent logs.
8. Memory branch proposals, merges, correction suggestions and rollbacks require explicit owner authorization and preserve original immutable records with history.
9. Visual-lore synthesis leaves source image, detailed description and approved canon untouched until an authorized owner workflow.
10. No extra memory copy/index/database and no per-character collection permissions; existing Bifröst/Skein/Skry/Samverk applications remain independently usable.
11. No misleading "consciousness", spiritual authority or historical authenticity assertions inferred from the architecture's metaphors. Symbolic/theological explorations remain available and explicitly framed.
12. Hardware/runtime comparison uses measured same-task results and documented model identities. Approximate acceleration scenarios are never represented as tested throughput.

## 11. Cross-project implementation responsibilities

| Repository | Ownership |
| --- | --- |
| `NorseSagaEngine` (Yggdrasil core) | Modern app-neutral Nine-World/Norns/Mímir cognitive contracts; preserve original RPG route, rules and lore while it gains a provider adapter |
| `bifrost-viewer` (canonical) | Second Brain optional module, evidence/focus/ephemeral memory adapters, owner UI, policy, journaling/branch review, authorized model offload |
| `RuneForgeAI-HugrGate` | DecisionSpec mappings, calibrated routing, abstention/fallback and privacy-safe decision metadata |
| `skein-kg` | Existing provenance-rich derived graph generations; not a Yggdrasil memory database |
| `skry-kg` | Read-only evidence and historical-as-of retrieval |
| `Huginn-and-Muninn-Ravens` | Optional association strength and recall signals, not an immutable archive writer |
| `gufo-RuneForgeAI-Hacks-and-Experiments` | Independently hosted Z13 model inference on verified APIs; no G14 DB ownership |
| `RuneForgeAI-Samverk` | Optional Git-native manifest review/branch provider; no required dependency |

Maintain ONE canonical integration roadmap in Bifröst; other project repositories link and own only their specific implementation plans. Never convert the NorseSagaEngine game repo into the second-brain source of truth. Mark every roadmap item as planned until implementation is independently verified.

---

**Design maxim:** *The World Tree does not replace the well of memory. It learns which roots to follow, which worlds to consult, which uncertainties to honor, and when thought should become silent.*
