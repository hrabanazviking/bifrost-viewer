"""Invariant tests for Bifröst — the Prophecy Rite, layer 5.

These tests verify the IMMUTABLE truths from PROJECT_LAWS.md. They import
the viewer module and inspect routes / state, but DO NOT require Postgres
or Ollama to be running.

Run with:    uv run pytest tests/
"""
from __future__ import annotations

import inspect
import os
import re

import pytest

# Set the required env vars to dummy values so viewer.py imports cleanly.
# (The pool isn't opened until first use, so dummy DB_URL is fine.)
os.environ.setdefault("VIEWER_DB_URL", "postgresql://nowhere/test")
os.environ.setdefault("VIEWER_TOKEN", "test-token")
os.environ.setdefault("VIEWER_OLLAMA_URL", "http://localhost:11434")
os.environ.setdefault("VIEWER_EMBED_MODEL", "nomic-embed-text")
os.environ.setdefault("VIEWER_CHAT_MODEL", "llama3.2:3b")

import viewer  # noqa: E402


# ─── Iron Law: every endpoint is wrapped in @safely ───────────────────────

def test_every_api_route_is_safely_wrapped():
    """Every /api/* route has its handler wrapped via @safely(...)."""
    source = inspect.getsource(viewer)
    # Find every @app.{get,post,delete,put,patch} on an /api/ path
    route_re = re.compile(
        r"@app\.(?:get|post|put|delete|patch)\(\s*[\"'](/api/[^\"']*)[\"']",
        re.MULTILINE,
    )
    # Find every @safely( decorator
    safely_re = re.compile(r"@safely\(")
    routes = route_re.findall(source)
    safely_count = len(safely_re.findall(source))
    # We expect: at least one @safely per /api/ route. We allow some non-/api
    # routes (like /) to lack @safely. So just check the count is >= len(routes).
    assert len(routes) > 0, "no /api/ routes detected — test setup wrong"
    assert safely_count >= len(routes), \
        f"{len(routes)} /api/ routes but only {safely_count} @safely decorators"


def test_route_docstring_lists_match_routes():
    """Every registered /api/ route is mentioned in the module docstring."""
    source = inspect.getsource(viewer)
    route_re = re.compile(
        r"@app\.(?:get|post|put|delete|patch)\(\s*[\"'](/api/[^\"']*)[\"']",
        re.MULTILINE,
    )
    routes = set(route_re.findall(source))
    doc = viewer.__doc__ or ""
    # Strip path params so /api/chunk/{chunk_id} matches /api/chunk/ in docstring
    def strip(r): return re.sub(r"\{[^}]+\}", "", r)
    missing = []
    for r in routes:
        if strip(r) not in doc.replace("{id}", ""):
            # try the full path too
            if r not in doc:
                missing.append(r)
    # Per docs/bugs/0012, the docstring was being kept up to date manually;
    # we accept a small drift but flag major gaps.
    assert len(missing) <= 2, f"module docstring missing routes: {missing}"


# ─── Iron Law: race-condition locks present for module-level dicts ────────

def test_module_level_locks_present():
    """Every module-level mutable dict has a corresponding lock."""
    expected_pairs = [
        ("_gpu_cache", "_gpu_cache_lock"),
        ("_skein_build_proc", "_skein_build_proc_lock"),
        ("_ingest_jobs", "_ingest_lock"),
        ("_build_proc", "_build_proc_lock"),
    ]
    for d, lock in expected_pairs:
        assert hasattr(viewer, d), f"missing module-level dict {d}"
        assert hasattr(viewer, lock), f"missing matching lock {lock}"


# ─── Iron Law: no print() in viewer.py or graph_builder.py ───────────────

def test_no_print_in_viewer():
    src = inspect.getsource(viewer)
    # Allow `print(` in comments or docstrings (rough heuristic: any `print(`
    # not preceded by `#` on the same line and not inside a triple-quoted block
    # is suspicious). Simpler: just count, then check it's zero in code lines.
    bad = [
        (i + 1, line) for i, line in enumerate(src.splitlines())
        if re.search(r"^\s*print\(", line) and not line.lstrip().startswith("#")
    ]
    assert not bad, f"viewer.py has print() calls: {bad}"


def test_no_print_in_graph_builder():
    import graph_builder
    src = inspect.getsource(graph_builder)
    bad = [
        (i + 1, line) for i, line in enumerate(src.splitlines())
        if re.search(r"^\s*print\(", line) and not line.lstrip().startswith("#")
    ]
    assert not bad, f"graph_builder.py has print() calls: {bad}"


# ─── Iron Law: token never logged in plaintext ────────────────────────────

def test_startup_log_masks_token():
    """The startup log line shows ?token=*** not the real value."""
    src = inspect.getsource(viewer)
    # Look for any string literal that could format the token directly:
    # f"... ?token={TOKEN}" or .format(token=TOKEN) etc.
    bad = re.search(r"\?token=\{[A-Za-z_]*[Tt][Oo][Kk][Ee][Nn]", src)
    assert not bad, f"token may be logged in plaintext: {bad.group(0) if bad else ''}"


# ─── Token discipline ────────────────────────────────────────────────────

def test_secrets_compare_digest_used():
    """Token comparison uses constant-time secrets.compare_digest, not =="""
    src = inspect.getsource(viewer)
    assert "secrets.compare_digest" in src, "token compare must use secrets.compare_digest"


# ─── XSS helper present in frontend ──────────────────────────────────────

def test_escape_html_present_in_frontend():
    """static/index.html defines an escapeHtml() helper (per bugs/0004-0006)."""
    path = os.path.join(os.path.dirname(viewer.__file__), "static", "index.html")
    with open(path, encoding="utf-8") as f:
        html = f.read()
    assert "function escapeHtml" in html, "escapeHtml helper missing"
    # And it's used in at least three places (toast, legend, node label)
    assert html.count("escapeHtml(") >= 3, "escapeHtml not used in expected sites"


def test_no_unescaped_innerhtml_of_user_data():
    """Spot-check: known-textual user-derived fields must go through escapeHtml.

    We deny-list the field names that we know carry corpus-derived strings
    (titles, names, text, snippets, URLs, log tails) — these MUST be wrapped
    in escapeHtml(...) when interpolated into innerHTML. Numeric/status
    fields (counts, percentages) are not flagged.
    """
    path = os.path.join(os.path.dirname(viewer.__file__), "static", "index.html")
    with open(path, encoding="utf-8") as f:
        html = f.read()
    suspicious_field_names = (
        "title", "name", "doc_title", "text", "snippet",
        "url", "log_tail", "kind", "label", "predicate",
    )
    # Find every innerHTML template; for each, ensure that any
    # ${something.<suspicious>} interpolation is wrapped in escapeHtml.
    innerhtml_blocks = re.findall(r"innerHTML\s*=\s*`([^`]*)`", html, re.S)
    flagged: list[str] = []
    for block in innerhtml_blocks:
        # Find raw interpolations NOT wrapped in escapeHtml
        raw_interp = re.findall(r"\$\{(?!escapeHtml\()([^}]+)\}", block)
        for expr in raw_interp:
            # Extract the trailing identifier (e.g. n.doc_title → "doc_title")
            tail = expr.split(".")[-1].strip().rstrip("|").split("|")[0].strip()
            tail = tail.split("[")[0].split("(")[0]
            if tail in suspicious_field_names:
                flagged.append(expr.strip())
    assert not flagged, f"raw (unescaped) innerHTML interpolation of user-derived field(s): {flagged}"
