"""Run the repository's durable inbox supervisor with the ingest runtime."""
from pathlib import Path
import runpy


if __name__ == "__main__":
    supervisor = Path(__file__).resolve().parents[1] / "scripts" / "watch_inbox.py"
    runpy.run_path(str(supervisor), run_name="__main__")
