# Task: portable recovery and safe delegated AI access

Date: 2026-09-30. Volmarr authorizes configurable email recovery to his supplied
address, portable security settings, stronger communications and non-destructive,
flood-resistant access for outside AIs he authorizes.

## Existing and desired architecture

The viewer currently accepts one shared token for every route and spawns an ingest
process for every URL request. It has no email transport, scoped keys, durable API
queue or admission quotas. Preserve read/search response shapes and existing data.
Give owner administration a strong local credential, maintain legacy read access,
and allow revocable, expiring AI keys limited to read and optional append-ingest.
No remote delete, arbitrary command or schema-migration capability is introduced.

## Owning domains and files

security/ owns private SQLite credential metadata, single-use expiring recovery,
verified recovery-email changes, TLS SMTP configuration, request admission and
persistent bounded job supervision. viewer.py delegates through public interfaces.
ingest/safe_fetch.py owns pinned-address public URL fetching with redirect checks,
TLS validation and response limits. The ingest CLI remains the only document writer.
static/security.html and static/security.js provide owner settings and recovery UI.
The launcher reads a local owner credential without printing it. Configuration,
keys, queue payloads, mail secrets and audit state live outside Git in user state.

## Invariants and verification

No source-table deletion or destructive migration. Preserve inbox state and corpus.
Keep bearer compatibility; the old shared credential becomes read-only so it cannot
administer the server. AI keys are separately revocable and never gain owner scope.
Protect writable jobs with quotas, idempotency, queue capacity, worker timeouts and
resource ceilings, and an append-only database role. Protect HTTP bodies, hosts,
origins, forwarding headers, response headers and transport boundaries. Email
recovery cannot revoke access until a valid one-use code is confirmed. Verification
of a replacement email precedes activation. SMTP requires TLS and owner-provided
credentials; no transport credentials were found during discovery.

Add isolated tests for authentication scopes, expiry/revocation, recovery replay,
email verification and delivery failures, rate/size/queue admission, SSRF/redirects,
worker recovery and append-only permissions. Run regression suites, test live
read/recovery/ingest boundaries without destructive data changes, update contracts
and operations docs, and push reviewed source to GitHub. SMTP credential setup is
requested asynchronously while independent implementation proceeds.
