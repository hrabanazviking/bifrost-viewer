"use strict";
let profileLoaded = false, sessionVersion = 0;
let token = new URLSearchParams(location.hash.slice(1)).get("token") || "";
history.replaceState(null, "", location.pathname);
const el = id => document.getElementById(id);
function status(message, error = false) { el("status").textContent = message; el("status").classList.toggle("error", error); }
async function api(path, body, authenticated = true) {
  const version = sessionVersion;
  const headers = {"Content-Type": "application/json"};
  if (authenticated) headers.Authorization = "Bearer " + token;
  const result = await fetch(path, {method: body === undefined ? "GET" : "POST", headers,
    body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(20000)});
  const data = await result.json();
  if (version !== sessionVersion) throw new Error("Session changed. Open the local launcher or unlock again.");
  if (!result.ok) {
    const retry = result.headers.get("Retry-After");
    throw new Error((data.error || (typeof data.detail === "string" ? data.detail : "Check the form fields") || "Request failed") + (retry ? ` Wait ${retry} seconds before trying again.` : ""));
  }
  return data;
}
function bind(id, fn) {
  el(id).addEventListener("submit", async event => {
    event.preventDefault();
    const button = event.target.querySelector("button"); button.disabled = true;
    try { await fn(); } catch (error) { status(error.message, true); }
    finally { button.disabled = false; }
  });
}
function issue(value) { el("issued").value = value; el("issued-label").hidden = false; el("copy-issued").hidden = false; }
async function loadKeys() {
  const keys = await api("/api/admin/keys"); el("keys").replaceChildren();
  for (const key of keys) {
    const row = document.createElement("div"); row.className = "key";
    const label = document.createElement("span");
    label.textContent = `${key.name} · ${key.scopes.join(", ")} · ${key.revoked ? "revoked" : key.expires && key.expires * 1000 <= Date.now() ? "expired" : "active"} · ${key.expires ? "expires " + new Date(key.expires * 1000).toLocaleDateString() : "no expiry"}`;
    row.append(label);
    if (!key.revoked) {
      const button = document.createElement("button"); button.textContent = "Revoke";
      button.onclick = async () => { button.disabled = true; try { await api(`/api/admin/keys/${encodeURIComponent(key.id)}/revoke`, {}); await loadKeys(); status("Key revoked. Queued submissions from that key will fail safely."); } catch (error) { status(error.message, true); button.disabled = false; } };
      row.append(button);
    }
    el("keys").append(row);
  }
}
async function loadOwner() {
  const data = await api("/api/admin/settings"); el("owner").hidden = false;
  el("unlock-section").hidden = true; el("lock").hidden = false;
  el("owner-token").value = "";
  el("email").value = data.email; el("recovery-email").value = data.email;
  el("email-state").textContent = data.verified ? "Active verified recovery email: " + data.email : "Recovery email has not yet been verified. Configure mail, then send and confirm a verification code.";
  const mail = data.mail;
  for (const [field, setting] of Object.entries({rpm:"ai_requests_per_minute",writes:"ai_writes_per_minute",documents:"ai_documents_per_day",bytes:"ai_bytes_per_day"})) {
    el("key-" + field).max = data.limits[setting];
    el("key-" + field).value = data.limits[setting];
  }
  el("mail-host").value = mail.host || "smtp.gmail.com"; el("mail-port").value = mail.port || 587;
  el("mail-mode").value = mail.mode || "starttls"; el("mail-user").value = mail.username || data.email;
  el("mail-sender").value = mail.sender || data.email;
  el("mail-state").textContent = data.mail_configured ? "An SMTP password is saved. Send an email verification code to test delivery." : "No SMTP password is saved; automatic mail delivery needs setup.";
  el("setup-summary").textContent = data.mail_configured && data.verified ? "Recovery is ready. Create an individual AI key below, then give the assistant the connection guide." : "Finish your recovery setup: configure mail delivery, send a verification code, and confirm the code here. Existing access stays valid while you set this up.";
  el("mail-details").open = !data.mail_configured;
  if (!profileLoaded) {
    const profile = await api("/api/admin/connection");
    el("connection-name").value = profile.name; el("connection-url").value = profile.base_url; profileLoaded = true;
  }
  const outcomes = await Promise.allSettled([loadKeys(), loadJobs()]);
  status(outcomes.some(x => x.status === "rejected") ? "Owner settings unlocked; some activity could not be loaded. Refresh when the service is ready." : "Owner settings unlocked.");
}

