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
