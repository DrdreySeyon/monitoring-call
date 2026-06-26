function bindFilters() {
  document.getElementById("searchInput").addEventListener("input", applyFilters);
  document.getElementById("statusFilter").addEventListener("change", applyFilters);
}

function bindHistoryFilters() {
  document.getElementById("historySearchInput").addEventListener("input", renderFullHistory);
  document.getElementById("historyCategoryFilter").addEventListener("change", renderFullHistory);
  document.getElementById("historyCallStatusFilter").addEventListener("change", renderFullHistory);
  document.getElementById("historyVoskFilter").addEventListener("change", renderFullHistory);
  document.getElementById("historyFromDate").addEventListener("change", renderFullHistory);
  document.getElementById("historyToDate").addEventListener("change", renderFullHistory);
  document.getElementById("historyExportBtn").addEventListener("click", exportFilteredHistoryCsv);
}

function applyFilters() {
  const query = document.getElementById("searchInput").value.trim().toLowerCase();
  const status = document.getElementById("statusFilter").value;
  state.filteredCalls = state.calls.filter((call) => {
    const haystack = [
      call.scenario_name,
      call.scenario_category,
      call.caller,
      call.callee,
      call.trunk,
      call.scenario_keyword,
      call.transcription,
    ]
      .join(" ")
      .toLowerCase();
    return (!query || haystack.includes(query)) && (!status || call.status === status);
  });

  if (!state.filteredCalls.some((call) => call.id === state.selectedId)) {
    state.selectedId = state.filteredCalls[0]?.id ?? null;
  }

  renderKpis();
  renderTable();
  renderFullHistory();
  renderDetail();
  renderTimeline();
  renderVoskList();
}

function renderTable() {
  const body = document.getElementById("callsTable");
  body.innerHTML = "";

  state.filteredCalls.forEach((call) => {
    const row = document.createElement("tr");
    row.className = call.id === state.selectedId ? "is-selected" : "";
    row.innerHTML = `
      <td>${formatDate(call.created_at)}</td>
      <td><strong>${escapeHtml(call.scenario_name || "-")}</strong><br><small class="muted">${escapeHtml(call.scenario_category || "-")}</small></td>
      <td><div class="number-stack"><strong>${escapeHtml(call.caller || "-")}</strong><small>vers ${escapeHtml(call.callee || "-")}</small><small>${escapeHtml(call.trunk || "-")}</small></div></td>
      <td>${statusChip(call)}</td>
      <td>${voskChip(call)}${checksHtml(call.keyword_checks, call.voicemail_checks)}</td>
      <td>${escapeHtml(call.hangup_cause_detail || call.error_message || "-")}</td>
    `;
    row.addEventListener("click", () => {
      state.selectedId = call.id;
      renderTable();
      renderDetail();
      renderTimeline();
    });
    body.appendChild(row);
  });
}

function renderFullHistory() {
  const body = document.getElementById("historyFullTable");
  if (!body) return;
  renderHistoryCategoryOptions();
  const calls = getFilteredHistoryCalls();

  body.innerHTML = calls
    .map(
      (call) => `
      <tr>
        <td>${formatDate(call.created_at)}</td>
        <td><strong>${escapeHtml(call.scenario_name || "-")}</strong><br><small class="muted">${escapeHtml(call.scenario_category || "-")}</small></td>
        <td>${escapeHtml(call.caller || "-")}</td>
        <td>${escapeHtml(call.callee || "-")}</td>
        <td>${escapeHtml(call.trunk || "-")}</td>
        <td>${statusChip(call)}</td>
        <td>${voskChip(call)}${checksHtml(call.keyword_checks, call.voicemail_checks)}</td>
        <td>${escapeHtml(call.dtmf || "-")}</td>
        <td>${formatDuration(call.duration)} / ${formatDuration(call.call_time_s)}</td>
        <td>${escapeHtml(call.error_message || call.hangup_cause_detail || "-")}</td>
      </tr>
    `,
    )
    .join("");
}

function getFilteredHistoryCalls() {
  const query = document.getElementById("historySearchInput").value.trim().toLowerCase();
  const category = document.getElementById("historyCategoryFilter").value;
  const callStatus = document.getElementById("historyCallStatusFilter").value;
  const voskStatus = document.getElementById("historyVoskFilter").value;
  const fromDate = document.getElementById("historyFromDate").value;
  const toDate = document.getElementById("historyToDate").value;
  return state.calls.filter((call) => {
    const haystack = [
      call.scenario_name,
      call.scenario_category,
      call.caller,
      call.callee,
      call.trunk,
      call.hangup_cause_detail,
      call.error_message,
      call.scenario_keyword,
      call.transcription,
    ]
      .join(" ")
      .toLowerCase();
    const callStatusOk = !callStatus || call.status === callStatus;
    const voskOk = !voskStatus || String(call.vosk_status).toUpperCase() === voskStatus;
    const categoryOk = !category || call.scenario_category === category;
    const dateOk = isCallInHistoryDateRange(call, fromDate, toDate);
    return (!query || haystack.includes(query)) && categoryOk && callStatusOk && voskOk && dateOk;
  });
}

