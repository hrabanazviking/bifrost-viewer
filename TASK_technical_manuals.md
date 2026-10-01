# Task: second-brain technical manuals

Date: 2026-09-30

## Target and ownership

Document the installed second brain and its component boundaries under Mythic
Engineering's Cartographer, Scribe and Auditor roles. This is documentation work:
the viewer, security gateway, parser, private inbox, Skein, Skry and desktop gauges
retain their current behavior, credentials, data and service configuration.

## Current state

Bifröst owns display/search, disposable layouts, owner recovery and bounded AI
access. Its ingest/ subproject owns canonical parser source; the sibling ingest/
directory holds private configuration, retained inputs and compatibility launchers.
Skein maintains derived entity tables; Skry performs read-only entity lookups.
The eww repository supplies desktop hardware gauges. The existing README and
interface documents describe contracts, but lack a connected operator manual.

## Deliverables

- SECOND_BRAIN_MANUAL.md: stack map, everyday use, service operations, GPU checks,
  backup/restore, migration, updates and troubleshooting.
- TECHNICAL_MANUAL.md at the Bifröst, Skry, Skein and eww project roots.
- ingest/TECHNICAL_MANUAL.md and security/TECHNICAL_MANUAL.md in Bifröst.
- A local TECHNICAL_MANUAL.md beside the private ingest inbox, explaining retained
  state and compatibility wrappers without copying its secrets into Git.
- Navigation links in existing README files and an appended DEVLOG entry in each
  published project.
- A user-facing Markdown bundle in the current chat's outputs directory.

## Execution and verification

1. Read source, CLI options, service templates and interface contracts.
2. Write complete manuals with executable examples and clearly labeled prerequisites.
3. Cover recovery, delegated keys, limits, idempotency, transport, sandbox boundaries,
   trustworthy source preservation and limits of automatic recovery.
4. Verify commands using read-only help/status checks, validate Markdown navigation,
   and review diffs for secrets and unintended non-document changes.
5. Commit and push documentation to each existing GitHub repository. No credentials,
   inbox content, live database, private state or runtime files are published.

## Invariants

- Original knowledge and inbox inputs remain untouched.
- No application code, schema, settings, keys or service state changes are needed.
- Commands distinguish trusted owner CLI operations from scoped outside-AI access.
- New-install, recovery and destructive maintenance prerequisites are explicit.
- No generic driver-install command is represented as portable across distributions.
- Documentation states what is implemented; it makes no guarantee of bug freedom.

## Documentation verification — 2026-10-01

Eight complete manuals were prepared in their owning component folders, including
the private inbox's local-only guide. Checked 89 local links/anchors, Bash syntax
for 41 command blocks and Python syntax for both API examples without errors.
Read-only CLI help verified ingest, Skry and Skein option names; installed eww
help and current service/NVIDIA state were inspected. Git diffs contain only
Markdown documentation; no runtime/data/configuration or service changes are
part of this task. The manuals explicitly cover capacity limits and isolation
boundaries without claiming unlimited automatic repair or successful SMTP setup.
