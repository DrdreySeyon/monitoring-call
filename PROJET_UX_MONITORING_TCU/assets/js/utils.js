function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function formatStatus(status) {
  return String(status || "Inconnu").replaceAll("_", " ");
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function formatDuration(value) {
  const seconds = Number(value);
  if (!Number.isFinite(seconds)) return "-";
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

function formatFrequency(value) {
  const map = {
    once: "Une fois",
    daily: "Quotidien",
    weekly: "Hebdomadaire",
    monthly: "Mensuel",
  };
  return map[value] || value || "Aucune";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function kv(label, value) {
  return `<div class="kv"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function kvInline(label, value) {
  return `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function statusChip(call) {
  const status = call.status || "unknown";
  const map = {
    answered: ["chip-ok", "Decroche"],
    missed: ["chip-warn", "Non decroche"],
    no_answer: ["chip-warn", "Non decroche"],
    not_answered: ["chip-warn", "Non decroche"],
    busy: ["chip-warn", "Occupe"],
    trunk_error: ["chip-ko", "Erreur trunk"],
    failed: ["chip-ko", "Echec"],
  };
  const [cls, label] = map[status] || ["chip-muted", call.status_label || formatStatus(status)];
  return `<span class="chip ${cls}">${escapeHtml(label)}</span>`;
}

function voskChip(call) {
  const status = String(call.vosk_status || "-").toUpperCase();
  const map = {
    OK: ["chip-ok", "Mot-cle OK"],
    KO: ["chip-ko", "Mot-cle KO"],
    VOICEMAIL: ["chip-info", "Messagerie vocale"],
  };
  const [cls, label] = map[status] || ["chip-muted", status];
  return `<span class="chip ${cls}">${escapeHtml(label)}</span>`;
}

function checksHtml(keywordChecks = [], voicemailChecks = []) {
  const checks = [...keywordChecks, ...voicemailChecks];
  if (!checks.length) return "";
  return `<div class="chip-row">${checks
    .map((check) => `<span class="chip ${String(check.status).toUpperCase() === "OK" ? "chip-ok" : "chip-ko"}">${escapeHtml(check.keyword || "-")} ${escapeHtml(check.status || "")}</span>`)
    .join("")}</div>`;
}
