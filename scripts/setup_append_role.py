"""Provision an API-only PostgreSQL writer with SELECT/INSERT, never UPDATE/DELETE."""
from __future__ import annotations

import logging
import os
import secrets
import sys
from pathlib import Path
from urllib.parse import quote

import psycopg
from dotenv import dotenv_values
from psycopg import sql

ROLE = "bifrost_api_ingest"
MARKER = "Bifrost bounded append worker"


def provision(project: Path, state: Path):
    cfg = {**dotenv_values(project / ".env"), **os.environ}
    ingest = dotenv_values(Path(cfg.get("INGEST_ENV_FILE", str(project / "ingest/.env"))))
    password = secrets.token_urlsafe(48)
    with psycopg.connect(cfg["VIEWER_DB_URL"]) as conn, conn.cursor() as cur:
        cur.execute("SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,shobj_description(oid,'pg_authid') FROM pg_roles WHERE rolname=%s", (ROLE,))
        row = cur.fetchone()
        if row and (any(row[:4]) or row[4] != MARKER):
            raise RuntimeError("Existing API role is not owned by this setup; refusing to alter it")
        action = "ALTER" if row else "CREATE"
        cur.execute(sql.SQL(action + " ROLE {} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION CONNECTION LIMIT 4 PASSWORD {}").format(sql.Identifier(ROLE), sql.Literal(password)))
        cur.execute(sql.SQL("COMMENT ON ROLE {} IS {}").format(sql.Identifier(ROLE), sql.Literal(MARKER)))
        cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(ROLE)))
        for table in ["documents", "chunks"]:
            cur.execute(sql.SQL("GRANT SELECT, INSERT ON TABLE {} TO {}").format(sql.Identifier(table), sql.Identifier(ROLE)))
            cur.execute("SELECT has_table_privilege(%s,%s,'UPDATE,DELETE,TRUNCATE,TRIGGER')", (ROLE, table))
            if cur.fetchone()[0]:
                raise RuntimeError("API role inherits destructive privileges; setup rolled back")
        cur.execute(sql.SQL("GRANT USAGE, SELECT ON SEQUENCE documents_id_seq,chunks_id_seq TO {}").format(sql.Identifier(ROLE)))
        for setting, value in [("statement_timeout", "15s"), ("lock_timeout", "5s"), ("idle_in_transaction_session_timeout", "60s")]:
            cur.execute(sql.SQL("ALTER ROLE {} SET {} TO {}").format(sql.Identifier(ROLE), sql.Identifier(setting), sql.Literal(value)))
        cur.execute("SELECT has_schema_privilege(%s,'public','CREATE')", (ROLE,))
        if cur.fetchone()[0]:
            raise RuntimeError("PUBLIC grants schema CREATE; remove that grant before enabling remote ingest")
        database, port = conn.info.dbname, conn.info.port
        # Password auth through TCP; local peer auth cannot identify the restricted role.
        host = cfg.get("VIEWER_API_DB_HOST", "127.0.0.1")
        url = f"postgresql://{ROLE}:{quote(password, safe='')}@{host}:{port}/{quote(database, safe='')}"
        state.mkdir(parents=True, exist_ok=True, mode=0o700)
        state.chmod(0o700)
        path = Path(cfg.get("VIEWER_API_INGEST_ENV_FILE", str(state / "ingest.env")))
        values = {"INGEST_DB_URL": url, "OLLAMA_URL": ingest.get("OLLAMA_URL") or cfg["VIEWER_OLLAMA_URL"],
                  "INGEST_EMBED_MODEL": ingest.get("INGEST_EMBED_MODEL") or cfg["VIEWER_EMBED_MODEL"]}
        temp = path.with_suffix(".tmp")
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write("\n".join(f"{key}='{value}'" for key, value in values.items()) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(path)
    logging.getLogger("bifrost.setup").info("Append-only API role and private worker configuration installed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    project = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project))
    from dotenv import load_dotenv
    load_dotenv(project / ".env")
    state = Path(os.getenv("VIEWER_SECURITY_DIR", str(Path(os.getenv("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "bifrost")))
    provision(project, state)
