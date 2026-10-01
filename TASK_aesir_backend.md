# Aesir chat backend for the second brain

Volmarr authorized improving RuneForgeAI-Project-Aesir for this second brain and
publishing the relevant owning repositories. Aesir owns native inference;
Bifröst owns provider selection and graceful service degradation.

Current chat and embeddings share VIEWER_OLLAMA_URL. Aesir supplies real native
CUDA text generation but not the nomic-embed-text vector space of this corpus.
Add an independently configured authenticated chat backend, explicit fallback
policy, finite request/concurrency budgets, observable circuit recovery and
health reporting. Preserve Ollama embedding configuration and public legacy
helper contracts for the ingest, Skein and Skry components.

Verify provider contracts with fault injection, actual Aesir/Ollama sockets and
the existing Bifröst regression suite. Benchmark equal installed model bytes and
honestly report speed differences. Deploy only the validated route, check search
and corpus fingerprint without production test writes, update manuals and push.
No corpus re-embedding, network exposure, credential disclosure or quota relaxation.

## Outcome — 2026-10-01

Separate lazy chat routing, bounded admission/responses, exact model/completion
checks, private authenticated Aesir key admission, observable explicit fallback
and single-probe circuit recovery are implemented. The full isolated suite passes
127 tests. Actual native HyDE and original semantic search, three outage fallback
requests, cooldown recovery, native supervised restart and final Ollama HyDE pass.
Source counts/fingerprint remain 1237 documents/49006 chunks/v3_49006_49006.
The measured faster live default remains Ollama; Aesir is supervised and explicitly
selectable. Detailed setup and evidence are linked from AESIR_BACKEND.md. Faster
native generation remains an upstream measured compute task, not a completed claim.
