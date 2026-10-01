"""Open the configured local viewer without printing its access token."""
from __future__ import annotations

import logging
import os
import subprocess
import sqlite3
import json
from contextlib import closing
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlencode

from dotenv import dotenv_values
import httpx


def viewer_base_url(config: dict) -> str:
    host = config.get("VIEWER_LOOPBACK_HOST", "127.0.0.1") or config.get("VIEWER_BIND_HOST", "127.0.0.1")
    if host in ("0.0.0.0", "::"):
        host = "127.0.0.1"
    if ":" in host:
        host = "[" + host + "]"
    scheme = "https" if config.get("VIEWER_TLS_CERT") else "http"
    return f"{scheme}://{host}:{config.get('VIEWER_PORT', '8731')}/"


def viewer_url(project: Path) -> str:
    config = {**dotenv_values(project / ".env"), **os.environ}
    token = config.get("VIEWER_TOKEN")
    state = Path(config.get("VIEWER_SECURITY_DIR") or str(Path(config.get("XDG_STATE_HOME") or str(Path.home() / ".local/state")) / "bifrost"))
    if (state / "access.sqlite3").is_file():
        with closing(sqlite3.connect(f"file:{state / 'access.sqlite3'}?mode=ro", uri=True)) as db:
            row = db.execute("SELECT value FROM meta WHERE name='launcher_token'").fetchone()
            if row:
                token = json.loads(row[0])
    if not token:
        raise RuntimeError("VIEWER_TOKEN is missing from the viewer configuration")
    return viewer_base_url(config) + "#" + urlencode({"token": token})


def main() -> None:
    project = Path(__file__).resolve().parents[1]
    subprocess.run(["systemctl", "--user", "start", "bifrost.service"], check=False, timeout=15)
    base = viewer_base_url({**dotenv_values(project / ".env"), **os.environ})
    # Give a cold service time to bind; graph readiness is handled by the page.
    for attempt in range(20):
        try:
            response = httpx.get(base, timeout=1)
            if response.status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(.5)
    webbrowser.open(viewer_url(project))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.getLogger("bifrost.launcher").error("Unable to open viewer: %s", exc)
