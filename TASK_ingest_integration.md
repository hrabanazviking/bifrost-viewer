# Task: publish the complete ingest component with Bifröst

Date: 2026-09-30. Authorized directly by Volmarr: attach the unpublished ingest
component to the Bifröst viewer and push its code there.

## Current state and target

The private sibling ingest directory contains the CLI, schema, frozen dependencies
and five regression tests, but has no Git remote. Only its supervisor is published.
Move ownership of these sources into ingest/ in the Bifröst repository. Keep the
inbox, retry state, private environment and knowledge database in their current
locations. The running watcher and URL-ingest route must execute the published
copy, while legacy local CLI/watch entry points forward to it.

## Boundaries and invariants

Preserve documents, embeddings, inbox files and current access credentials. No
schema migration or production deletion. Exclude .env, corpus inputs, runtime state
and virtual environments from Git. The existing CLI commands remain supported.
Separate source project, configuration file and durable inbox paths explicitly.

## Implementation and verification

Publish ingest.py, schema.sql, pyproject.toml, uv.lock, safe configuration example,
regression tests, README_AI.md and INTERFACE.md under ingest/. Update viewer.py,
scripts/watch_inbox.py, the watcher unit and architecture/operations documentation.
Add boundary tests for the separated source/data paths. Install the frozen ingest
runtime, switch local entry points and services, and verify duplicate-safe ingestion
against the existing maintenance document without adding or removing corpus rows.
Run both viewer and ingest suites, scan staged content for credentials and runtime
artifacts, then commit, push and verify remote main matches the tested source.

The current configured access token was read locally and successfully checked
against the running API. Its value belongs in private configuration, not this file.

## Completed verification

32 combined viewer/ingest tests pass, including the two new source/state boundary
tests and the five migrated ingest regressions. The separate frozen ingest runtime
passes its five tests and dependency compatibility check. Changed Python sources
pass Ruff and Git whitespace checks. The installed watcher now executes the bundled
source with the existing private dotenv and inbox paths. Both services are active.
A live duplicate-safe canary completed without changing the 1235-document/49004-chunk
corpus. A live URL-ingest job executed the bundled runtime and correctly reported
an intentionally unreachable local source as failed. Legacy CLI invocation and its
five tests still work through the compatibility entry point. API access with the
existing configured token was verified successfully. No credentials or inbox data
are part of the staged source.
