// Ranking of finished slots (spec.md, "Ranking").
// Highest score first; slots without a score (critique unavailable, generation failed) last;
// equal scores keep their variation order, because Array.prototype.sort is stable.
"use strict";

function isFinished(slot) {
  return slot.status === "critiqued" || slot.status === "unavailable" || slot.status === "failed";
}

function scoreOf(slot) {
  return slot.status === "critiqued" && slot.result && Number.isInteger(slot.result.score) ? slot.result.score : null;
}

function rankSlots(slots) {
  return [...slots].sort((a, b) => {
    const sa = scoreOf(a);
    const sb = scoreOf(b);
    if (sa === null && sb === null) return 0;
    if (sa === null) return 1;
    if (sb === null) return -1;
    return sb - sa;
  });
}