function renderHistoryCategoryOptions() {
  const select = document.getElementById("historyCategoryFilter");
  if (!select) return;
  const current = select.value;
  const categories = [...new Set(state.calls.map((call) => call.scenario_category).filter(Boolean))]
    .sort((a, b) => String(a).localeCompare(String(b), "fr", { sensitivity: "base" }));
  select.innerHTML = [
    `<option value="">Toutes les categories</option>`,
    ...categories.map((category) => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`),
  ].join("");
  select.value = categories.includes(current) ? current : "";
}

function isCallInHistoryDateRange(call, fromDate, toDate) {
  if (!fromDate && !toDate) return true;
  const callDate = new Date(call.created_at);
  if (Number.isNaN(callDate.getTime())) return true;
  if (fromDate && callDate < new Date(`${fromDate}T00:00:00`)) return false;
  if (toDate && callDate > new Date(`${toDate}T23:59:59`)) return false;
  return true;
}

function exportFilteredHistoryCsv() {
  const calls = getFilteredHistoryCalls();
  const headers = [
    "date",
    "scenario",
    "categorie",
    "caller",
    "callee",
    "trunk",
    "statut_appel",
    "resultat_metier",
    "dtmf",
    "duree_reelle",
    "duree_prevue",
    "hangup_cause",
    "cause",
    "sip_error_code",
    "mots_cles",
    "transcription",
  ];
  const rows = calls.map((call) => [
    call.created_at || "",
    call.scenario_name || "",
    call.scenario_category || "",
    call.caller || "",
    call.callee || "",
    call.trunk || "",
    call.status_label || call.status || "",
    call.vosk_status || "",
    call.dtmf || "",
    call.duration ?? "",
    call.call_time_s ?? "",
    call.hangup_cause ?? "",
    call.error_message || call.hangup_cause_detail || "",
    call.sip_error_code || "",
    call.scenario_keyword || "",
    call.transcription || "",
  ]);
  const csv = [headers, ...rows].map((row) => row.map(csvCell).join(";")).join("\n");
  const blob = new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `historique_tcu_${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

function csvCell(value) {
  return `"${String(value ?? "").replaceAll('"', '""')}"`;
}

function renderDetail() {
  const call = selectedCall();
  const detail = document.getElementById("callDetail");
  document.getElementById("detailTitle").textContent = call ? `Appel #${call.id}` : "Selectionner un appel";

  if (!call) {
    detail.className = "detail-empty";
    detail.textContent = "Aucun appel selectionne.";
    return;
  }

  detail.className = "";
  detail.innerHTML = `
    <div class="detail-section">
      <h3>Statut appel</h3>
      <div class="chip-row">${statusChip(call)}${call.sip_error_code ? `<span class="chip chip-ko">SIP ${escapeHtml(call.sip_error_code)}</span>` : ""}</div>
      ${kv("Cause AMI", call.hangup_cause_detail || "-")}
      ${kv("Code hangup", call.hangup_cause || "-")}
      ${kv("Erreur", call.error_message || "-")}
    </div>
    <div class="detail-section">
      <h3>CDR</h3>
      ${kv("Disposition", call.cdr_disposition || call.disposition || "-")}
      ${kv("Duree reelle", formatDuration(call.duration))}
      ${kv("Duree prevue", formatDuration(call.call_time_s))}
      ${kv("Channel", call.channel_id || "-")}
    </div>
    <div class="detail-section">
      <h3>Vosk et mots-cles</h3>
      <div class="chip-row">${voskChip(call)}</div>
      ${checksHtml(call.keyword_checks, call.voicemail_checks)}
      <p class="transcription">${escapeHtml(call.transcription || "Aucune transcription disponible.")}</p>
    </div>
    <div class="detail-section">
      <h3>Scenario</h3>
      ${kv("Nom", call.scenario_name || "-")}
      ${kv("Categorie", call.scenario_category || "-")}
      ${kv("Mots-cles", call.scenario_keyword || "-")}
      ${kv("DTMF", call.dtmf || "-")}
    </div>
  `;
}

function renderTimeline() {
  const call = selectedCall();
  const timeline = document.getElementById("timeline");
  if (!call) {
    timeline.innerHTML = "";
    return;
  }

  const steps = [
    ["Scenario", call.scenario_name || "Scenario inconnu"],
    ["ARI", `Appel cree vers ${call.callee || "-"}`],
    ["DTMF", call.dtmf && call.dtmf !== "-" ? `DTMF ${call.dtmf}` : "Aucun DTMF"],
    ["AMI/CDR", `${call.status_label || formatStatus(call.status)} - ${call.hangup_cause_detail || "cause non renseignee"}`],
    ["Vosk", `${call.vosk_status || "-"} - ${call.transcription ? "transcription disponible" : "pas de transcription"}`],
  ];

  timeline.innerHTML = steps
    .map(([title, text]) => `<div class="timeline-step"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(text)}</span></div>`)
    .join("");
}

function selectedCall() {
  return state.calls.find((call) => call.id === state.selectedId) || null;
}
