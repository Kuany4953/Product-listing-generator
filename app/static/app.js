// The page: one form, one grid. Each owner has a marked section (plan.md, "Owners and branches").
"use strict";

const LIMITS = { product_name: 80, color: 40, material: 40, background: 80, style: 80, extra_details: 300 };
const REQUIRED = ["product_name", "color", "material", "background"];

// ===== Form (Kuany): validation mirrors app/brief.py =====

const form = document.getElementById("brief");
const button = document.getElementById("generate");
const formError = document.getElementById("form-error");

function readBrief() {
  const brief = {};
  for (const name of Object.keys(LIMITS)) {
    const value = document.getElementById(name).value.trim();
    if (value) brief[name] = value;
  }
  return brief;
}

function briefIsValid(brief) {
  const filled = REQUIRED.every((name) => brief[name]);
  const withinLimits = Object.entries(LIMITS).every(([name, max]) => (brief[name] || "").length <= max);
  return filled && withinLimits;
}

function updateButton() {
  button.disabled = !briefIsValid(readBrief());
}

function showFormError(message) {
  formError.textContent = message || "";
}

form.addEventListener("input", () => {
  showFormError("");
  updateButton();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const brief = readBrief();
  if (!briefIsValid(brief)) return;
  showFormError("");
  button.disabled = true;
  try {
    const config = await (await fetch("/api/config")).json();
    await startGeneration(brief, config.variations);
  } finally {
    updateButton();
  }
});

// ===== Grid (Jeevan): one request per variation =====

const grid = document.getElementById("grid");
const VIEWS = ["Front view", "Top-down view", "Close-up", "Three-quarter view", "Lifestyle scene"];
let slots = [];        // one state object per variation: { variation, el, status, id, result }

async function startGeneration(brief, variations) {
  grid.innerHTML = "";
  slots = [];
  for (let v = 1; v <= variations; v++) slots.push(makeSlot(brief, v));
  await Promise.all(slots.map(generateSlot));
}

function makeSlot(brief, variation) {
  const el = document.createElement("div");
  el.className = "slot";
  el.dataset.variation = variation;
  el.innerHTML = `<div class="frame"></div>
    <div class="body"><div class="title"></div><div class="status"></div><div class="critique"></div></div>`;
  el.querySelector(".title").textContent = `${variation}. ${VIEWS[variation - 1]}`;
  grid.appendChild(el);
  return { brief, variation, el, status: "pending", id: null, result: null };
}

async function generateSlot(slot) {
  slot.status = "pending";
  slot.el.querySelector(".frame").innerHTML = '<div class="spinner" aria-label="Generating"></div>';
  slot.el.querySelector(".status").textContent = "Generating…";
  let response, data;
  try {
    response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ brief: slot.brief, variation: slot.variation }),
    });
    data = await response.json().catch(() => ({}));
  } catch {
    response = { ok: false, status: 0 };
    data = {};
  }
  if (response.status === 400 || response.status === 422) {   // the brief itself was refused
    grid.innerHTML = "";
    slots = [];
    showFormError(data.detail);
    return;
  }
  if (!response.ok) return showFailure(slot, data.detail);
  showImage(slot, data);
}

function showImage(slot, data) {
  slot.id = data.id;
  slot.status = "generated";
  const frame = slot.el.querySelector(".frame");
  frame.innerHTML = '<img alt=""><span class="badge ai">AI-generated mockup</span>';
  frame.querySelector("img").src = data.imageUrl;
  frame.querySelector("img").alt = `${VIEWS[slot.variation - 1]} of ${slot.brief.product_name} (AI-generated)`;
  slot.el.querySelector(".status").textContent = "";
  onImageReady(slot);
}

function showFailure(slot, detail) {
  slot.status = "failed";
  slot.el.querySelector(".frame").textContent = "No image";
  const status = slot.el.querySelector(".status");
  status.innerHTML = '<span class="error"></span> <button class="retry" type="button">Retry</button>';
  status.querySelector(".error").textContent = detail || "Image could not be generated";
  status.querySelector(".retry").addEventListener("click", () => generateSlot(slot));
  onSlotFinished(slot);
}

// ===== Critique (Sidally): checklist under each image, then ranking =====

const disclaimer = document.getElementById("disclaimer");

async function onImageReady(slot) {
  const box = slot.el.querySelector(".critique");
  box.textContent = "Critiquing…";
  let body = {};
  try {
    const response = await fetch("/api/critique", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: slot.id }),
    });
    body = await response.json();
  } catch {
    body = {};
  }
  if (body.status === "ok") {
    slot.status = "critiqued";
    slot.result = body;
    showCritique(slot);
  } else {
    slot.status = "unavailable";
    slot.result = null;
    box.textContent = "Critique unavailable";
  }
  disclaimer.hidden = false;
  onSlotFinished(slot);
}

function addLine(box, className, text) {
  const p = document.createElement("p");
  p.className = className;
  p.textContent = text;
  box.appendChild(p);
}

function showCritique(slot) {
  const r = slot.result;
  const box = slot.el.querySelector(".critique");
  box.innerHTML = "";
  addLine(box, "score", `Score ${r.score}/10`);
  const list = document.createElement("ul");
  list.className = "checks";
  for (const c of r.checks) {
    const li = document.createElement("li");
    li.className = c.met ? "met" : "unmet";
    li.textContent = c.requirement;
    const evidence = document.createElement("span");
    evidence.className = "evidence";
    evidence.textContent = c.evidence;
    li.appendChild(evidence);
    list.appendChild(li);
  }
  box.appendChild(list);
  if (r.missing.length) addLine(box, "unmet", `Not answered by the critic: ${r.missing.join("; ")}`);
  if (r.invented.length) addLine(box, "note", `Critic added (not scored): ${r.invented.join("; ")}`);
  if (r.problems.length) addLine(box, "unmet", `Problems: ${r.problems.join("; ")}`);
  if (r.disagreements.length) {
    addLine(box, "disagree", `Critics disagree on: ${r.disagreements.join("; ")} (look at the image yourself)`);
  }
  if (r.second_status === "unavailable") addLine(box, "note", "Second critic unavailable");
}

function onSlotFinished() {
  if (!slots.length || !slots.every(isFinished)) return;
  for (const s of slots) {
    s.el.classList.remove("top-pick");
    s.el.querySelector(".badge.pick")?.remove();
  }
  const ranked = rankSlots(slots);
  for (const s of ranked) grid.appendChild(s.el);
  const top = ranked[0];
  if (top && scoreOf(top) !== null) {
    top.el.classList.add("top-pick");
    const badge = document.createElement("span");
    badge.className = "badge pick";
    badge.textContent = "Top pick";
    top.el.querySelector(".frame").appendChild(badge);
  }
}

updateButton();
