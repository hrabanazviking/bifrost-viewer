"use strict";
window.Brain = (() => {
  let token = "", generation = 0;
  const byId = id => document.getElementById(id);
  function setToken(value) { token = value.trim(); generation++; window.dispatchEvent(new Event("brain-auth")); }
  function takeFragment() {
    const incoming = new URLSearchParams(location.hash.slice(1)).get("token") || new URLSearchParams(location.search).get("token");
    if (incoming) token = incoming.trim();
    history.replaceState(null, "", location.pathname);
  }
  takeFragment();
  window.addEventListener("hashchange", () => { takeFragment(); generation++; window.dispatchEvent(new Event("brain-auth")); });
  function message(value, error = false) {
    const node = byId("message"); if (!node) return;
    node.textContent = value; node.classList.toggle("error", error);
  }
  async function api(path, {body, key, timeout = 30000, authenticated = true} = {}) {
    const current = generation, headers = {"Content-Type": "application/json"};
    if (authenticated) headers.Authorization = "Bearer " + token;
    if (key) headers["Idempotency-Key"] = key;
    let response;
    try { response = await fetch(path, {method: body === undefined ? "GET" : "POST", headers,
      body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(timeout), redirect: "error"}); }
    catch (error) { throw new Error("Connection interrupted. Your form is preserved; check activity before retrying an import."); }
    if (authenticated && current !== generation) throw new Error("Session changed; unlock again.");
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = typeof data.detail === "string" ? data.detail : Array.isArray(data.detail) ? data.detail.map(x => x.msg).join("; ") : "";
      const retry = response.headers.get("Retry-After");
      const error = new Error((data.error || detail || "Request failed (" + response.status + ")") + (retry ? ` Wait ${retry} seconds before trying again.` : ""));
      error.status = response.status; error.retry = Number(retry) || 0; throw error;
    }
    return data;
  }
  function navigate(path) { location.assign(path + (token ? "#token=" + encodeURIComponent(token) : "")); }
  function wireNavigation() {
    document.querySelectorAll("a[data-session]").forEach(node => node.onclick = event => { event.preventDefault(); navigate(node.getAttribute("href")); });
  }
  function bind(id, work) {
    const form = byId(id); if (!form) return;
    form.addEventListener("submit", async event => {
      event.preventDefault(); const button = form.querySelector("button[type=submit]") || form.querySelector("button");
      button.disabled = true;
      try { await work(form); } catch (error) { message(error.message, true); }
      finally { button.disabled = false; }
    });
  }
  function text(tag, value, className = "") { const node = document.createElement(tag); node.textContent = value; node.className = className; return node; }
  async function copy(value) {
    try { await navigator.clipboard.writeText(value); message("Copied to clipboard."); }
    catch { message("Clipboard unavailable here. Select the text and copy it manually.", true); }
  }
  wireNavigation();
  return {byId, api, message, setToken, hasToken: () => Boolean(token), navigate, bind, text, copy};
})();
