"""Bounded child-output collection and process-group cancellation."""
from __future__ import annotations

from collections import deque
import os
import signal
import subprocess
import threading
import time
from pathlib import Path


class ChildFailure(RuntimeError):
    def __init__(self, code: int, detail: str = ""):
        self.code = code
        self.category = {20: "dependency", 21: "input", 22: "configuration", 124: "timeout"}.get(code, "unexpected")
        super().__init__(f"Ingest child exited {code}; category={self.category}" + (f"; {detail}" if detail else ""))


def terminate(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def drain(stream, tail: deque) -> None:
    try:
        while block := stream.read(1024):
            tail.append(block)
    except (OSError, ValueError):
        pass


def run_child(command: list[str], cwd: Path, timeout: float, stop: threading.Event, *, env: dict | None = None) -> None:
    if stop.is_set():
        raise InterruptedError("Inbox supervisor is stopping")
    process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, start_new_session=True, bufsize=0, env=env)
    tail: deque = deque(maxlen=64)
    reader = threading.Thread(target=drain, args=(process.stdout, tail), daemon=True)
    reader.start()
    deadline, code = time.monotonic() + timeout, 124
    try:
        while not stop.is_set() and time.monotonic() < deadline:
            try:
                code = process.wait(timeout=.2)
                break
            except subprocess.TimeoutExpired:
                continue
        if stop.is_set():
            raise InterruptedError("Inbox supervisor is stopping")
    finally:
        terminate(process)
        process.wait(timeout=5)
        reader.join(timeout=1)
        process.stdout.close()
    if code:
        lines = b"".join(tail).decode("utf-8", errors="replace").splitlines()
        diagnostics = [line.split("Ingestion failed ", 1)[1][:256] for line in lines if "Ingestion failed " in line]
        raise ChildFailure(code, diagnostics[-1] if diagnostics else "")
