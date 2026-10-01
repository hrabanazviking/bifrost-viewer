# Owner recovery and outside-AI access: technical manual

Source-verified on 2026-10-01. This manual describes Bifröst's security boundary,
not a guarantee that every service on the machine is inaccessible. Start with the
[stack manual](../SECOND_BRAIN_MANUAL.md) for everyday use and backup/restore.

## 1. Owner, delegated key and private state

The owner has `read`, `ingest` and `admin`. Delegated keys can have `read` or
`read` plus `ingest`; they cannot receive `admin`. Scope checking happens before
request-body parsing. Read access exposes the corpus, not a per-document subset.
Only authorize a reader who may see the whole knowledge database.

First startup creates a strong random owner credential. Open it through:

```bash
cd "$HOME/ai/ingest-viewer"
uv run --frozen python scripts/open_brain.py
```

The optional old `VIEWER_TOKEN` is a read-only migration key with a one-day grace
period. It cannot manage settings, rebuild graphs or append. Revoke it after
replacing integrations with separate named keys; an expired migration key is not
a service outage.

Private state defaults to `$XDG_STATE_HOME/bifrost`, normally
`~/.local/state/bifrost`. `VIEWER_SECURITY_DIR` relocates it. Important files include
`access.sqlite3`, restricted-worker `ingest.env`, queued payloads/logs and effective
worker limits. Preserve the entire directory with services stopped. Directory
mode is `0700`; credentials are `0600`. AI secrets are hashed; the local launcher
credential and SMTP password remain recoverable local secrets. A person controlling
your Unix account can read them, so encrypted external backups matter.

No browser localStorage keeps credentials. **Lock** clears page credentials, and
refresh requires signing in again. Do not share an owner fragment URL, screenshot
of an issued key, state backup or browser developer-tools output.

## 2. Configure email delivery

1. Open the owner launcher and choose **security & recovery**.
2. In **Mail delivery**, choose the intended SMTP host, port, TLS mode, username
   and From address. Paste the provider's app password locally in the masked field.
3. Choose **Save mail settings**. A saved configuration is not proof of delivery.
4. Under **Recovery email**, enter the recipient and choose **Send verification code**.
5. Copy the code from the received message and choose **Verify and activate address**.
6. Confirm the page reports the address verified. Until then public recovery cannot
   deliver a usable owner-recovery code for it.

Gmail defaults:

| Field | Value |
|---|---|
| SMTP host | `smtp.gmail.com` |
| Port | `587` |
| TLS mode | STARTTLS |
| Username | Full Gmail address |
| From | Address the SMTP account may send as |
| Password | Google app password, not your normal login password |

