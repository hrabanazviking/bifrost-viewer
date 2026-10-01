"""Durable inbox supervision for the optional sibling ingest CLI.

The supervisor invokes `ingest.py add`; it does not parse documents or
write database tables. Pending inputs and retry metadata survive restarts.
"""
from __future__ import annotations

import json
import logging
import math
import os
import shutil
import signal
import sys
import time
import uuid
import threading
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from inbox_child import ChildFailure, run_child  # noqa: E402
from inbox_state import atomic_json, exclusive_lock, load_state, save_state  # noqa: E402

log = logging.getLogger("ingest.watcher")
PROJECT = Path(os.getenv("INGEST_PROJECT_DIR", str(Path(__file__).resolve().parents[1] / "ingest"))).expanduser().resolve()
load_dotenv(Path(os.getenv("INGEST_ENV_FILE", str(PROJECT / ".env"))))


DEFAULTS = json.loads(SCRIPT_DIR.joinpath("inbox.defaults.json").read_text())


def watch_setting(name: str) -> float:
    value = float(os.getenv("INGEST_WATCH_" + name.upper(), str(DEFAULTS[name])))
    minimum = 0 if name == "settle_seconds" else .01
    if not math.isfinite(value) or value < minimum:
        raise ValueError("Invalid watcher setting: " + name)
    return value


def read_urls(path: Path) -> list[str] | None:
    suffix = path.suffix.lower()
    if suffix not in (".url", ".urls", ".txt"):
        return None
    text = path.read_text(encoding="utf-8")
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
    def __init__(self, project: Path, state_dir: Path | None = None) -> None:
        self.project = project
        self.state_dir = state_dir if state_dir is not None else project
        self.inbox = self.state_dir / "inbox"
        self.processed = self.inbox / "processed"
        self.failed = self.inbox / "failed"
        for folder in (self.inbox, self.processed, self.failed):
            folder.mkdir(parents=True, exist_ok=True)
        self.state_path = self.inbox / ".watch-state.json"
        self.health_path = self.inbox / ".watch-health.json"
        self.state = load_state(self.state_path)
        self.stop_event = threading.Event()
        self.health = {}
        try:
            data = json.loads(self.health_path.read_text())
            if not isinstance(data, dict):
                raise ValueError("Health metadata must be an object")
            retry_at = data.get("dependency_retry_at", 0)
            if isinstance(retry_at, (int, float)) and math.isfinite(retry_at):
                self.health["dependency_retry_at"] = min(retry_at, time.time() + watch_setting("retry_max_seconds"))
        except (OSError, ValueError):
            pass
        self.settle = watch_setting("settle_seconds")
        self.retry_base = watch_setting("retry_seconds")
        self.retry_max = watch_setting("retry_max_seconds")

    def archive(self, path: Path, folder: Path) -> Path:
        destination = folder / path.name
        if destination.exists() and destination != path:
            destination = folder / f"{path.stem}_{uuid.uuid4().hex[:8]}{path.suffix}"
        if destination != path:
            shutil.move(str(path), str(destination))
        return destination

    def run_ingest(self, target: str) -> None:
        self._publish_health("running")
        env = {**os.environ, "INGEST_PROGRESS_FILE": str(self.inbox / ".watch-job-progress.json")}
        run_child([sys.executable, str(self.project / "ingest.py"), "add", target],
                  self.project, watch_setting("job_timeout"), self.stop_event, env=env)

    def _previous_record(self, key: str, signature: list[int]) -> dict:
        previous = self.state.get(key, {})
        if previous.get("signature") in (signature, signature[-2:]):
            return previous
        return next((value for value in self.state.values() if value.get("signature") == signature), {})

    def _retain_failure(self, path: Path, key: str, signature: list[int], record: dict, exc: Exception) -> None:
        attempts = record.get("attempts", 0) + 1
        delay = min(self.retry_max, self.retry_base * 2 ** min(attempts - 1, 16))
        code = getattr(exc, "code", 21 if isinstance(exc, (UnicodeError, ValueError)) else 20)
        category = getattr(exc, "category", "input" if code == 21 else "dependency")
        destination = self.archive(path, self.failed)
        self.state.pop(key, None)
        stat = destination.stat()
        self.state[str(destination.relative_to(self.inbox))] = {
            **record, "signature": [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns],
            "attempts": attempts, "retry_at": time.time() + delay, "error": str(exc),
            "last_exit": code, "error_category": category, "permanent": code == 21,
        }
        if code in (20, 22, 124):
            self.health.update(dependency_retry_at=time.time() + delay, last_error_category=category)
        log.warning("input %s retained category=%s retry_in=%.0fs: %s", path.name, category, delay, exc)

    def process(self, path: Path) -> None:
        key = str(path.relative_to(self.inbox))
        stat = path.stat()
        signature = [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns]
        record = self._previous_record(key, signature)
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
                save_state(self.state_path, self.state)
            fresh = path.stat()
            if signature != [fresh.st_dev, fresh.st_ino, fresh.st_size, fresh.st_mtime_ns]:
                raise ChildFailure(20, "Input changed; retain and retry a stable version")
            self.archive(path, self.processed)
            self.state.pop(key, None)
            log.info("ingested %s", path.name)
        except InterruptedError:
            self.state[key] = {**record, "signature": signature}
            log.info("shutdown retained pending input %s", path.name)
        except Exception as exc:
            self._retain_failure(path, key, signature, record, exc)
        save_state(self.state_path, self.state)

    def _publish_health(self, stage: str) -> None:
        self.health.update(stage=stage, last_scan_at=time.time(),
                           pending=sum(p.is_file() and not p.name.startswith(".") for p in self.inbox.iterdir()),
                           failed=sum(p.is_file() for p in self.failed.iterdir()),
                           blocked=sum(bool(r.get("permanent")) for r in self.state.values()))
        atomic_json(self.health_path, self.health)

    def scan(self) -> None:
        if time.time() < self.health.get("dependency_retry_at", 0):
            self._publish_health("dependency-backoff")
            return
        for folder in (self.inbox, self.failed):
            for path in sorted(folder.iterdir()):
                if self.stop_event.is_set():
                    self._publish_health("stopping")
                    return
                if path.is_file() and not path.name.startswith("."):
                    try:
                        self.process(path)
                    except Exception as exc:
                        log.warning("input deferred: %s: %s", path.name, exc)
                    if time.time() < self.health.get("dependency_retry_at", 0):
                        self._publish_health("dependency-backoff")
                        return
        self._publish_health("idle")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    worker = InboxWorker(PROJECT, state_dir=Path(os.getenv("INGEST_STATE_DIR", str(PROJECT))).expanduser().resolve())
    def stop(signum: int, frame: object) -> None:
        worker.stop_event.set()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    log.info("watching inbox; retry state survives restarts")
    with exclusive_lock(worker.inbox / ".watcher.lock"):
        while not worker.stop_event.is_set():
            try:
                worker.scan()
            except Exception as exc:
                log.warning("Inbox scan deferred kind=%s", type(exc).__name__)
            worker.stop_event.wait(watch_setting("poll_seconds"))


if __name__ == "__main__":
    main()
