"use strict";
const SNAPSHOT = document.documentElement.dataset.mode === "snapshot";
const RESULTS_URL = SNAPSHOT ? "./data/latest.json" : "./api/results";
const ARCHIVE_URL = SNAPSHOT ? "./data/upstream_reanalysis.json" : "./api/upstream";
const $ = (id) => document.getElementById(id);
const ui = { data: null, episode: null, state: "differences" };
const pct = (n) => (Number.isFinite(n) ? `${(n * 100).toFixed(1)}%` : "—");
const readable = (value) =>
  typeof value === "string" ? value : JSON.stringify(value, null, 2);
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function status(message, error = false) {
  $("status").textContent = message;
  $("status").classList.toggle("error", error);
  $("status").hidden = !message;
}
function passK(episodes, tasks, k) {
  if (!tasks.length || !Number.isInteger(k) || k < 1) return null;
  const groups = tasks.map((t) => episodes.filter((e) => e.task_id === t.id));
  if (groups.some((es) => es.length < k)) return null;
  const estimates = groups.map((es) => {
    const s = es.filter((e) => e.success).length;
    if (s < k) return 0;
    let p = 1;
    for (let i = 0; i < k; i++) p *= (s - i) / (es.length - i);
    return p;
  });
  return estimates.reduce((a, b) => a + b, 0) / estimates.length;
}
function render() {
  const d = ui.data,
    agent = $("agent").value,
    category = $("category").value;
  const tasks = d.tasks.filter(
      (t) => category === "all" || t.category === category,
    ),
    ids = new Set(tasks.map((t) => t.id));
  const episodes = d.episodes.filter(
    (e) => e.agent_id === agent && ids.has(e.task_id),
  );
  $("success").textContent = pct(
    episodes.length
      ? episodes.filter((e) => e.success).length / episodes.length
      : null,
  );
  $("state-match").textContent = pct(
    episodes.length
      ? episodes.filter((e) => e.state_match).length / episodes.length
      : null,
  );
  $("compliance").textContent = pct(
    episodes.length
      ? episodes.filter((e) => !e.policy_violations?.length).length /
          episodes.length
      : null,
  );
  $("episodes").textContent = episodes.length.toLocaleString();
  $("coverage").textContent =
    `${tasks.length} tasks · ${d.trials_per_task} trials per task`;
  const eligible = [1, 2, 4, 8].filter(
      (k) => passK(episodes, tasks, k) !== null,
    ),
    maxK = eligible.at(-1);
  $("consistent").textContent = pct(maxK ? passK(episodes, tasks, maxK) : null);
  $("consistent-label").textContent = maxK
    ? `Pass^${maxK} · all ${maxK} attempts succeed`
    : "No eligible trials";
  $("matrix").replaceChildren();
  for (const task of tasks) {
    const row = el("div", undefined, "matrix-row"),
      name = el("div", task.title, "task-name");
    name.append(el("span", task.category, "task-category"));
    const trials = el("div", undefined, "trials");
    for (const ep of episodes
      .filter((e) => e.task_id === task.id)
      .sort((a, b) => a.trial - b.trial)) {
      const b = el(
        "button",
        ep.trial + 1,
        "trial " + (ep.success ? "good" : "bad"),
      );
      b.type = "button";
      b.title = `${task.title}, trial ${ep.trial + 1}: ${ep.success ? "pass" : "fail"}`;
      b.setAttribute("aria-label", b.title);
      b.setAttribute("aria-pressed", String(ui.episode === ep));
      if (ui.episode === ep) b.classList.add("selected");
      b.addEventListener("click", () => {
        ui.episode = ep;
        render();
        renderEpisode(task);
        $("detail").scrollIntoView({
          behavior: window.matchMedia("(prefers-reduced-motion: reduce)")
            .matches
            ? "instant"
            : "smooth",
          block: "nearest",
        });
      });
      trials.append(b);
    }
    row.append(name, trials);
    $("matrix").append(row);
  }
  if (!episodes.length)
    $("matrix").append(
      el(
        "p",
        "No episodes match these filters. Choose another strategy or category.",
        "empty",
      ),
    );
  $("chart").replaceChildren();
  for (const k of [1, 2, 4, 8]) {
    const p = passK(episodes, tasks, k),
      item = el("div", undefined, "bar-item"),
      bar = el("div", undefined, "bar");
    bar.style.height = `${p === null ? 0 : p * 135}px`;
    item.append(
      el("span", pct(p), "bar-value"),
      bar,
      el("span", `k = ${k}`, "bar-label"),
    );
    $("chart").append(item);
  }
  if (ui.episode && !episodes.includes(ui.episode)) {
    ui.episode = null;
    resetDetail();
  }
}
function resetDetail() {
  $("detail-title").textContent = "Select a trial above";
  $("detail-subtitle").textContent =
    "Inspect the conversation, policy checks, and final records.";
  $("detail-body").hidden = true;
  $("detail-badge").hidden = true;
}
function renderState() {
  if (!ui.episode) return;
  const value = ui.episode[ui.state];
  $("state").textContent =
    ui.state === "differences" && Array.isArray(value) && !value.length
      ? "No differences between expected and actual final state."
      : readable(value ?? "No data recorded.");
  document.querySelectorAll("[data-state]").forEach((b) => {
    b.classList.toggle("active", b.dataset.state === ui.state);
    b.setAttribute("aria-pressed", String(b.dataset.state === ui.state));
  });
}
function renderEpisode(task) {
  const e = ui.episode;
  $("detail-title").textContent = task.title;
  $("detail-subtitle").textContent =
    `${ui.data.agents.find((a) => a.id === e.agent_id)?.name ?? e.agent_id} · Trial ${e.trial + 1} · State ${e.state_match ? "matches" : "does not match"} expected records`;
  $("detail-body").hidden = false;
  $("detail-badge").hidden = false;
  $("detail-badge").textContent = e.success ? "PASS" : "FAIL";
  $("detail-badge").classList.toggle("failed", !e.success);
  $("trace").replaceChildren();
  for (const t of e.trace ?? []) {
    const node = el("div", undefined, "trace-item");
    node.append(
      el("div", t.role + (t.tool ? ` / ${t.tool}` : ""), "trace-role"),
    );
    if (t.content && t.result === undefined)
      node.append(el("p", readable(t.content)));
    if (t.arguments !== undefined)
      node.append(el("pre", readable(t.arguments)));
    if (t.result !== undefined) node.append(el("pre", readable(t.result)));
    $("trace").append(node);
  }
  if (!e.trace?.length)
    $("trace").append(el("p", "No conversation trace recorded.", "muted"));
  $("violations").replaceChildren();
  if (e.policy_violations?.length) {
    const list = el("ul");
    e.policy_violations.forEach((v) => list.append(el("li", readable(v))));
    $("violations").append(list);
  } else $("violations").textContent = "✓ No recorded policy violations";
  renderState();
}
async function load() {
  try {
    const response = await fetch(RESULTS_URL, { cache: "no-store" });
    if (!response.ok)
      throw new Error(`Results request returned ${response.status}.`);
    const d = await response.json();
    if (
      !Array.isArray(d.episodes) ||
      !Array.isArray(d.tasks) ||
      !Array.isArray(d.agents)
    )
      throw new Error("Results format is incomplete.");
    ui.data = d;
    ui.episode = null;
    const previous = $("agent").value;
    $("agent").replaceChildren();
    d.agents.forEach((a) => {
      const option = el("option", a.name);
      option.value = a.id;
      $("agent").append(option);
    });
    if (d.agents.some((a) => a.id === previous)) $("agent").value = previous;
    $("category").replaceChildren(new Option("All categories", "all"));
    [...new Set(d.tasks.map((t) => t.category))]
      .sort()
      .forEach((c) => $("category").append(new Option(c, c)));
    $("limitations").replaceChildren();
    (d.limitations ?? []).forEach((l) =>
      $("limitations").append(el("li", readable(l))),
    );
    const date = new Date(d.created_at);
    $("timestamp").textContent = Number.isNaN(date.getTime())
      ? "Run timestamp unavailable"
      : `${SNAPSHOT ? "SNAPSHOT" : "RUN"} · ${date.toLocaleString()}`;
    $("workspace").hidden = false;
    resetDetail();
    render();
    status(
      d.episodes.length
        ? ""
        : "No episodes yet. Run the scripted benchmark to generate results.",
    );
  } catch (error) {
    status(
      `Could not load results. ${error.message} ${SNAPSHOT ? "Reload the page or view the saved artifacts in the source repository." : "Start the local server and use “Run scripted benchmark” to generate results."}`,
      true,
    );
  }
}
$("agent").addEventListener("change", render);
$("category").addEventListener("change", render);
document.querySelectorAll("[data-state]").forEach((b) =>
  b.addEventListener("click", () => {
    ui.state = b.dataset.state;
    renderState();
  }),
);
if (!SNAPSHOT) $("run").addEventListener("click", async () => {
  const button = $("run");
  button.disabled = true;
  button.textContent = "Running scripted benchmark…";
  status("Running scripted strategies against the simulated SaaS tasks…");
  try {
    const r = await fetch("./api/run", { method: "POST" });
    if (!r.ok) throw new Error(`Benchmark request returned ${r.status}.`);
    await load();
  } catch (error) {
    status(
      `Benchmark could not finish. ${error.message} Check the server output and try again.`,
      true,
    );
  } finally {
    button.disabled = false;
    button.textContent = "Run scripted benchmark ↗";
  }
});
async function loadArchive() {
  const section = el("section", undefined, "panel archive-panel");
  const head = el("div", undefined, "panel-heading"),
    copy = el("div");
  copy.append(
    el("p", "ARCHIVED RESEARCH / INDEPENDENT REANALYSIS", "eyebrow"),
    el("h3", "Recalculating archived reliability"),
    el(
      "p",
      "Authors’ archived runs · independently recalculated · no new model calls",
    ),
  );
  head.append(copy);
  section.append(head);
  const container = el("div", undefined, "archive-content");
  section.append(container);
  document.querySelector("footer").before(section);
  try {
    const r = await fetch(ARCHIVE_URL, { cache: "no-store" });
    if (!r.ok) throw new Error("Archive data is unavailable.");
    const data = await r.json();
    if (!data.datasets?.length)
      throw new Error("No archived runs have been imported.");
    const table = el("table"),
      thead = el("thead"),
      tr = el("tr");
    [
      "Archived run",
      "Episodes",
      "Tasks",
      "Pass¹",
      "Pass²",
      "Pass⁴",
      "Pass⁸",
    ].forEach((x) => tr.append(el("th", x)));
    thead.append(tr);
    table.append(thead);
    const tbody = el("tbody");
    data.datasets.forEach((d) => {
      const row = el("tr"),
        name = el("td");
      const a = el("a", d.file);
      try {
        const u = new URL(d.source_url);
        if (u.protocol === "https:") {
          a.href = u.href;
          a.target = "_blank";
          a.rel = "noopener noreferrer";
        }
      } catch {}
      name.append(a);
      row.append(name, el("td", d.episodes), el("td", d.tasks));
      [1, 2, 4, 8].forEach((k) =>
        row.append(el("td", pct(d.pass_k?.[String(k)]))),
      );
      tbody.append(row);
    });
    table.append(tbody);
    container.append(table);
    const notes = el("ul", undefined, "archive-notes");
    (data.limitations ?? []).forEach((l) =>
      notes.append(el("li", readable(l))),
    );
    container.append(notes);
  } catch (error) {
    container.append(
      el(
        "p",
        `${error.message} Archived paper results will appear here when available.`,
        "muted",
      ),
    );
  }
}
load();
loadArchive();
