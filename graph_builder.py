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
import os
import sys
import traceback
from pathlib import Path

import orjson

PROJECT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT))

# Import shared build logic from the viewer module
from viewer import build_graph, cache_path, CACHE_DIR  # noqa: E402


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
    existing.update(fields)
    tmp = p.with_suffix(".tmp")
    tmp.write_bytes(orjson.dumps(existing))
    tmp.replace(p)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: graph_builder.py <fingerprint>", file=sys.stderr)
        return 2
    fp = sys.argv[1]

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
        # Prune any stale graph caches with a different fingerprint
        target = cache_path(fp)
        for old in CACHE_DIR.glob("graph_v*.json"):
            if old != target:
                try:
                    old.unlink()
                except OSError:
                    pass

        g = build_graph(fp, progress=progress)
        target.write_bytes(orjson.dumps(g, option=orjson.OPT_SERIALIZE_NUMPY))

        write_status(fp, running=False, stage="done", progress=1.0,
                     finished_at=datetime.datetime.now().isoformat(),
                     error=None)
        print(f"graph build complete · fp={fp} · cache={target.name}")
        return 0
    except Exception as e:
        tb = traceback.format_exc()
        write_status(fp, running=False, stage="failed", progress=0.0,
                     finished_at=datetime.datetime.now().isoformat(),
                     error=str(e))
        print(f"graph build FAILED · fp={fp}\n{tb}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
