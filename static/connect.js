"use strict";
(() => {
  const B = Brain, el = B.byId; let base = location.origin;
  function download(name, value, type) {
    const url = URL.createObjectURL(new Blob([value], {type}));
    const a = document.createElement("a"); a.href = url; a.download = name; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function load() {
    try {
      const descriptor = await B.api("/.well-known/bifrost.json", {authenticated: false}); base = descriptor.base_url;
      el("base-url").value = base;
      const local = /\/\/(localhost|127\.|\[::1\])/.test(base);
      el("address-help").textContent = local ? "This is a local address. A remote AI needs an advertised tailnet or HTTPS address it can reach." : "Test this address from the AI’s machine. Reachability and access still depend on your configured network.";
      el("rest-example").textContent = `export BIFROST_BASE_URL='${base}'\n# Set BIFROST_TOKEN in your secret environment.\ncurl --fail-with-body --connect-timeout 5 --max-time 30 \\\n  -H "Authorization: Bearer $BIFROST_TOKEN" \\\n  "$BIFROST_BASE_URL/api/capabilities"`;
      el("mcp-example").textContent = JSON.stringify({mcpServers: {bifrost: {
        command: "uv", args: ["--directory", "/YOUR/PATH/bifrost-viewer/clients", "run", "--frozen", "--extra", "mcp", "python", "mcp_bridge.py"],
        env: {BIFROST_BASE_URL: base, BIFROST_TOKEN: "SET_THE_ASSIGNED_AI_KEY_PRIVATELY"}}}}, null, 2);
      B.message("Connection details ready. Download the guide and share the key through your AI’s secret settings.");
    } catch (error) { B.message(error.message, true); }
  }
  el("copy-url").onclick = () => B.copy(base);
  el("copy-rest").onclick = () => B.copy(el("rest-example").textContent);
  el("copy-mcp").onclick = () => B.copy(el("mcp-example").textContent);
  el("download-guide").onclick = async () => {
    try {
      const response = await fetch("/AI_CONNECT.md", {signal: AbortSignal.timeout(10000)});
      if (!response.ok) throw new Error("Guide unavailable; try again later.");
      download("BIFROST_AI_CONNECT.md", `# Connection handoff\n\nAssigned server: ${base}\n\nUse your individually assigned key from secret settings. This handoff contains no credential.\n\n` + await response.text(), "text/markdown");
      B.message("Downloaded the AI connection guide. Send the assigned key separately and privately.");
    } catch (error) { B.message(error.message, true); }
  };
  B.bind("test-connection", async () => {
    const key = el("ai-key").value.trim(); el("ai-key").value = "";
    if (key.startsWith("bfo_")) throw new Error("Use an individual AI key here. Owner access belongs in Settings.");
    const options = {headers: {Authorization: "Bearer " + key}, redirect: "error", signal: AbortSignal.timeout(30000)};
    const responses = await Promise.all([fetch("/api/auth/me", options), fetch("/api/health", options)]);
    const data = await Promise.all(responses.map(response => response.json()));
    if (!responses[0].ok || !responses[1].ok) throw new Error(data.find(x => x.error || x.detail)?.error || "Connection rejected. Check key expiry and permissions.");
    el("test-result").textContent = `Connected · ${data[0].scopes.join(" + ")} · ${data[0].quotas.request_units_per_minute} request units/minute · database ${data[1].db ? "ready" : "unavailable"} · embeddings ${data[1].ollama ? "ready" : "unavailable"}`;
    B.message("AI identity checked. Test the network address from the AI machine next.");
  });
  el("download-schema").onclick = async () => {
    try { download("bifrost-agent-openapi.json", JSON.stringify(await B.api("/api/ai/openapi.json"), null, 2), "application/json"); B.message("Downloaded the authenticated agent API description."); }
    catch (error) { B.message(error.message + " Open this page from an unlocked workspace to download the schema.", true); }
  };
  load();
})();
