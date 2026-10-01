"""Standalone graph-build subprocess.

Runs in its own Python interpreter so its UMAP/HDBSCAN/numpy work cannot
GIL-block the FastAPI request handlers in the main viewer process.

Usage (called by viewer.py via subprocess.Popen):
    uv run graph_builder.py <fingerprint>

Writes two files under .cache/:
    graph_<fp>.json          — the actual graph payload (chunk + document levels)
    build_status_<fp>.json   — live status, polled by /api/graph/build-status
"""
from __future__ import annotations

import datetime
import logging
import os
import sys
import traceback
from pathlib import Path

import orjson

PROJECT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT))

# Import shared build logic from the viewer module
from viewer import build_graph, cache_path, CACHE_DIR  # noqa: E402
from runtime_support import atomic_json, publish_graph  # noqa: E402

# docs/bugs/0011: structured logging via `logging` module — never `print()`.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname).1s] graph_builder: %(message)s",
)
log = logging.getLogger("graph_builder")


def status_path(fp: str) -> Path:
    return CACHE_DIR / f"build_status_{fp}.json"


def write_status(fp: str, **fields) -> None:
    """Atomically write the status JSON so the polling endpoint never sees a
    half-written file."""
    existing: dict = {}
    p = status_path(fp)
    if p.exists():
        try:
            existing = orjson.loads(p.read_bytes())
        except Exception:
            existing = {}
    if not isinstance(existing, dict):
        existing = {}
    existing.update(fields)
    atomic_json(p, existing)


def main() -> int:
    if len(sys.argv) not in (2, 3):
        log.error("usage: graph_builder.py <fingerprint>")
        return 2
    fp = sys.argv[1]
    entity = len(sys.argv) == 3 and sys.argv[2] == "entity"
    source_fp = fp
    if entity:
        fp = "entity_" + fp

    # Be nice to the rest of the system — graph build is not interactive
    try:
        os.nice(5)
    except Exception:
        pass

    write_status(fp, running=True, stage="queued", progress=0.0,
                 started_at=datetime.datetime.now().isoformat(),
                 finished_at=None, error=None, pid=os.getpid())

    def progress(stage: str, frac: float) -> None:
        write_status(fp, stage=stage, progress=float(frac))

    try:
        target, g = _compute_graph(source_fp, entity, progress)
        publish_graph(target, g, "skein_graph_" if entity else "graph_")

        write_status(fp, running=False, stage="done", progress=1.0,
                     finished_at=datetime.datetime.now().isoformat(),
                     error=None)
        log.info("graph build complete · fp=%s · cache=%s", fp, target.name)
        return 0
    except Exception as e:
        tb = traceback.format_exc()
        write_status(fp, running=False, stage="failed", progress=0.0,
                     finished_at=datetime.datetime.now().isoformat(),
                     error=str(e))
        log.error("graph build FAILED · fp=%s\n%s", fp, tb)
        return 1
    finally:
        from viewer import close_pool
        close_pool()


def _compute_graph(source_fp: str, entity: bool, progress) -> tuple[Path, dict]:
    if entity:
        from viewer import _build_skein_graph, db_conn, _skein_fingerprint
        target = CACHE_DIR / f"skein_graph_{source_fp}.json"
        progress("projecting entities", 0.1)
        graph = _build_skein_graph(source_fp)
        with db_conn() as conn, conn.cursor() as cur:
            if (_skein_fingerprint(cur) or "noversion") != source_fp:
                raise RuntimeError("entity graph changed during layout; retry its new fingerprint")
    else:
        from viewer import fingerprint
        target = cache_path(source_fp)
        graph = build_graph(source_fp, progress=progress)
        if fingerprint() != source_fp:
            raise RuntimeError("corpus changed during build; will retry with its new fingerprint")
    return target, graph


if __name__ == "__main__":
    sys.exit(main())
