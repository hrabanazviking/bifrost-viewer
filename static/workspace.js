"use strict";
(() => {
  const B = Brain, el = B.byId; let timer, refreshing = false, authEpoch = 0, nextPollAt = 0;
  const submissions = new Map(), completed = new Set();
  let loadedJobs = false;
  async function open() {
    const epoch = ++authEpoch; clearTimeout(timer);
    el("workspace").hidden = true; el("unlock-panel").hidden = false;
    if (!B.hasToken()) return;
    try {
      const identity = await B.api("/api/auth/me");
      if (epoch !== authEpoch) return;
      el("workspace").hidden = false; el("unlock-panel").hidden = true; el("lock").hidden = false;
      el("access-token").value = ""; const append = identity.scopes.includes("ingest");
      el("append-controls").hidden = !append;
      el("append-hint").textContent = append ? "Imports run in the background. Follow their progress below." : "This key can read your knowledge. Ask the owner for append access to add something new.";
      B.message(identity.scopes.includes("admin") ? "Welcome back. Your knowledge is ready to explore." : "Connected with " + identity.scopes.join(" + ") + " access.");
      await Promise.allSettled([loadSummary(), loadJobs()]); schedule();
    } catch (error) { B.message(error.message, true); }
  }
  async function loadSummary() {
    const epoch = authEpoch;
    const outcomes = await Promise.allSettled([B.api("/api/overview"), B.api("/api/health")]);
    if (epoch !== authEpoch) return;
    if (outcomes[0].status === "fulfilled") {
      el("document-count").textContent = outcomes[0].value.documents.toLocaleString();
      el("chunk-count").textContent = outcomes[0].value.chunks.toLocaleString();
    } else { el("document-count").textContent = "Unavailable"; el("chunk-count").textContent = "Unavailable"; }
    const h = outcomes[1];
    el("health-state").textContent = h.status === "rejected" ? "Unavailable" : h.value.db && h.value.ollama ? "Ready" : h.value.db ? "Keyword mode" : "Needs attention";
  }
  async function loadJobs() {
    if (refreshing || !B.hasToken() || Date.now() < nextPollAt) return;
    refreshing = true;
    try {
      const jobs = await B.api("/api/ingest/jobs"); el("jobs").replaceChildren();
      const newlyCompleted = jobs.some(job => job.status === "ok" && !completed.has(job.job_id));
      jobs.filter(job => job.status === "ok").forEach(job => completed.add(job.job_id));
      if (loadedJobs && newlyCompleted) await loadSummary(); loadedJobs = true;
      if (!jobs.length) el("jobs").append(B.text("div", "No imports yet. Add a note or save a public page to get started.", "empty"));
      for (const job of jobs.slice(0, 12)) renderJob(job);
      el("activity-hint").textContent = jobs.length > 12 ? `${jobs.length} retained imports. Showing the latest 12; the owner can inspect all in Settings.` : "Recent imports · refreshes every 15 seconds while this page is visible.";
    } catch (error) { el("activity-hint").textContent = error.message; nextPollAt = Date.now() + Math.max(15, error.retry || 0) * 1000; }
    finally { refreshing = false; }
  }
  function renderJob(job) {
    const row = B.text("div", "", "job"), head = B.text("div", "", "job-head");
    head.append(B.text("strong", job.title || (job.url ? "Web page" : "Saved note")), B.text("span", job.status === "ok" ? "Preserved" : job.status === "failed" ? "Needs attention" : job.status === "running" ? "Working" : "Queued", "badge " + job.status));
    row.append(head, B.text("small", job.url || "Job " + job.job_id));
    const progress = document.createElement("progress"); progress.max = 1; progress.value = job.progress || 0; progress.setAttribute("aria-label", "Import progress");
    row.append(progress, B.text("small", `${(job.stage || job.status).replaceAll("_", " ")} · ${Math.round((job.progress || 0) * 100)}%`));
    if (job.error_category) row.append(B.text("small", "Issue: " + job.error_category.replaceAll("_", " ") + ". The original submission is retained."));
    if (job.status === "queued" && job.attempts > 0 && job.next_attempt_at) row.append(B.text("small", "A bounded retry is scheduled after " + new Date(job.next_attempt_at * 1000).toLocaleTimeString() + "."));
    el("jobs").append(row);
  }
  function schedule() {
    clearTimeout(timer); if (!B.hasToken() || document.hidden) return;
    timer = setTimeout(async () => { await loadJobs(); schedule(); }, Math.max(15000, nextPollAt - Date.now()));
  }
  async function submit(kind, body, form) {
    const signature = JSON.stringify(body), old = submissions.get(kind);
    const key = old && old.signature === signature ? old.key : "human-" + crypto.randomUUID();
    submissions.set(kind, {signature, key});
    const data = await B.api("/api/ingest/" + kind, {body, key});
    submissions.delete(kind); form.reset();
    B.message((data.duplicate ? "Recovered your existing import" : "Import accepted") + ". Job " + data.job_id + " will appear in activity.");
    await loadJobs(); schedule();
  }
  B.bind("unlock", async () => { B.setToken(el("access-token").value); });
  B.bind("note-form", form => submit("text", {title: el("note-title").value.trim(), text: el("note-text").value}, form));
  B.bind("url-form", form => submit("url", {url: el("page-url").value.trim()}, form));
  B.bind("search", async () => {
    const epoch = authEpoch;
    el("search-status").textContent = "Searching your knowledge…";
    try {
      const result = await B.api("/api/search?q=" + encodeURIComponent(el("query").value.trim()) + "&k=6&hyde=0");
      const snippets = await Promise.allSettled(result.hits.map(hit => B.api("/api/chunk/" + hit.id)));
      if (epoch !== authEpoch) return;
      el("results").replaceChildren();
      snippets.forEach((outcome, i) => renderResult(outcome, result.hits[i]));
      if (!result.hits.length) el("results").append(B.text("div", "No matching passages yet. Try a shorter phrase or different keywords.", "empty"));
      el("search-status").textContent = `${result.hits.length} passages found · ${result.degraded ? "keyword search; embeddings temporarily unavailable" : "semantic + keyword search"}`;
    } catch (error) { el("search-status").textContent = "Search could not complete. Try again when the service is ready."; throw error; }
  });
  function renderResult(outcome, hit) {
    const row = B.text("article", "", "result");
    if (outcome.status !== "fulfilled") { row.append(B.text("p", "Passage " + hit.id + " could not be loaded. " + outcome.reason.message)); el("results").append(row); return; }
    const chunk = outcome.value;
    row.append(B.text("h3", chunk.doc_title || "Untitled document"), B.text("div", "Document " + chunk.doc_id + " · passage " + chunk.id, "source"), B.text("p", chunk.text.slice(0, 360) + (chunk.text.length > 360 ? "…" : "")));
    const button = B.text("button", "Read passage"); button.type = "button";
    button.onclick = () => { el("reader-title").textContent = chunk.doc_title || "Passage"; el("reader-source").textContent = chunk.source || "Preserved in your brain"; el("reader-text").textContent = chunk.text; el("reader").showModal(); };
    row.append(button); el("results").append(row);
  }
  function selectTab(note) {
    el("note-form").hidden = !note; el("url-form").hidden = note;
    el("note-tab").setAttribute("aria-selected", String(note)); el("url-tab").setAttribute("aria-selected", String(!note));
  }
  el("note-tab").onclick = () => selectTab(true); el("url-tab").onclick = () => selectTab(false);
  el("close-reader").onclick = () => el("reader").close();
  el("refresh").onclick = async () => { await loadJobs(); schedule(); };
  el("lock").onclick = () => {
    B.setToken(""); clearTimeout(timer); authEpoch++; submissions.clear(); completed.clear(); loadedJobs = false; nextPollAt = 0;
    el("workspace").hidden = true; el("unlock-panel").hidden = false; el("lock").hidden = true;
    el("results").replaceChildren(B.text("div", "Your discoveries will appear here, with excerpts and a link to each source.", "empty")); el("jobs").replaceChildren(); el("reader").close();
    for (const id of ["note-title", "note-text", "page-url", "query", "reader-title", "reader-source", "reader-text"]) { if ("value" in el(id)) el(id).value = ""; else el(id).textContent = ""; }
    B.message("Locked. Open your desktop launcher or enter your token to return.");
  };
  document.addEventListener("visibilitychange", schedule);
  window.addEventListener("brain-auth", open); open();
})();
