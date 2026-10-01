"""A minimal read-only filesystem and isolated processes for untrusted parsing."""
from __future__ import annotations

import shutil
from pathlib import Path

from security.store import AccessError


def available() -> str:
    program = shutil.which("bwrap")
    if not program:
        raise AccessError("API ingestion requires Bubblewrap process isolation", 503)
    return program


def command(project: Path, env_file: Path, payload: Path | None, limits_file: Path, tmp_bytes: int) -> list[str]:
    python = project / ".venv/bin/python"
    cfg = project / ".venv/pyvenv.cfg"
    values = dict(line.split(" = ", 1) for line in cfg.read_text().splitlines() if " = " in line) if cfg.exists() else {}
    runtime = Path(values["home"]).parent if values.get("home") else python.resolve().parents[1]
    args = [available(), "--unshare-all", "--share-net", "--unshare-user", "--disable-userns",
            "--die-with-parent", "--new-session", "--cap-drop", "ALL"]
    # Mount individual application files; never mount the project .env or home.
    paths = [Path("/usr"), Path("/lib"), Path("/lib64"), runtime, project / ".venv",
             project / "ingest.py", project / "safe_fetch.py"]
    paths += [Path(value) for value in ["/etc/resolv.conf", "/etc/hosts", "/etc/nsswitch.conf",
              "/etc/passwd", "/etc/group", "/etc/localtime", "/etc/ld.so.cache", "/etc/ssl/certs"]]
    for path in dict.fromkeys(paths):
        if path.exists():
            args += ["--ro-bind", str(path), str(path)]
    args += ["--ro-bind", str(env_file), "/worker.env", "--ro-bind", str(limits_file), "/limits.json",
             "--proc", "/proc", "--dev", "/dev", "--size", str(tmp_bytes), "--tmpfs", "/tmp",
             "--dir", "/tmp/home", "--symlink", "usr/bin", "/bin", "--chdir", str(project)]
    if payload:
        args += ["--ro-bind", str(payload), "/payload.txt"]
    return args


def environment(job: dict, title: str) -> dict:
    return {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": "/tmp/home",
            "XDG_CACHE_HOME": "/tmp/home/.cache", "INGEST_ENV_FILE": "/worker.env",
            "VIEWER_LIMITS_FILE": "/limits.json", "INGEST_API_JOB_ID": job["id"],
            "INGEST_API_CLIENT_ID": job["principal"], "INGEST_SUBMISSION_TITLE": title,
            "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}
