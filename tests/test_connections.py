"""Discovery and portable contracts cannot grant or expose owner authority."""
import json

import pytest
from fastapi.testclient import TestClient

import viewer
from security.connections import connection_url
from security.store import AccessError


@pytest.mark.parametrize("url", ["http://public.example", "https://user:pass@example.com", "https://example.com/x", "https://example.com#key", "https://example.com?token=x", "https://example.com:99999", "https://evil'$().ts.net", "https://example.com\\x", "ftp://example.com"])
def test_advertised_origin_validation(url):
    with pytest.raises(AccessError):
        connection_url(url)


@pytest.mark.parametrize("url", ["http://127.0.0.1:8731/", "http://100.67.240.22:8731", "http://gungnir.tailc7274f.ts.net:8731", "https://brain.example.org", "http://[::1]:8731"])
def test_valid_advertised_origins(url):
    assert connection_url(url) == url.rstrip("/")


def test_discovery_schema_and_profile_permissions():
    store = viewer.get_security()
    read = store.create_key("Reader", ["read"], 30, rpm=30)
    owner = {"Authorization": "Bearer " + store.owner_token()}
    delegated = {"Authorization": "Bearer " + read["token"]}
    client = TestClient(viewer.app, base_url="http://localhost")
    public = client.get("/.well-known/bifrost.json")
    assert public.status_code == 200 and public.json()["protocol_version"] == "1.0"
    assert not any(word in public.text for word in (read["token"], store.owner_token(), "owner@example", "documents"))
    assert client.get("/api/ai/openapi.json").status_code == 401
    assert client.get("/api/admin/connection", headers=delegated).status_code == 403
    assert client.post("/api/admin/connection", headers=delegated, json={"name": "x"}).status_code == 403
    result = client.post("/api/admin/connection", headers=owner, json={"name": "My brain", "base_url": "http://100.67.240.22:8731"})
    assert result.status_code == 200
    assert client.get("/.well-known/bifrost.json").json()["base_url"] == "http://100.67.240.22:8731"
    caps = client.get("/api/capabilities", headers=delegated).json()
    assert caps["principal"]["quotas"]["request_units_per_minute"] == 30
    assert caps["principal"]["scopes"] == ["read"] and caps["destructive_operations"] is False
    schema = client.get("/api/ai/openapi.json", headers=delegated).json()
    assert not any("admin" in path for path in schema["paths"])
    assert schema["security"] == [{"AgentBearer": []}]
    assert schema["components"]["schemas"]["ImportJob"]["properties"]["status"]["enum"] == ["queued", "running", "ok", "failed"]
    assert schema["paths"]["/api/search"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("SearchResults")
    assert schema["paths"]["/api/ingest/text"]["post"]["x-required-scope"] == "ingest"
    assert schema["paths"]["/api/ingest/text"]["post"]["parameters"][-1]["schema"]["maxLength"] == 128
    assert client.post("/api/admin/connection", headers=owner, json={"name": "My brain", "base_url": "https://u:p@example.com"}).status_code == 400
    assert client.get("/.well-known/bifrost.json").json()["base_url"] == "http://100.67.240.22:8731"


def test_discovery_budget_separate_and_cross_origin_retry_header(monkeypatch):
    monkeypatch.setenv("VIEWER_ALLOWED_ORIGINS", "https://authorized.example")
    store = viewer.get_security(); store.limits["discovery_requests_per_hour"] = 2
    delegated = store.create_key("Limited reader", ["read"], 30, rpm=1)
    monkeypatch.setattr(viewer.app, "middleware_stack", None)
    client = TestClient(viewer.app, base_url="http://localhost")
    assert client.get("/.well-known/bifrost.json").status_code == 200
    assert client.get("/.well-known/bifrost.json").status_code == 200
    assert client.get("/.well-known/bifrost.json").status_code == 429
    # Public recovery remains within its own quota.
    assert client.post("/api/auth/recovery/request", json={"email": "nobody@example.com"}).status_code == 202
    headers = {"Authorization": "Bearer " + delegated["token"], "Origin": "https://authorized.example"}
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    preflight = client.options("/api/ingest/text", headers={"Origin": "https://authorized.example", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Authorization,Content-Type,Idempotency-Key"})
    assert preflight.status_code == 204
    assert preflight.headers.get_list("Access-Control-Allow-Origin") == ["https://authorized.example"]
    assert "Idempotency-Key" in preflight.headers["Access-Control-Allow-Headers"]
    busy = client.get("/api/auth/me", headers=headers)
    assert busy.status_code == 429 and int(busy.headers["Retry-After"]) > 0
    assert busy.headers["Access-Control-Allow-Origin"] == "https://authorized.example"
    assert "Retry-After" in busy.headers["Access-Control-Expose-Headers"]
    assert busy.headers["X-Content-Type-Options"] == "nosniff"
    assert client.get("/api/auth/me", headers={**headers, "Origin": "https://untrusted.example"}).status_code == 403
