"""Portable public metadata; authenticated contracts retain the REST boundary."""
from __future__ import annotations

import ipaddress
import re
import json
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Request
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field

from security.store import AccessError

AGENT_PATHS = frozenset({"/api/auth/me", "/api/capabilities", "/api/health",
    "/api/search", "/api/chunk/{chunk_id}", "/api/ingest/text", "/api/ingest/url",
    "/api/ingest/jobs", "/api/ingest/jobs/{job_id}"})


def connection_url(value: str) -> str:
    """Validate advertised origins without fetching them or trusting proxy headers."""
    value = value.strip().rstrip("/")
    if not value:
        return ""
    try:
        url = urlsplit(value)
        port = url.port
        host = url.hostname or ""
    except ValueError:
        raise AccessError("Invalid connection URL", 400) from None
    if (url.scheme not in {"http", "https"} or not host or url.username or url.password
        or url.query or url.fragment or url.path or any(c.isspace() for c in value)
        or "\\" in value or not re.fullmatch(r"[A-Za-z0-9.:-]+", host) or (port is not None and not 1 <= port <= 65535)):
        raise AccessError("Use an HTTP(S) origin without credentials, path, query or fragment", 400)
    try:
        ip = ipaddress.ip_address(host)
        private_transport = ip.is_loopback or ip in ipaddress.ip_network("100.64.0.0/10") or ip in ipaddress.ip_network("fd7a:115c:a1e0::/48")
    except ValueError:
        private_transport = host == "localhost" or host.endswith(".ts.net")
    if url.scheme == "http" and not private_transport:
        raise AccessError("Use HTTPS, loopback HTTP or an encrypted tailnet origin", 400)
    return value


class ConnectionProfile(BaseModel):
    name: str = Field(default="Bifröst Second Brain", min_length=1, max_length=80,
                      pattern=r"^[^\x00-\x1f\x7f]+$")
    base_url: str = Field(default="", max_length=512)


def descriptor(store, request: Request) -> dict:
    profile = store.setting("connection_profile", {})
    return {"service": "bifrost", "protocol_version": "1.0", "name": profile.get("name", "Bifröst Second Brain"),
            "base_url": profile.get("base_url") or str(request.base_url).rstrip("/"),
            "authentication": "Bearer", "capabilities_url": "/api/capabilities",
            "openapi_url": "/api/ai/openapi.json", "instructions_url": "/AI_CONNECT.md",
            "connection_page": "/connect", "destructive_operations": False,
            "transports": ["REST", "MCP via client-side stdio adapter"]}


def principal_info(principal) -> dict:
    return {"id": principal.id, "scopes": sorted(principal.scopes), "quotas": {
        "request_units_per_minute": principal.rpm, "submissions_per_minute": principal.writes,
        "documents_per_utc_day": principal.documents, "bytes_per_utc_day": principal.bytes}}


def capabilities(store, request: Request) -> dict:
    return {**descriptor(store, request), "scopes": ["read", "ingest"],
            "principal": principal_info(request.state.principal),
            "append_routes": ["/api/ingest/text", "/api/ingest/url"],
            "idempotency": "Idempotency-Key", "limits": store.limits,
            "retry": {"statuses": [429, 502, 503, 504], "header": "Retry-After",
                      "same_key_and_payload_required": True},
            "job_terminal_states": ["ok", "failed"],
            "request_costs": {"search": store.limits["query_request_cost"],
                              "graph": store.limits["graph_request_cost"], "other": 1}}


def agent_schema(request: Request) -> dict:
    routes = [route for route in request.app.routes if isinstance(route, APIRoute) and route.path in AGENT_PATHS]
    schema = get_openapi(title="Bifröst authorized agent API", version="1.0", routes=routes)
    schema["servers"] = [{"url": str(request.base_url).rstrip("/")}]
    schema.setdefault("components", {})["securitySchemes"] = {
        "AgentBearer": {"type": "http", "scheme": "bearer", "description": "Individual expiring AI key; never use the owner token"}}
    schema["security"] = [{"AgentBearer": []}]
    enrich_contract(schema)
    for path, methods in schema["paths"].items():
        for operation in methods.values():
            if not isinstance(operation, dict):
                continue
            operation["x-required-scope"] = "ingest" if path in {"/api/ingest/text", "/api/ingest/url"} else "read"
            if operation["x-required-scope"] == "ingest":
                operation.setdefault("parameters", []).append({"name": "Idempotency-Key", "in": "header", "required": True,
                    "schema": {"type": "string", "minLength": 8, "maxLength": 128},
                    "description": "Unique operation ID; retain unchanged with the same payload on retries"})
    return schema



def enrich_contract(schema):
    models = json.loads(Path(__file__).with_name("agent_schemas.json").read_text())
    schema["components"].setdefault("schemas", {}).update(models)
    responses = {"/api/auth/me": "AgentIdentity", "/api/capabilities": "AgentCapabilities",
                 "/api/health": "AgentHealth", "/api/search": "SearchResults",
                 "/api/chunk/{chunk_id}": "Passage", "/api/ingest/jobs/{job_id}": "ImportJob",
                 "/api/ingest/jobs": "ImportJob", "/api/ingest/text": "ImportAccepted", "/api/ingest/url": "ImportAccepted"}
    for path, methods in schema["paths"].items():
        for operation in methods.values():
            model = {"$ref": "#/components/schemas/" + responses[path]}
            if path == "/api/ingest/jobs":
                model = {"type": "array", "maxItems": 100, "items": model}
            operation["responses"]["200"] = {"description": "Successful scoped operation", "content": {"application/json": {"schema": model}}}
            for parameter in operation.get("parameters", []):
                if parameter["name"] == "k":
                    parameter["schema"].update(minimum=1, maximum=100)
                elif parameter["name"] == "q":
                    parameter["schema"].update(minLength=1, maxLength=10000)
            for status in (401, 403, 409, 413, 429, 503):
                operation["responses"][str(status)] = {"description": "Access, validation, capacity or service failure; see AI_CONNECT.md",
                    "headers": {"Retry-After": {"description": "Minimum seconds before a retry, when supplied", "schema": {"type": "integer", "minimum": 1}}}}


def router(get_store, require_token, safely):
    api = APIRouter()

    @api.get("/.well-known/bifrost.json")
    @safely("connection_discovery")
    def discovery(request: Request):
        return descriptor(get_store(), request)

    @api.get("/api/ai/openapi.json")
    @safely("agent_schema")
    def schema(request: Request, _=Depends(require_token)):
        return agent_schema(request)

    @api.get("/api/admin/connection")
    @safely("connection_profile")
    def profile(_=Depends(require_token)):
        return get_store().setting("connection_profile", {"name": "Bifröst Second Brain", "base_url": ""})

    @api.post("/api/admin/connection")
    @safely("connection_save")
    def save(body: ConnectionProfile, _=Depends(require_token)):
        profile = {"name": body.name.strip(), "base_url": connection_url(body.base_url)}
        if not profile["name"]:
            raise AccessError("Choose a connection name", 400)
        get_store().set_setting("connection_profile", profile)
        return {"ok": True, **profile, "message": "Connection details saved. Listener, DNS, allowed Hosts and TLS are configured separately."}

    return api
