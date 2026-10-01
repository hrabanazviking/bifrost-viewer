"""Durable inbox supervision for the optional sibling ingest CLI.

The supervisor invokes `ingest.py add`; it does not parse documents or
write database tables. Pending inputs and retry metadata survive restarts.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import time
import uuid
import tempfile
from pathlib import Path

from dotenv import load_dotenv

log = logging.getLogger("ingest.watcher")
PROJECT = Path(os.getenv("INGEST_PROJECT_DIR", str(Path(__file__).resolve().parents[2] / "ingest")))
load_dotenv(PROJECT / ".env")


def atomic_json(path: Path, payload: dict) -> None:
    """The supervisor only needs stdlib plus the ingest CLI's dotenv package."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, mode="w", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def read_urls(path: Path) -> list[str] | None:
    suffix = path.suffix.lower()
    if suffix not in (".url", ".urls", ".txt"):
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if suffix == ".url":
        lines = [line.split("=", 1)[1].strip() for line in lines if line.upper().startswith("URL=")]
    urls = [line for line in lines if line.startswith(("https://", "http://")) and not any(c.isspace() for c in line)]
    if suffix == ".txt" and (len(urls) != len(lines) or not urls):
        return None
    if suffix != ".txt" and len(urls) != len(lines):
        return []
    return list(dict.fromkeys(urls))


class InboxWorker:
    def __init__(self, project: Path) -> None:
        self.project = project
        self.inbox = project / "inbox"
        self.processed = self.inbox / "processed"
        self.failed = self.inbox / "failed"
        for folder in (self.inbox, self.processed, self.failed):
            folder.mkdir(parents=True, exist_ok=True)
        self.state_path = self.inbox / ".watch-state.json"
        try:
            self.state = json.loads(self.state_path.read_text())
            if not isinstance(self.state, dict):
                self.state = {}
        except (OSError, ValueError):
            self.state = {}
        self.settle = float(os.getenv("INGEST_WATCH_SETTLE_SECONDS", "3"))
        self.retry_base = float(os.getenv("INGEST_WATCH_RETRY_SECONDS", "30"))
        self.retry_max = float(os.getenv("INGEST_WATCH_RETRY_MAX_SECONDS", "3600"))

    def archive(self, path: Path, folder: Path) -> Path:
        destination = folder / path.name
        if destination.exists() and destination != path:
            destination = folder / f"{path.stem}_{uuid.uuid4().hex[:8]}{path.suffix}"
        if destination != path:
            shutil.move(str(path), str(destination))
        return destination

    def run_ingest(self, target: str) -> None:
        result = subprocess.run(
            [sys.executable, str(self.project / "ingest.py"), "add", target],
            cwd=self.project, capture_output=True, text=True,
            timeout=float(os.getenv("INGEST_WATCH_JOB_TIMEOUT", "900")),
        )
        if result.returncode:
            raise RuntimeError(f"ingest exited {result.returncode}: {result.stderr[-1500:]}")

    def process(self, path: Path) -> None:
        key = str(path.relative_to(self.inbox))
        stat = path.stat()
        signature = [stat.st_size, stat.st_mtime_ns]
        previous = self.state.get(key, {})
        record = previous if isinstance(previous, dict) and previous.get("signature") == signature else {}
        if not stat.st_size or time.time() - stat.st_mtime < self.settle:
            return
        if record.get("permanent") or time.time() < record.get("retry_at", 0):
            return
        try:
            urls = read_urls(path)
            if urls == []:
                record["permanent"] = True
                raise ValueError("URL container has no valid HTTP URLs")
            targets = urls if urls is not None else [str(path)]
            completed = record.setdefault("completed", [])
            for target in targets:
                if target in completed:
                    continue
                self.run_ingest(target)
                completed.append(target)
                self.state[key] = {**record, "signature": signature}
                atomic_json(self.state_path, self.state)
            self.archive(path, self.processed)
            self.state.pop(key, None)
            log.info("ingested %s", path.name)
        except Exception as exc:
            attempts = record.get("attempts", 0) + 1
            delay = min(self.retry_max, self.retry_base * 2 ** min(attempts - 1, 16))
            destination = self.archive(path, self.failed)
            self.state.pop(key, None)
            self.state[str(destination.relative_to(self.inbox))] = {
                **record, "signature": signature, "attempts": attempts,
                "retry_at": time.time() + delay, "error": str(exc),
            }
            log.warning("input %s failed; retained for retry in %.0fs: %s", path.name, delay, exc)
        atomic_json(self.state_path, self.state)

    def scan(self) -> None:
        for folder in (self.inbox, self.failed):
            for path in sorted(folder.iterdir()):
                if path.is_file() and not path.name.startswith("."):
                    try:
                        self.process(path)
                    except Exception as exc:
                        log.warning("input deferred: %s: %s", path.name, exc)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    worker = InboxWorker(PROJECT)
    stopping = False
    def stop(signum: int, frame: object) -> None:
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    log.info("watching inbox; retry state survives restarts")
    while not stopping:
        worker.scan()
        time.sleep(float(os.getenv("INGEST_WATCH_POLL_SECONDS", "5")))


if __name__ == "__main__":
    main()
