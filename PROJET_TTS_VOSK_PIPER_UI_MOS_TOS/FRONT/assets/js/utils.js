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

function toDatetimeLocalValue(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 16);
  const offsetMs = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

function formatDuration(value) {
  const seconds = Number(value);
  if (!Number.isFinite(seconds)) return "-";
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

function formatNumber(value, digits = 1) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return number.toLocaleString("fr-FR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}

function formatMos(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return number.toLocaleString("fr-FR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 2,
  });
}

function formatMs(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return `${formatNumber(number, 1)} ms`;
}

function formatPercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return `${formatNumber(number, 2)} %`;
}

function formatFrequency(value) {
  const map = {
    once: "Une fois",
    interval_30m: "Toutes les 30 min",
    interval_1h: "Toutes les 1h",
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

function callMode(call = {}) {
  const hasTts = Boolean(String(call.tts || "").trim());
  const hasDtmf = Boolean(String(call.dtmf || "").trim() && String(call.dtmf || "").trim() !== "-");
  if (hasTts && hasDtmf) return "tts_dtmf";
  if (hasTts) return "tts";
  if (hasDtmf) return "dtmf";
  return "standard";
}

function callModeLabel(mode) {
  const map = {
    tts_dtmf: "TTS + DTMF",
    tts: "TTS",
    dtmf: "DTMF",
    standard: "Standard",
  };
  return map[mode] || "Standard";
}

function callModeChip(call) {
  const mode = callMode(call);
  const map = {
    tts_dtmf: "chip-info",
    tts: "chip-info",
    dtmf: "chip-warn",
    standard: "chip-muted",
  };
  return `<span class="chip ${map[mode] || "chip-muted"}">${escapeHtml(callModeLabel(mode))}</span>`;
}

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function keywordList(value) {
  return String(value || "")
    .split(/[;,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function ttsStatus(call = {}) {
  if (callMode(call) !== "tts" && callMode(call) !== "tts_dtmf") return "none";
  const transcription = normalizeText(call.transcription);
  if (!transcription) return "pending";

  const expected = keywordList(call.keyword_expected || call.scenario_keyword);
  if (!expected.length) return "unknown";

  return expected.some((keyword) => transcription.includes(normalizeText(keyword))) ? "ok" : "ko";
}

function ttsChip(call) {
  const status = ttsStatus(call);
  const map = {
    ok: ["chip-ok", "TTS detecte"],
    ko: ["chip-ko", "TTS non detecte"],
    pending: ["chip-muted", "TTS en attente"],
    unknown: ["chip-warn", "TTS non qualifie"],
    none: ["chip-muted", "Sans TTS"],
  };
  const [cls, label] = map[status] || map.unknown;
  return `<span class="chip ${cls}">${escapeHtml(label)}</span>`;
}

function mosLevel(call = {}) {
  const score = Number(call.mos_score);
  if (!Number.isFinite(score)) return ["chip-muted", "MOS N/A"];
  if (score >= 4.0) return ["chip-ok", `MOS ${formatMos(score)}`];
  if (score >= 3.6) return ["chip-warn", `MOS ${formatMos(score)}`];
  return ["chip-ko", `MOS ${formatMos(score)}`];
}

function mosChip(call = {}) {
  const [cls, label] = mosLevel(call);
  const text = call.mos_label ? `${label} - ${call.mos_label}` : label;
  return `<span class="chip ${cls}">${escapeHtml(text)}</span>`;
}

function qualitySummary(call = {}) {
  const parts = [];
  if (call.rtp_jitter_ms != null) parts.push(`jitter ${formatMs(call.rtp_jitter_ms)}`);
  if (call.rtp_packet_loss_pct != null) parts.push(`perte ${formatPercent(call.rtp_packet_loss_pct)}`);
  if (call.rtp_rtt_ms != null) parts.push(`RTT ${formatMs(call.rtp_rtt_ms)}`);
  if (call.rtp_rxcount != null || call.rtp_txcount != null) parts.push(`paquets ${call.rtp_rxcount ?? "-"} / ${call.rtp_txcount ?? "-"}`);
  if (call.rtp_lost_packets != null) parts.push(`perdus ${call.rtp_lost_packets}`);
  return parts.length ? parts.join(" / ") : "metriques RTP non renseignees";
}

function checksHtml(keywordChecks = [], voicemailChecks = []) {
  const checks = [...keywordChecks, ...voicemailChecks];
  if (!checks.length) return "";
  return `<div class="chip-row">${checks
    .map((check) => `<span class="chip ${String(check.status).toUpperCase() === "OK" ? "chip-ok" : "chip-ko"}">${escapeHtml(check.keyword || "-")} ${escapeHtml(check.status || "")}</span>`)
    .join("")}</div>`;
}