async function loadJobs() {
  const health = await api("/api/admin/ingest/status");
  const queue = health.api_queue, inbox = health.local_inbox;
  el("ingest-health").textContent = `API supervisor: ${queue.supervisor_alive ? "running" : "stopped"} · retained jobs ${queue.retained_jobs}/${queue.retained_capacity} · inbox ${inbox.stage || "unknown"}${inbox.progress === undefined ? "" : " " + Math.round(inbox.progress * 100) + "%"}${inbox.failed === undefined ? "" : " · failed files " + inbox.failed}`;
  const jobs = await api("/api/ingest/jobs"); el("ingest-jobs").replaceChildren();
  for (const job of jobs) {
    const row = document.createElement("div"); row.className = "key";
    const label = document.createElement("span");
    label.textContent = `${job.title || job.url || job.job_id} · ${job.status} · ${job.stage} ${Math.round(job.progress * 100)}% · attempts ${job.attempts}${job.error_category ? " · " + job.error_category : ""}`;
    row.append(label);
    if (job.status === "failed") {
      const button = document.createElement("button"); button.textContent = "Retry original job";
      button.onclick = async () => {
        button.disabled = true;
        try { await api(`/api/admin/ingest/jobs/${encodeURIComponent(job.job_id)}/retry`, {}); await loadJobs(); status("Original job requeued. Its existing payload and deduplication identity are preserved."); }
        catch (error) { status(error.message, true); button.disabled = false; }
      };
      row.append(button);
    }
    el("ingest-jobs").append(row);
  }
}
bind("connection-profile", async () => {
  const data = await api("/api/admin/connection", {name: el("connection-name").value.trim(), base_url: el("connection-url").value.trim()});
  status(data.message);
});
el("copy-issued").onclick = async () => {
  try { await navigator.clipboard.writeText(el("issued").value); status("Key copied. Store it in secret settings and share the guide separately."); }
  catch { el("issued").focus(); el("issued").select(); status("Select and copy the key manually; clipboard access is unavailable here."); }
};
el("connections-link").onclick = event => { event.preventDefault(); location.assign("/connect" + (token ? "#token=" + encodeURIComponent(token) : "")); };
el("refresh-jobs").onclick = () => loadJobs().catch(error => status(error.message, true));
bind("unlock", async () => { sessionVersion++; token = el("owner-token").value.trim(); await loadOwner(); });
bind("mail", async () => {
  await api("/api/admin/mail", {host: el("mail-host").value.trim(), port: Number(el("mail-port").value), mode: el("mail-mode").value, username: el("mail-user").value.trim(), sender: el("mail-sender").value.trim(), password: el("mail-password").value});
  el("mail-password").value = ""; await loadOwner(); status("Mail settings saved. Send an email verification code to check delivery.");
});
bind("email-request", async () => { const data = await api("/api/admin/email/request", {email: el("email").value.trim()}); status(data.message); });
bind("email-confirm", async () => { await api("/api/admin/email/confirm", {code: el("email-code").value.trim()}); el("email-code").value = ""; await loadOwner(); status("Recovery email verified and activated."); });
bind("new-key", async () => {
  const data = await api("/api/admin/keys", {name: el("key-name").value.trim(), days: Number(el("key-days").value), scopes: el("key-scopes").value === "append" ? ["read", "ingest"] : ["read"], rpm: Number(el("key-rpm").value), writes: Number(el("key-writes").value), documents: Number(el("key-documents").value), bytes: Number(el("key-bytes").value)});
  issue(data.token); await loadKeys(); status("AI key created. Copy it now and give it only to the AI you authorize.");
});
bind("recover-request", async () => { const data = await api("/api/auth/recovery/request", {email: el("recovery-email").value.trim()}, false); status(data.message); });
bind("recover-confirm", async () => {
  const data = await api("/api/auth/recovery/confirm", {code: el("recovery-code").value.trim()}, false);
  token = data.token; el("recovery-code").value = ""; issue(token); await loadOwner(); status("Owner token replaced. Copy the new token; your local desktop launcher has also been updated automatically.");
});
el("back").onclick = event => { if (token) { event.preventDefault(); location.assign("/#token=" + encodeURIComponent(token)); } };
el("lock").onclick = () => {
  sessionVersion++; token = ""; profileLoaded = false; el("copy-issued").hidden = true; el("owner").hidden = true; el("unlock-section").hidden = false;
  el("lock").hidden = true; el("issued").value = ""; el("issued-label").hidden = true;
  el("keys").replaceChildren(); el("ingest-jobs").replaceChildren();
  for (const id of ["owner-token", "mail-password", "email-code", "recovery-code"]) el(id).value = "";
  status("Settings locked. Reopen with the local launcher or enter the owner token.");
};
window.addEventListener("hashchange", () => {
  const incoming = new URLSearchParams(location.hash.slice(1)).get("token");
  if (incoming) {
    sessionVersion++; token = incoming; profileLoaded = false; history.replaceState(null, "", location.pathname);
    loadOwner().catch(error => status(error.message, true));
  }
});
if (token) loadOwner().catch(error => status(error.message, true));
