# Bifröst security and portable access

This domain owns credentials, recovery and admission. It never updates or deletes
knowledge. Read [INTERFACE.md](INTERFACE.md) before changing the protocol.

## Owner access and email

The first start generates a strong owner token in `$XDG_STATE_HOME/bifrost`
(normally `~/.local/state/bifrost`). Use the desktop launcher or
`uv run --frozen python scripts/open_brain.py` to open it without printing the key.
The optional old `VIEWER_TOKEN` grants only read access for one day after migration;
the owner can revoke it earlier. New installations should leave it blank.

Open **Security & recovery**, enter TLS SMTP settings, and save an app password
locally. Gmail defaults are `smtp.gmail.com`, port `587`, STARTTLS, your full email
address for username/from. Gmail requires an account that supports app passwords
with two-step verification enabled; see [Google's instructions](https://support.google.com/mail/answer/185833).
An account that does not support this can use another TLS SMTP provider. This
implementation does not reuse Codex connector credentials or browser sessions.

Send and confirm the verification code before an address becomes the active recovery
address. Changing the address requires verification of the replacement; the old one
remains active until then. Recovery sends a random single-use code, valid for 15
minutes. Confirm it to receive the replacement owner token. Existing owner access
remains valid until confirmation. Confirmation invalidates other outstanding
recovery codes. Failed delivery cancels its code without changing existing access.
Changing SMTP endpoints clears a saved password unless a new one is supplied.

SMTP credentials are saved server-side, never returned to a browser, and used only
after verified TLS negotiation. The UI clears the password field after saving.
SMTP setup and actual delivery must be verified on each installation; test coverage
alone is not evidence that a mailbox received an email.

## Enable bounded HTTP ingestion

Prepare the separate frozen parser environment and provision its restricted account:

```bash
uv sync --frozen --project ingest
systemctl --user stop bifrost.service
uv run --frozen python scripts/setup_append_role.py
systemctl --user start bifrost.service
```

Provisioning uses the owner database configuration to create `bifrost_api_ingest`.
It grants SELECT/INSERT on documents/chunks and sequence access, with connection
and statement/lock/transaction deadlines. It refuses destructive grants or schema
CREATE access. It never migrates source tables. The password/config is private and
is not returned to AI clients. Configure `VIEWER_API_DB_HOST` if the database is on
another machine; PostgreSQL must accept the restricted role through password auth.
For a remote database, enable database TLS in the private worker connection URL.
The script targets the standard public ingest schema.

Each AI needs its own named key. Grant **read**, or **read and append**, choose expiry
and quotas, and copy the generated secret once. Give that key only to the AI you
authorize. Revoke it in settings to block new requests and queued submissions.
An already running atomic append can finish; revocation never deletes its data.
Keys cannot gain admin, update/delete, arbitrary SQL, filesystem paths or commands.
Accepted AI documents record server-assigned job/client IDs in source metadata.
Existing hash matches are preserved rather than modified to add metadata.

## Limits and failures

`limits.json` is the reviewed default; `VIEWER_LIMITS_FILE` selects an owner-managed
partial JSON override; unknown settings and non-positive/non-integer values are
rejected. Quotas can be reduced per key. Defaults are 120 weighted requests/minute,
3 submissions/minute, 20 documents/UTC day, and 2 MiB admitted payload/UTC day.
Search, path, Skry and URL validation cost 10; graph responses cost 20; ordinary
reads cost 1. Expensive requests have a global concurrency ceiling of 2.
Public, invalid-auth and delegated traffic also share a 1200-request/minute global
ceiling. Owner administration retains its independent budget. Retry-After identifies
the next relevant minute/hour/UTC-day boundary.

Bodies are capped at 256 KiB, headers at 32 KiB, with a ten-second body deadline.
There are at most 32 active API jobs and four pending jobs per key. The serial
worker has a 300-second wall deadline, 120 CPU seconds, 6 GiB virtual memory,
bounded descriptors and an 8 MiB log ceiling. There are at most three attempts with
backoff. Total private worker logs are capped at 64 MiB, retained job count at 1024,
and admitted payload reservations at 256 MiB. Payloads and logs remain private.
Source payload files are retained; no automated purge of source inputs is performed.

The HTTP worker requires Linux/Bubblewrap with user namespaces enabled. It starts
with an allowlisted environment, a minimal read-only filesystem, isolated user/PID/
IPC namespaces, dropped capabilities and a 64 MiB temporary filesystem. It sees
the parser runtime, its restricted worker configuration and its own payload. It
cannot see the owner access database, mail secrets, project dotenv, inbox, home or
host PostgreSQL Unix socket. Networking remains enabled for configured database/
model services and validated public URL retrieval; it is not a network jail. The
trusted local CLI remains a separate path. Failure to create the sandbox is explicit,
and no unisolated fallback runs.

URL jobs reserve the full 2 MiB maximum fetch size against byte quotas, so a key with
the default byte quota admits at most one URL per UTC day. This conservative charge
prevents clients from using a tiny URL string to fetch unlimited large documents.
Redirects are revalidated, all DNS answers must be global addresses, sockets connect
to a validated address, and HTTPS still verifies the original hostname. Only web
ports 80/443 are accepted; credentials, compressed responses and oversized documents
are rejected. These restrictions also apply to URL ingestion through the bundled CLI.

429 responses include Retry-After. Reuse Idempotency-Key after an uncertain submit
response; the same key/payload returns the original job without charging quotas
again. A different payload with the same key returns 409. Job acceptance is not
database completion: poll until `ok` or `failed`. Failed jobs expose a generic
message; detailed logs are available only in private local state. Never retry
forever. Local trusted inbox ingestion is independently configured and serialized
by its existing supervisor; it does not use HTTP client quotas.

When retained budgets fill, admission fails explicitly. Stop the service, preserve
and archive the entire private state to owner-controlled storage, then review queue
metadata and successful payloads before any intentional cleanup. Do not delete
the access database or regenerate credentials to bypass a full queue. Larger limits
should be reviewed against available CPU, memory and disk before restarting.

## Communications and portability

The default listener is loopback plus the configured tailnet interface. Cleartext
HTTP is admitted only on loopback or an explicitly bound Tailscale address with a
tailnet peer. Other peers require HTTPS. Native TLS uses `VIEWER_TLS_CERT` and
`VIEWER_TLS_KEY`; the certificate must cover the hostname clients use. Add the
hostname to `VIEWER_ALLOWED_HOSTS`. Uvicorn ignores forwarding headers. For an
owner-controlled TLS reverse proxy on loopback, explicitly allow its public Host
and HTTPS Origin; the proxy must authenticate/restrict upstream access and enforce
request limits. Do not enable public forwarding or wildcard CORS as a shortcut.
Browser AI clients need an exact `VIEWER_ALLOWED_ORIGINS` entry; server-to-server
clients with bearer headers do not need CORS. Database and Ollama network policies
remain separate infrastructure boundaries; never distribute their credentials to
outside AIs as a substitute for a Bifröst scoped key.

Token fragments are removed from the address bar/history after loading. Credentials
remain in page memory; refreshing requires the launcher or signing in again. Tokens
are never placed in localStorage. Responses use no-store, no-referrer, nosniff,
frame restrictions and CSP; access logging is disabled to avoid query-token leaks.
API validation and internal errors omit submitted secrets and internal exceptions.

To move installations, stop the service and copy the entire private state directory
through encrypted owner-controlled storage, restore directory mode 0700/files 0600,
and set VIEWER_SECURITY_DIR. Preserve `.env`, the knowledge database and independent
inbox separately. Reprovision the worker account if the database changes. Keys,
email settings, idempotency and queued work survive when this state is retained.
Keep encrypted backups. Owner launcher and SMTP credentials are recoverable local
secrets, not encrypted against an attacker who already controls your Unix account.

The design follows [OWASP REST security](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html),
[recovery guidance](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)
and [SSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).
