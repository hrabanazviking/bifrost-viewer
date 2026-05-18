# PHILOSOPHY.md — Bifröst

> *Written by the Skald. Speak of why before how.*

---

## The Wound This Project Salves

Knowledge that you cannot *see* is knowledge you cannot *trust*.

A vector store full of embeddings is, technically, a knowledge graph. The
geometry is in there: this chunk huddles near those chunks, this document
echoes through that document, this idea belongs to a cluster you have not
yet named. But to a human eye, it is opaque — a black warehouse with a
search slot. You type in a question; an answer slides out; you have no way
to know what else lives in the dark, what was passed over, what almost
matched, what *should* have matched and didn't.

Bifröst exists so that you can walk the warehouse. So that you can see your
own thinking. So that the corpus stops being a slot machine and becomes a
sky you can stand under and trace.

---

## Core Ethos

**The corpus is a living thing.** Every chunk is a small organism with a
position in the embedding-space sky. Together they form constellations. The
job of this tool is to render those constellations *honestly*, *beautifully*,
and *quickly*, so the human architect can develop intuition that no query
language can give.

**Comprehension before retrieval.** A search box answers questions you already
know to ask. A 3D map suggests questions you didn't.

**Local-first, sovereign by default.** The corpus is yours. The compute is
yours. The visualization is yours. Nothing leaves the tailnet. No API key
required. No subscription. No telemetry. If your laptop has a GPU, it does
the work; if not, CPU is fine.

**Cyber-Viking aesthetic.** Not because it looks cool (though it does) but
because aesthetics communicate intent. Drama in the visuals tells the
visitor: *this is not a corporate dashboard, this is your forge.* Glowing
rainbow gradient on the title literally names the project — Bifröst is the
rainbow bridge. The runes on the system gauges are not decoration; they are
section markers in a tradition older than punctuation.

---

## Values

| Value | What it means in practice |
|---|---|
| **Comprehension** | Every visualization choice serves human understanding first, novelty second. |
| **Sovereignty** | Self-hosted, locally-computed, no cloud anything. |
| **Honesty** | No silent loaders. No fake "still working." No hidden filtering. Every error visible. |
| **Speed when it matters** | Page load is instant. Cached views are sub-second. Heavy work runs out of band. |
| **Dignity for all content** | The architect's corpus may include the strange, the personal, the rough — Bifröst displays it all with equal craft. No content-moderation hand-wringing. |
| **Tradition + technology** | Norse mythology and modern web GL are not at war. The bridge of Asgard rendered as a force-directed graph is appropriate, not ironic. |

---

## Synthesis Approach

Bifröst is **not** a research project trying to invent new visualization
techniques. It is a **practical artifact** that takes the best of what
already exists — UMAP for dimensionality reduction, HDBSCAN for topic
clustering, pgvector for vector storage, 3d-force-graph for WebGL rendering,
trafilatura for web extraction, FastAPI for plumbing — and weaves them into
one coherent surface.

The novelty is in the **composition**, not the components. Every dependency
is mature and well-understood. The user benefit is having all of them in one
local service with one keystroke.

The two genuinely new things in this orbit — **Skein** and **Skry** — are
deliberately separate repositories so their value is independent of
Bifröst's. You can use either without the viewer. The viewer just becomes
their theatre.

---

## Iron Laws (Things This Project Will Never Do)

These are not "should nots." They are "shall nots."

1. **Bifröst shall never mutate `documents` or `chunks`.** Those tables
   belong to the ingest project. Bifröst is a reader.

2. **Bifröst shall never block the page in silence.** Every long operation
   reports stage + progress. The bridge "opening" is *always* narrated.

3. **Bifröst shall never require an external paid service to display the
   corpus.** A working Ollama, Postgres, and browser are sufficient.

4. **Bifröst shall never censor or de-emphasize content.** Equal dignity for
   every node, regardless of subject matter.

5. **Bifröst shall never crash on a downstream failure.** It degrades
   honestly — if Ollama is down, HyDE turns off and search still works; if
   nvidia-smi is missing, the GPU gauge hides; if Skein hasn't been built,
   the ENTITIES layer shows an empty graph with a clear message.

6. **Bifröst shall never bury an error.** Every exception is logged with a
   traceback; every API failure returns a structured error; every build
   crash sets `stage=failed` with the error string visible in the loader.

7. **Bifröst shall never `print()`.** All output goes through the `logging`
   module. Stdout is reserved for systemd journals.

8. **Bifröst shall never hardcode infrastructure.** DB URL, Ollama URL,
   tokens, model names — all live in `.env`.

9. **Bifröst shall never block the FastAPI request thread on multi-second
   compute.** Heavy work runs out-of-process via `graph_builder.py`. The
   server stays responsive at all times.

---

## Ultimate Aim

That the corpus owner will, one day, look at the floating constellation of
their own thinking and feel something approaching *recognition*. Not just
"these are the chunks I ingested," but "ah — *that* is how I think; *that*
is what I've been circling; *that* is what's connected to what."

That kind of recognition is what justifies the existence of any tool. If
Bifröst delivers it even once, it has earned the disk space.

If it ever stops delivering it — if the panels become noise, the loaders
become heavy, the visualizations become decoration — Bifröst has drifted
from this vision. The correct response is to return here and re-read.

---

## What This Project Is Not

- **Not a search engine.** It contains search; search is not its purpose.
- **Not a knowledge graph.** It can *display* graphs (Skein's, primarily);
  it does not build them.
- **Not a CMS.** It does not own the corpus; the ingest pipeline does.
- **Not multi-tenant.** One owner, one corpus, one tailnet.
- **Not a SaaS.** No commercial intent. Run it yourself or don't.
- **Not a competitor to Obsidian Graph or Foam or Roam.** Different
  substrate, different audience. Those are markdown-graph tools; Bifröst is
  an embedding-graph tool over an arbitrary text corpus.

---

## Closing Note from the Skald

The bridge between worlds in the old stories was not a metaphor for
inconvenience. It was a place. You walked it. You arrived changed. The
bridge itself glowed.

This tool tries to be a bridge of that kind, however small. Between the
warehouse and the eye. Between the embedding and the meaning. Between
what you collected and what you understood.

That is the only point.
