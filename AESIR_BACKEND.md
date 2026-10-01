# Selecting Aesir or Ollama for Bifröst chat

## Current operating choice

Bifröst has a separate bounded chat router for HyDE search passages and cluster
labels. It supports the original Ollama endpoint and an authenticated same-host
Aesir native service. The original Ollama `nomic-embed-text` configuration still
owns all corpus/query embeddings. Trusted ingestion, API ingestion, Skein and
Skry do not switch embedding models when chat changes.

On the exercised RTX 2060 Max-Q with the same Llama 3.2 3B GGUF, the latest
native efficiency slice is another 1.60–1.66x faster than its previous release.
Repeated 32-token passages now take about 0.838 seconds native versus 0.874
seconds Ollama; repeated longer prompts take 0.876 versus 0.892 seconds in a
small paired series. Observed first passage/longer requests still favor Ollama
(1.306/5.820 seconds native versus 0.918/1.003 seconds Ollama). Templates and
KV/prefix policies differ despite identical model bytes, so this is a narrow
observation, not general provider superiority.

**The live default remains Ollama for ordinary new prompts.** Native Aesir is
installed, supervised and available as an explicit option. Its current kernels
and exact-prefix reuse preserve sampled/greedy replay, deadline/reset recovery
and the existing authentication/resource boundaries. Embeddings and corpus are
unchanged. See [current measured evidence](https://github.com/hrabanazviking/RuneForgeAI-Project-Aesir/blob/main/docs/evidence/native-efficiency-2026-10-01.md)
and [operation and benchmarking](https://github.com/hrabanazviking/RuneForgeAI-Project-Aesir/blob/main/docs/NATIVE_EFFICIENCY.md).
Earlier 8.1-second native measurements describe the historical integration
release and are superseded for this exercised model/device.

## Long prompts and native buffers

The later native long-token slice uses four-token prefill for the exercised
Llama 3.2 3B profile. The local engine decodes each packed weight block once for
four input positions, preserving causal KV and the sequential numerical results.
Authenticated native health exposes actual `prefill_batch`; operators can select
`--prefill-batch 1` for the reference path. Four-token capacity adds 396 KiB of
compact scratch, with shared scores/logits and unchanged F16 KV. Deadline checks
occur at boundaries of at most four input tokens, then each output token.

[Native long-token operation and verification](https://github.com/hrabanazviking/RuneForgeAI-Project-Aesir/blob/main/docs/NATIVE_LONG_TOKENS.md)
provides controls and physical evidence. This does not change Bifröst request
schemas, the default provider, external AI permissions or embeddings. Outside
clients still use their individual Bifröst keys and documented append/rate limits.
A native-engine improvement alone does not establish a current Ollama speed win.

## Configuration

Edit the private root `.env` through a text editor; do not shell-source it.
Use an absolute credential path and restart `bifrost.service` afterward.

| Setting | Default | Meaning |
| --- | --- | --- |
| `VIEWER_CHAT_BACKEND` | `ollama` | `ollama` or `aesir` |
| `VIEWER_CHAT_MODEL` | Existing configuration | Same registered chat model name for primary and fallback |
| `VIEWER_CHAT_URL` | Ollama origin, or Aesir loopback | Explicit origin without credentials, route, query or fragment |
| `VIEWER_CHAT_API_KEY_FILE` | Required only for Aesir | Current-owner private regular key file; symlinks/FIFOs/public files refused |
| `VIEWER_CHAT_FALLBACK` | `none` | `ollama` enables an explicit fallback only for an Aesir primary |
| `VIEWER_INFERENCE_POLICY` | Repository `inference.json` | Exact-schema bounded routing policy |
| `VIEWER_OLLAMA_URL` | Existing configuration | Embeddings and optional Ollama chat/fallback origin |
| `VIEWER_EMBED_MODEL` | Existing configuration | Must retain the corpus embedding model identity |

Existing default policy example:

```dotenv
VIEWER_CHAT_BACKEND=ollama
VIEWER_CHAT_URL=http://your-actual-ollama-origin:11434
VIEWER_CHAT_MODEL=llama3.2:3b
VIEWER_CHAT_FALLBACK=none
```

Explicit native configuration:

```dotenv
VIEWER_CHAT_BACKEND=aesir
VIEWER_CHAT_URL=http://127.0.0.1:18434
VIEWER_CHAT_API_KEY_FILE=/absolute/private/path/to/service.key
VIEWER_CHAT_MODEL=llama3.2:3b
VIEWER_CHAT_FALLBACK=ollama
```

Install/build/import the native service first using
[Aesir's second-brain manual](https://github.com/hrabanazviking/RuneForgeAI-Project-Aesir/blob/main/docs/SECOND_BRAIN.md).
This adapter accepts authenticated IPv4 loopback for Aesir. Its credential never
goes to the Ollama fallback. HTTP clients ignore environment proxies, reject
redirects and retain certificate verification for HTTPS origins.

The Aesir credential belongs to the local service connection. External AI clients
receive individual Bifröst keys; they never need the native key or DB password.
Access to Aesir is not a new externally reachable data or model API.

## Request bounds and recovery

The JSON policy defaults are one active chat call, 0.2 seconds waiting for
admission, 3 seconds to connect, a 45-second per-operation HTTP timeout,
1 MiB maximum decoded response, a two-failure primary circuit and a 30-second
cooldown. Ollama chat explicitly requests context 4096 and temperature zero.
Both providers accept at most 256 generated tokens through this adapter.

Response streaming is used internally to enforce the body-size limit; the
application receives a complete response. The HTTP library timeouts cover
individual network operations. A monotonic elapsed check also rejects late
chunks. This is not a strict 45-second end-to-end workflow deadline: a stalled
operation and an explicitly selected fallback can add time. Aesir additionally
enforces its native cooperative generation deadline. Clients should use their
own request deadline appropriate to HyDE rather than polling a slow request.

On transient network, server, invalid-response or incomplete-generation failure,
the router records an unavailable category. After two primary failures it skips
that primary for 30 seconds. A subsequent request probes it once and closes the
circuit on success. Fallback runs only if explicitly configured. Ordinary input
or authentication rejection (400/401/403/422) is surfaced without fallback and
does not cause an outage circuit. There is no automatic retry loop.

Native success requires the configured model, `backend=cuda`, nonempty text and
an EOS/length finish. Ollama success requires the configured model, `done=true`,
stop/length completion and nonempty content. Partial timeout answers and replies
from a different model are discarded. A native process crash is handled by its
user service supervisor; lost requests are not automatically replayed.

If HyDE fails, Bifröst uses the raw query and reports `hyde_used=false`. If
embeddings fail, search can use keyword matches and reports degraded mode.
Cluster-label generation has its existing deterministic label fallback. These
failures do not write, re-embed or repair source records.

## Human and AI health

The human workspace's **Knowledge services** card shows the selected chat engine,
readiness and circuit recovery state. After an ordinary service restart, refresh
the page when convenient; it does not forcibly reload an open editing session.

Authenticated `GET /api/health` retains its existing DB/Ollama fields and adds:

```json
{
  "inference": {
    "configured_provider": "aesir",
    "fallback_provider": "ollama",
    "last_provider": "aesir",
    "last_error": null,
    "circuit": "closed",
    "retry_after_seconds": 0,
    "ready": true,
    "embeddings_provider": "ollama"
  }
}
```

This is a schema example, not a captured health witness. `last_provider` may be
null before chat is used. Readiness is cached for ten seconds and observes the
configured model. A ready process can still have an open circuit from recent
generation failures. Configuration errors report `last_error=configuration`
and `ready=false` without returning private paths or credentials.

For network AIs, continue using [AI_CONNECT.md](AI_CONNECT.md), scoped keys,
advertised Bifröst addresses, provenance-preserving read routes and the existing
bounded append queue. `hyde=0` is the ordinary fast search path. Opt-in `hyde=1`
uses the configured chat engine and can take substantially longer. Respect gateway
quotas and Retry-After; do not treat a model outage as permission to bypass auth,
call the DB, change an embedding model or submit duplicate imports.

## Validate, stop and restore

```bash
systemctl --user status aesir-brain.service bifrost.service --no-pager
systemctl --user restart bifrost.service
uv run --frozen pytest -q tests/test_inference.py
```

The focused tests use controlled provider failures; they are not physical GPU
evidence. The full suite includes four DB/worker integrations only when its
isolated test credentials are configured. Do not run ingestion experiments
against the production corpus to validate a chat backend.

For a native update, stop its service before rebuilding and running additional
GPU harnesses. Native allocation admission observes free memory; it cannot
reserve against concurrent Ollama loads. Restart the unit and check authenticated
native health before selecting it again in Bifröst.

To return to the default engine, set backend `ollama`, its actual chat origin and
fallback `none`, then restart Bifröst. The native unit can be stopped independently
with `systemctl --user stop aesir-brain.service`. Chat configuration does not alter
document/chunk counts, source provenance, append roles or embedding identity.

## Ownership for maintainers

`inference.py` owns provider contracts, safe credentials, HTTP client lifetime,
bounded admission and circuit state. `inference.json` owns policy values.
`viewer.py` retains the public `ollama_chat` helper name for compatibility and
delegates it to this router; `ollama_embed` remains separate. A router is created
lazily, so missing optional native configuration cannot stop viewer startup.
Viewer shutdown closes its client. Provider/model/policy changes require restart.

This work established real local socket generation, Bifröst HyDE/search,
supervised native restart and explicit outage fallback separately from the
mocked provider-contract tests. Full-model numerical parity, long-context model
quality, broad GPU/model support and native superiority remain open gates.
