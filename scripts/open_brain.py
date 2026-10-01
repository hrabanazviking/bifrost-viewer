"""Open the configured local viewer without printing its access token."""
from __future__ import annotations

import logging
import os
import subprocess
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlencode

from dotenv import dotenv_values
import httpx


def viewer_url(project: Path) -> str:
    config = {**dotenv_values(project / ".env"), **os.environ}
    host = config.get("VIEWER_LOOPBACK_HOST", "127.0.0.1") or config.get("VIEWER_BIND_HOST", "127.0.0.1")
    if host in ("0.0.0.0", "::"):
        host = "127.0.0.1"
    if ":" in host:
        host = "[" + host + "]"
    token = config.get("VIEWER_TOKEN")
    if not token:
        raise RuntimeError("VIEWER_TOKEN is missing from the viewer configuration")
    return f"http://{host}:{config.get('VIEWER_PORT', '8731')}/#" + urlencode({"token": token})


def main() -> None:
    project = Path(__file__).resolve().parents[1]
    subprocess.run(["systemctl", "--user", "start", "bifrost.service"], check=False, timeout=15)
    url = viewer_url(project)
    # Give a cold service time to bind; graph readiness is handled by the page.
    for attempt in range(20):
        try:
            response = httpx.get(url.split("#", 1)[0], timeout=1)
            if response.status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(.5)
    webbrowser.open(url)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.getLogger("bifrost.launcher").error("Unable to open viewer: %s", exc)