Google requires an eligible account with two-step verification for app passwords.
Some organizational/Advanced Protection accounts cannot use them. Changing your
Google account password can revoke app passwords; replace the saved one afterward.
See [Google's instructions](https://support.google.com/mail/answer/185833).
Bifröst currently uses SMTP credentials, not Google OAuth or a Codex mail connector.
Use another TLS SMTP relay if your account policy does not permit this method.

Only verified STARTTLS or TLS-from-start connections are supported. SMTP login
occurs after certificate verification. The API never returns the saved password.
Leaving the password empty preserves it only when host, port, mode and username
stay the same; changing those clears it unless a replacement is supplied.
The password field clears after saving. The sender must be an address permitted
by the provider; provider spam/delivery policy still applies.

### Change the email or SMTP provider

Configure and test the new relay, then request verification at the replacement
recipient. The current recovery email stays active until the new code is confirmed.
Failed delivery does not remove the existing address or revoke owner access.
Update recipient and sender deliberately: they are independent settings.

## 3. Recover owner access

1. Visit `/security` even while locked out.
2. Under **Recover owner access**, enter the verified recovery address and request
   a recovery code. The public response is generic to avoid mailbox enumeration.
3. Read the email and confirm its code within **15 minutes**.
4. Save the replacement owner token in your private credential store. Confirmation
   invalidates the previous owner token and outstanding recovery codes and updates
   the local launcher's stored credential. Other owner sessions must sign in again.

Each code is random, hashed in storage and single-use. A failed send cancels its
code. A request alone never replaces the owner token. Verification codes and
recovery codes have different purposes; use the form that matches the email.
An outdated-email recovery code cannot take over after a replacement is activated.

If email is unavailable but the Unix account and private state are intact, use
the desktop launcher. If private state was lost, restore its encrypted backup;
creating new blank state does not restore old AI keys, verified mail settings or
pending jobs. There is no remote master-password bypass.

## 4. Authorize an outside AI

Choose **Authorized AIs** in owner settings:

1. Give each integration a meaningful distinct name.
2. Start with **Read only**. Enable **Read and append** when it should add documents.
3. Set expiry from 1 to 365 days; default is 30 days.
4. Set quotas at or below server ceilings. A per-key quota cannot increase a
   server maximum. The byte quota is admission volume, not available database size.
5. Create the key and copy its secret once into that client's secret manager.
6. Check `/api/auth/me` and `/api/capabilities` using the issued key.
7. Revoke the key when retiring or replacing the integration.

At most 64 unrevoked non-owner keys are supported by default; revoke expired keys
to free their slots, and the migration key also counts until revoked. You cannot retrieve
a delegated secret later; issue a replacement and revoke the lost one. A key's
name is metadata, not permission. Keys are not scoped to individual documents.
Revocation blocks new requests and queued jobs; an already running atomic append
can finish. Existing knowledge is not removed when a key expires or is revoked.

Treat external AI writes as untrusted knowledge with provenance, not automatic
instructions for privileged actions. The admission layer prevents unbounded
submissions but does not judge factual quality or eliminate prompt injection from
source text. No approval/review queue for document content is implemented.

## 5. Copyable API requests

These Bash examples prompt for the secret without recording it in command history.
The helper sends the bearer header through curl's standard input, avoiding a
literal secret in curl's command-line arguments. Do not enable shell tracing or
curl verbose tracing while using it. A server client does not need browser CORS.

```bash
export BIFROST_URL=http://127.0.0.1:8731
read -r -s -p 'Delegated AI key: ' BIFROST_AI_KEY
printf '\n'
bifrost_auth() {
  printf 'header = "Authorization: Bearer %s"\n' "$BIFROST_AI_KEY"
}
bifrost_auth | curl --fail-with-body --silent --show-error --config - \
  "$BIFROST_URL/api/auth/me"
bifrost_auth | curl --fail-with-body --silent --show-error --config - \
  "$BIFROST_URL/api/capabilities"
bifrost_auth | curl --fail-with-body --silent --show-error --config - \
  --get --data-urlencode 'q=the well of wisdom' --data 'k=8' \
  "$BIFROST_URL/api/search"
```

Set `BIFROST_URL` to the authorized tailnet/HTTPS endpoint for a remote client.
The localhost URL only works on the server itself.

With a read-and-append key, submit a deliberately chosen document:

```bash
bifrost_auth | curl --fail-with-body --silent --show-error --config - \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: my-agent-note-2026-09-30-001' \
  --data '{"title":"An observation","text":"The source text to preserve."}' \
  "$BIFROST_URL/api/ingest/text"
```

Text titles are 1–200 characters with no C0/DEL controls; text is 1–200,000
characters, nonblank and without NUL. The **256 KiB total JSON body limit** also
applies, so UTF-8 bytes/JSON escaping can make the byte ceiling bind first.

For a URL use `POST /api/ingest/url` with `{"url":"https://example.com/"}`.
Save the returned `job_id`. Poll with the same key, replacing `JOB_ID`:

```bash
bifrost_auth | curl --fail-with-body --silent --show-error --config - \
  "$BIFROST_URL/api/ingest/jobs/JOB_ID"
unset BIFROST_AI_KEY
```

Poll every 5–10 seconds with a finite deadline rather than a tight loop. Statuses
are `queued`, `running`, `ok`, `failed`; responses also include stage, progress,
attempts and compatible `started_at`/return-code fields. Owner job listing sees all;
a delegated identity sees only its own jobs, with the latest 100 in the list.
Raw worker logs are private and are not returned to that AI. Live stage markers
cover parsing, validation, embedding and persistence; status also reports
`error_category`, `next_attempt_at`, `owner_retries` and optional integer
`doc_id`/`chunks`/`embedded`. Stale markers from previous attempts are ignored.

### Idempotency and retries

- Assign an ASCII `Idempotency-Key` of at most 128 characters to each logical
  submission and retain the exact payload with it.
- After a timeout or uncertain response, retry that **same key and payload**.
  It returns the original job without charging the reservation again.
- Reusing that key for changed content returns `409`. Keys are namespaced by
  client identity; replacing the AI credential is not the same submission namespace.
- Respect `Retry-After` on `429`, use bounded backoff/jitter and stop retrying when
  a human/configuration error needs correction.
- Job acceptance is not indexing completion. Content-hash deduplication also
  avoids duplicate source insertion if an interrupted job is replayed. This is
  not a distributed exactly-once guarantee.

## 6. Default capacity and rate limits

The source of truth is [limits.json](limits.json). `GET /api/capabilities` returns
active server values. Daily budgets reset on **UTC day boundaries**, independently
of the operator's local timezone. Ordinary requests cost 1; query/path/Skry/URL
validation costs 10 and graph requests cost 20.

| Control | Default |
|---|---|
| Per AI weighted requests/minute | 120 |
| Per AI submissions/minute | 3 |
| Per AI documents/UTC day | 20 |
| Per AI admitted payload bytes/UTC day | 2 MiB |
| Global untrusted requests/minute | 1200 |
| Independent owner requests/minute | 600 |
| Public recovery traffic/hour/IP | 20 |
| Invalid auth/hour/IP | 30 |
| Recovery/verification mail requests/hour | 3 for each configured mail budget |
| Request body / headers | 256 KiB / 32 KiB |
| Request body deadline | 10 seconds |
| Server / expensive-request concurrency | 16 / 2 |
| Active API jobs / pending per key | 32 / 4 |
| API workers | 1 serial worker |
| Retained jobs / payload reservations | 1024 / 256 MiB |
| Total / per-job worker logs | 64 MiB / 8 MiB |
| Worker wall / CPU deadline | 300 / 120 seconds |
| Worker virtual memory / tmp | 6 GiB / 64 MiB |
| Attempts / retry base | 3 / 30 seconds |
| Public URL response / redirects | 2 MiB / 4 |

Each URL submission reserves the full **2 MiB** response allowance. Therefore the
default daily byte quota admits at most **one URL/day**, even when the URL string
is tiny. Trusted local inbox ingestion is separately configured and does not use
these HTTP quotas.

For server ceiling changes, create an owner-controlled JSON file containing only
reviewed overrides, set `VIEWER_LIMITS_FILE` to its absolute path and restart the
viewer. Example content for a server deliberately sized for two URL admissions
per key/day is `{"ai_bytes_per_day":4194304}`. Unknown or non-positive/non-integer
values fail validation. A server change does not automatically increase existing
key quotas; issue a replacement with reviewed quotas when needed. Increasing
limits does not grant more permissions or remove worker/transport checks.

Retained payloads are not automatically discarded. When count/disk reservation
budgets fill, admission fails explicitly. There is no owner purge button or
general cleanup command in this release. Stop services, preserve the entire state
and review archival/metadata maintenance before any intentional cleanup. Do not
delete `access.sqlite3` or reset identity to bypass capacity.

## 7. Worker isolation and database permissions

The API parser requires a frozen `ingest/.venv` and private append-role config.
Provisioning is an owner-run operation with Bifröst stopped:

```bash
cd "$HOME/ai/ingest-viewer"
uv sync --frozen --project ingest
systemctl --user stop bifrost.service
uv run --frozen python scripts/setup_append_role.py
systemctl --user start bifrost.service
```

Stop on a provisioning error and inspect it before restart. The script creates or
rotates `bifrost_api_ingest`: SELECT/INSERT on documents/chunks and sequence usage,
no UPDATE/DELETE/TRUNCATE/TRIGGER/schema CREATE, no superuser/inherited roles and
bounded connections/statements/locks. It refuses unsafe pre-existing role grants.
Existing source tables must already exist. Remote DBs need explicit password-auth
rules and TLS in the private connection URL; never expose owner credentials.

Bubblewrap exposes only runtime/parser files, public system libraries/CA/DNS files,
the restricted worker config, effective limits and the job's payload. It isolates
user/PID/IPC/UTS namespaces, drops capabilities and bounds resources. Owner state,
SMTP secrets, project dotenv, inbox, home and the host DB Unix socket are hidden.
Failure to create the sandbox fails the job; there is no unisolated fallback.

Networking remains available for configured PostgreSQL/Ollama and approved public
web fetches: **this is not a network jail**. Keep those services independently
protected. Sandbox/append-only permissions limit damage but are not a promise of
bug-free software or protection from a fully compromised owner account.

New API documents receive server-assigned `api_job_id`/`api_client_id` metadata.
Text sources use `bifrost-api://CLIENT/JOB`. Existing hash matches keep original
provenance rather than being rewritten by a later submitter.

## 8. Transport and browser compatibility

| Connection | Requirements |
|---|---|
| Same-machine browser/API | Loopback HTTP or correctly configured TLS |
| Authorized Tailscale client | Explicit tailnet listener and tailnet peer; approved Host |
| Public/LAN client | HTTPS; correctly named certificate and explicit allowed Host |
| Browser on another origin | Exact `VIEWER_ALLOWED_ORIGINS` entry as well as a scoped key |
| Server-to-server client | Bearer auth and allowed transport/Host; no CORS requirement |

Native HTTPS requires both `VIEWER_TLS_CERT` and `VIEWER_TLS_KEY`, with a certificate
covering the hostname clients use. Add that hostname to `VIEWER_ALLOWED_HOSTS`.
Do not bypass certificate checks with curl `-k`. The current installation is private
loopback/Tailscale; this guide does not publish it to the internet.

A TLS reverse proxy may reach Bifröst on loopback, but it must enforce its own
upstream access/request policy. Explicitly allow its public Host and browser HTTPS
Origin. Forwarded headers are deliberately ignored, so proxy termination does
not magically change Bifröst's transport classification. Do not add wildcard
CORS or public forwarding to make a client error disappear.

URL fetching rejects private/reserved DNS answers, URL credentials, non-web ports,
compressed bodies and oversized responses. It pins sockets to validated public
addresses, retries only validated candidates and revalidates every redirect;
HTTPS verifies the original hostname. Owner CLI URL fetching uses this same policy.
Download an intentionally trusted private source separately and ingest its local
file through the trusted owner workflow instead.

## 9. Failure meanings and operations

| Response/symptom | Meaning and action |
|---|---|
| 401 | Missing, expired, revoked or invalid key; check identity/expiry |
| 403 | Valid key lacks required scope, or request origin/transport is forbidden |
| 400 / 422 | Input validation failure; fix the payload rather than retrying |
| 409 | Idempotency conflict or an unavailable prerequisite graph |
| 408 | Request-body deadline exceeded; correct slow/incomplete upload behavior |
| 413 / 431 | Body / header capacity exceeded; reduce the corresponding input |
| 429 | Quota/concurrency/mail or retained-budget bound; honor `Retry-After`, but full retention also needs owner maintenance |
| 503 | Required service, worker config or sandbox unavailable |
| Recovery request 202, no email | Generic acknowledgment; check verified address, relay and delivery locally |
| Job failed | Check private worker log and current DB/model/sandbox; bounded attempts are exhausted |

Statuses and queue state survive restarts; interrupted work returns to the queue.
Follow [stack backup/restore](../SECOND_BRAIN_MANUAL.md#back-up-and-verify).
Inspect `journalctl --user -u bifrost.service` locally, without uploading secrets
or raw knowledge. Validate changes with `uv run --frozen pytest -q` from the root.
The exact HTTP contracts are recorded in [INTERFACE.md](INTERFACE.md).

## 11. Owner ingestion recovery

Unlock `/security`, then use **Ingestion recovery → Refresh ingestion status**.
The panel shows the queue supervisor, retained-job budget, local inbox stage and
job attempts/progress. A failed job shows its category. Correct the actual input,
model, SQL configuration or dependency first. **Retry original job** calls the
owner-only retry route without replacing its original payload, client or quota
reservation. A client which has expired or been revoked remains blocked. There
are at most three deliberate owner retries per job by default, in addition to
bounded automatic temporary-failure attempts. Retrying a successful, queued or
running job is refused. Retained payload/log ceilings continue to apply.

`GET /api/admin/ingest/status` returns aggregate queue counts/budgets and sanitized
local inbox health. `POST /api/admin/ingest/jobs/JOB_ID/retry` accepts an empty
JSON object using the owner bearer header. Read/append AI keys cannot call either
route. API job status remains limited to its own identity. See the
[ingest manual](../ingest/TECHNICAL_MANUAL.md#10-read-only-diagnosis-and-recovery-decisions)
for CLI exit classes and the read-only database doctor.
