# SYSTEM_VISION.md — Bifröst
## *The Genesis Scroll*

> Sacred and unchanging. If a future change to this project does not serve what
> follows, the change is wrong — not this scroll.

---

## Name and Nature

**Bifröst** — the shimmering bridge between the realm of raw knowledge and the
realm of human sight. It is a small local service that takes a Postgres
database of embedded text chunks and renders it as a 3D, navigable
constellation in the browser.

It is **not** a knowledge-base, nor a search engine, nor an LLM. It is a *lens*
through which all three can be looked at, walked through, and understood.

---

## Purpose — The Great Why

To make a corpus *visible* and *touchable*.

A vector store full of embeddings is technically a knowledge graph; humans
cannot see it. Bifröst projects that hidden geometry into 3D space, colors it
by source and by topic, draws the implicit similarity edges, lets you click
through chunks, ask questions of the corpus, and follow paths through it. The
goal is intuition — to let the architect of the corpus *feel* what is in there
and what is connected to what, without needing to query.

This is the difference between owning a library and being able to walk it.

---

## Primary Rite — Core User Interaction

> Open a browser to the local tailnet URL. Watch the bridge open. See your
> 20,000 chunks float in space, colored by document. Click one and read it.
> Type "Odin and Mímir" and watch matching chunks pulse. Shift-click two
> chunks and see the glowing shortest path between them. Switch to the
> ENTITIES layer and walk the woven graph of named things Skein has spun out
> of the embeddings.

If the Primary Rite ever feels heavy, slow, or punishing — Bifröst has drifted
from its vision and must be returned.

---

## Feeling / Vibe

- **Cyber-Viking awe.** The bridge of Asgard rendered as glowing neon
  constellations.
- **Instant responsiveness.** The page must *never* hang silently. If
  something is slow, the user must see *what* is slow and how long it will
  take.
- **Inviting exploration.** Every node, every edge, every panel should
  encourage one more click.

---

## Unbreakable Vows

1. **The Bridge Shall Never Block in Silence.** Every long operation reports
   live progress. The "opening the bridge" loader must always say *what stage*
   and *what percentage*. A user staring at an unmoving page is the worst sin
   Bifröst can commit.

2. **The Bridge Shall Not Cost.** Bifröst runs entirely on local hardware
   against a local Postgres and a local Ollama. It must never require a paid
   API or a cloud subscription to display the corpus.

3. **The Bridge Shall Not Lose Work.** Caches are invalidated by data
   fingerprint, not deleted by mistake. Long builds run in the background,
   detached from any one browser tab, so a refresh never destroys progress.

4. **The Bridge Shall Be Truthful.** When something fails, Bifröst says so —
   visibly, with the stage that failed and an honest error. Silent half-loads
   are forbidden.

5. **The Bridge Shall Tail the Wind, Not Fight It.** It reads from the
   knowledge DB. It does not modify documents or chunks. It only writes its
   own derived caches and the Skein KG tables. The source of truth stays
   sacred.

6. **The Bridge Shall Honor the Corpus.** All ingested content, no matter how
   strange or personal, is rendered with equal dignity. Bifröst does not
   filter, censor, or hide its architect's wyrd designs.

---

## What This Project Is Not

- Not a content-management system. (See [the Ingest project](../ingest/) for
  that.)
- Not the source of truth for knowledge. (That is Postgres + pgvector.)
- Not a knowledge-graph extractor. (See [`skein-kg`](../skein-kg/) for that.)
- Not a query-time entity tool. (See [`skry-kg`](../skry-kg/) for that.)
- Not a multi-tenant service. Bifröst is a personal lens for one corpus owner.

Bifröst is the *theatre* in which all the other tools display their work.
