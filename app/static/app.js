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

async function startGeneration(brief, variations) {
  grid.innerHTML = "";
  const requests = [];
  for (let v = 1; v <= variations; v++) requests.push(generateSlot(brief, v));
  await Promise.all(requests);
}

async function generateSlot(brief, variation) {
  const response = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ brief, variation }),
  });
  const data = await response.json().catch(() => ({}));
  if (response.status === 400 || response.status === 422) {
    grid.innerHTML = "";
    showFormError(data.detail);
    return;
  }
  // Generation itself is added in the week06-jeevan pull request.
  showFormError(data.detail || "");
}

// ===== Critique (Sidally) =====
// Added in the week06-sidally pull request.

updateButton();
