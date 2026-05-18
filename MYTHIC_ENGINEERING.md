# MYTHIC_ENGINEERING.md — Bifröst

> *How to work in this repository under the Mythic Engineering convention.*
> *Read this before opening a session.*

This project follows [Mythic Engineering](https://github.com/hrabanazviking/Mythic-Engineering)
— an architecture-first, vision-led, AI-orchestrated convention for building
software as a living system. This document is the local applied guide.

---

## The Scrolls of This Project

Before touching anything, know what exists:

| Scroll | What it tells you | When to consult |
|---|---|---|
| [`SYSTEM_VISION.md`](SYSTEM_VISION.md) | The soul — what this project exists to do | Any time a decision feels uncertain |
| [`PHILOSOPHY.md`](PHILOSOPHY.md) | The deeper why — values and iron laws | Before any architectural change |
| [`DOMAIN_MAP.md`](DOMAIN_MAP.md) | Realm boundaries — what belongs where | Before adding any new module or feature |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | The bones — major structure and connectors | Before changing how subsystems interact |
| [`DATA_FLOW.md`](DATA_FLOW.md) | Rivers of flow — how data moves through the system | When debugging anything to do with where data comes from or goes |
| [`PROJECT_LAWS.md`](PROJECT_LAWS.md) | Immutable rules | Always |
| [`README.md`](README.md) | Outward-facing intro | When orienting new contributors |
| [`DEVLOG.md`](DEVLOG.md) | What changed, why, what was learned | At session start (to catch up) and close (to record) |
| [`static/README_AI.md`](static/README_AI.md) | Notes for anyone editing the frontend | Before editing `static/index.html` |
| [`docs/bugs/`](docs/bugs/) | Open bug notes from Auditor passes | Before fixing anything not in scope of a new feature |
| [`docs/decisions/`](docs/decisions/) | Architecture Decision Records | When proposing a change that contradicts an earlier decision |

---

## How to Start a Session

1. **Read [`DEVLOG.md`](DEVLOG.md)** end first → end last → most recent entry. Skim everything since you last touched the repo.
2. **Read [`SYSTEM_VISION.md`](SYSTEM_VISION.md)** in full. Even if you've read it before. It is short, and it shapes every decision.
3. **Scan [`docs/bugs/`](docs/bugs/)** for open bug notes. If you're about to work in a domain that has open bugs there, you are likely encountering the same root cause.
4. **State your role.** Each task has a natural role (see below). Naming the role keeps the work focused.

## How to End a Session

1. **Append to [`DEVLOG.md`](DEVLOG.md)** — what changed, why, what was learned, what's still open.
2. **Run the verification ritual** (see "Prophecy Rite" below).
3. **Commit and push** via the Rite of Preservation.
4. **Update any scroll that drifted from reality.** Stale documentation is a bug.

---

## The Six Roles

When operating in this codebase, name the role you are wearing. Roles are
functional, not metaphorical — they have non-overlapping domains.

| Role | Norse name | Personality | Owns |
|---|---|---|---|
| **Skald** | (the poet) | INFJ 4w5 | Naming, framing, philosophy — `PHILOSOPHY.md`, `SYSTEM_VISION.md`, names of new concepts |
| **Cartographer** | (the mapmaker) | INFP 9w1 | Maps, orientation, dependency graphs — `DATA_FLOW.md`, `DOMAIN_MAP.md`, getting un-lost |
| **Architect** | (the planner) | INTJ 5w6 | Boundaries, refactor planning, interface design — `ARCHITECTURE.md`, `INTERFACE.md`, deciding where things live |
| **Forge Worker** | (the maker) | ESTP 8w7 | Code writing, tests, implementation — `viewer.py`, `graph_builder.py`, `static/index.html` |
| **Auditor** | Sólrún Hvítmynd | INTJ 1w9 | Bug hunting, invariant verification, contradiction detection — `docs/bugs/`, code review |
| **Scribe** | (the keeper) | ISFJ 6w5 | Documentation, changelogs, continuity — `DEVLOG.md`, `docs/decisions/`, README_AI files |

Using the wrong role wastes effort. The Skald should not be writing
implementation. The Forge Worker should not be writing philosophy. The
Auditor should not be giving encouragement.

---

## The Five Layers

Every change touches one or more layers. Cross layers with the right role.

```
Layer 1 — VISION       → Skald
Layer 2 — DOMAIN       → Architect
Layer 3 — INTERFACE    → Architect + Auditor
Layer 4 — EXECUTION    → Forge Worker
Layer 5 — VERIFICATION → Auditor
```

Each layer has its own scroll(s). Decisions made at the wrong layer
produce wrong results everywhere downstream.

---

## The Iron Laws of Working Here

Drawn from the canonical Mythic Engineering RULES.AI; absolute and immutable.

1. **Document before code.** Write a markdown file describing what exists,
   propose the change, get approval, *then* write code.
2. **No pseudocode ever.** Use markdown to describe future behavior; never
   pseudo-Python in comments.
3. **Never delete without asking.** Files, functions, modules, data — always
   ask the architect (Volmarr) before removing anything.
4. **Full files only.** When editing a file in a planning doc, show the
   entire updated file. Never deliver fragments or "I added these lines"
   snippets.
5. **Additive bug fixing only.** Fix by adding or correcting; never fix by
   removing structure. Same bug recurring in the same area = structural;
   redesign the domain that produced it.
6. **No `print()` in production code.** Use the `logging` module.
7. **No absolute paths.** Every path is relative or dynamically resolved.
8. **No hardcoded config.** Settings live in `.env`; data in data files.
9. **Cross-platform always.** Linux/macOS/Windows. If a feature is platform-
   specific (e.g. nvidia-smi, systemd), guard it and degrade gracefully.
10. **All subsystems wrap in try/except.** Bifröst does not crash on
    downstream failure; it degrades.
11. **Every endpoint uses `@safely(...)`.** Removing it on even one is a
    regression.
12. **Push often.** Don't accumulate substantial unpushed work.
13. **Type hints on all public function signatures.**
14. **Methods under 50 lines.** One responsibility each.
15. **Folder depth ≤ 4.**

---

## The Bug Hunt Rite (When You Find Something Wrong)

1. **Create a Bug Note** under `docs/bugs/NNNN-short-slug.md`:

   ```markdown
   # Bug: <name>

   **Discovered:** YYYY-MM-DD by <role>

   ## Symptom
   <what is visibly wrong>

   ## Expected
   <what should happen>

   ## Suspected domains
   - <domain a>
   - <domain b>

   ## Invariant violated
   <what truth the bug breaks>

   ## Reproduction
   1. <steps>

   ## Hypothesis
   <best current theory>

   ## Fix plan
   <additive only — never delete structure to fix>
   ```

2. **Invoke the Auditor** (Sólrún Hvítmynd) for confirmation:
   - What symptom is visible?
   - What invariant failed?
   - What domain owns this behavior?
   - Is the bug local (one line) or structural (the domain is wrong)?
   - What changed recently near this boundary?
   - Could the bug be hidden coupling?

3. **For complex bugs**, invoke Cartographer + Auditor together: map where
   the contamination touches; identify the flaw.

4. **Fix additively.** Wrap, redirect, add a new correct path alongside the
   broken one. Never delete structure to fix a bug.

5. **Verify against invariants** (see PROJECT_LAWS.md): IDs unique; saved
   data loadable; public API shape stable; event ordering deterministic;
   state transitions cannot skip stages.

6. **Update the Bug Note** with the fix and any lessons. Close it
   (`STATUS: resolved`) but never delete it.

---

## The Robustness Rite

Daily / per-session hardening pass:

- All subsystems wrapped in try/except with `log.warning(...)` on failure
- Type hints on every function signature
- No `print()` — only `logging`
- Cross-platform: any OS-specific call (`nvidia-smi`, `os.statvfs`,
  systemd, `/proc/*`) guarded with a fallback
- Methods >50 lines flagged as refactor candidates
- Dead code removed (after confirming it's truly dead — `grep` the whole
  tree)
- Documentation reads as truth: any drift between doc and code is fixed
  in the doc
- `.env.example` includes every env var the code reads
- Five layers of testing (Prophecy Rite below) — at minimum the invariant
  layer

---

## The Prophecy Rite (Testing)

Five layers, in increasing scope:

1. **Unit** — pure or mostly-isolated logic
2. **Boundary** — confirm interface contracts between modules
3. **Integration** — confirm domains work together
4. **Regression** — preserve previously correct behavior through refactors
5. **Invariant** — verify the immutable truths the system must always obey

Bifröst's invariants live in `PROJECT_LAWS.md`. Start writing tests at
the **invariant layer** and work outward.

---

## The Rite of Preservation (Commits)

```
<short subject line, under 70 chars>

<blank line>

<paragraph or two on the WHY — what changed and why it changed>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

When pair-engineered with an AI, add the `Co-Authored-By` line. Use
multi-line message via `git commit -m "$(cat <<'EOF' ... EOF)"`.

## The Rite of Return (Reverts)

Use `git revert <sha>` to undo a pushed commit by appending an inverse
commit. **Never** `git reset --hard` anything pushed; never `--force-push`
anything other than your own ephemeral branches.

---

## The Plundering Workflow (If You Adapt Upstream Code)

If a future feature adapts code from an open-source project, follow the
[canonical Plundering Workflow](https://github.com/hrabanazviking/Mythic-Engineering/blob/main/MYTHIC_ENGINEERING_PLUNDERING_WORKFLOW.md):

- Attribution mandatory in `LICENSE` / `NOTICE` / `THIRD_PARTY_NOTICES.md`
- Create `docs/plunder/<UPSTREAM>_PLUNDER_MAP.md` mapping what was taken
- Pass license review, architecture review, security review, integration
  tests before merging

We have not yet plundered anything; this guidance is here for when we do.

---

## A Word from the Architect

The reason we do this is not that "more documentation is better." It is
that **a system that remembers what was decided is a system that does not
re-litigate every decision.** Every scroll above represents a debate that
is now over. Future contributors (human and AI) can read what was decided,
why, and move on. That is what compounds.

If you find yourself wanting to break one of the iron laws "just this
once": stop. Open a Bug Note. The Auditor will hear you out. If the law
deserves an exception, document it as an ADR under `docs/decisions/`. Then
proceed. *Earned* exceptions are fine; *silent* exceptions are how
systems rot.

— Volmarr Wyrd, architect-in-chief, May 2026
