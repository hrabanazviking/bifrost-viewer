"""Verify SDK contracts and a real stdio subprocess against a disposable HTTP server."""
import asyncio
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mcp import Client, StdioServerParameters
from bifrost_client import BifrostClient
from mcp_bridge import build_server


def test_mcp_read_scope_and_append_opt_in():
    async def check():
        client = BifrostClient("http://localhost:8731", "synthetic-key", exchange=lambda *a: (200, {}, b'{"db":true}'))
        for append in (False, True):
            async with Client(build_server(client, append)) as session:
                tools = (await session.list_tools()).tools
                names = {tool.name for tool in tools}
                assert len(names) == (9 if append else 7)
                assert ("brain_add_note" in names) == append
                assert not any("delete" in name or "admin" in name or "sql" in name for name in names)
                for tool in tools:
                    assert tool.annotations.destructive_hint is False
                    if tool.name.startswith("brain_add_"):
                        assert "operation_id" in tool.input_schema["required"]
                response = await session.call_tool("brain_health", {})
                assert response.structured_content == {"db": True} and not response.is_error
                guide = await session.read_resource("bifrost://connection-guide")
                assert "Retry-After" in guide.contents[0].text
    asyncio.run(check())


def test_real_mcp_stdio_handshake_calls_protected_rest():
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_GET(self):
            requests.append((self.path, self.headers.get("Authorization")))
            self.send_response(200 if self.headers.get("Authorization") == "Bearer synthetic-key" else 401)
            self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps({"db": True, "ollama": True}).encode())
    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True); thread.start()
    async def check():
        parameters = StdioServerParameters(command=sys.executable,
            args=[str(Path(__file__).resolve().parents[1] / "mcp_bridge.py")],
            env={"BIFROST_BASE_URL": f"http://127.0.0.1:{http.server_port}", "BIFROST_TOKEN": "synthetic-key"})
        async with Client(parameters, read_timeout_seconds=20) as session:
            assert len((await session.list_tools()).tools) == 7
            result = await session.call_tool("brain_health", {})
            assert result.structured_content["db"] is True
    try: asyncio.run(check())
    finally: http.shutdown(); http.server_close(); thread.join()
    assert requests == [("/api/health", "Bearer synthetic-key")]
