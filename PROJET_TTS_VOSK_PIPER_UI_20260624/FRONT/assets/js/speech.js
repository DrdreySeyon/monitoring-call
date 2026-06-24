function bindVoskFilters() {
  document.getElementById("voskSearchInput").addEventListener("input", renderVoskList);
  document.getElementById("voskStatusFilter").addEventListener("change", renderVoskList);
  document.getElementById("voskModeFilter").addEventListener("change", renderVoskList);
}

function renderVoskList() {
  const query = document.getElementById("voskSearchInput").value.trim().toLowerCase();
  const status = document.getElementById("voskStatusFilter").value;
  const mode = document.getElementById("voskModeFilter").value;
  const rows = state.calls.filter((call) => {
    const haystack = [
      call.scenario_name,
      call.scenario_category,
      call.scenario_keyword,
      call.keyword_expected,
      call.keyword_detected,
      call.tts,
      call.transcription,
      call.recording_path,
    ]
      .join(" ")
      .toLowerCase();
    const statusOk = !status || String(call.vosk_status).toUpperCase() === status;
    const modeOk = !mode || callMode(call) === mode;
    return (!query || haystack.includes(query)) && statusOk && modeOk;
  });

  document.getElementById("voskList").innerHTML = rows
    .map(
      (call) => `
      <article class="vosk-card">
        <div class="scenario-card-head">
          <div>
            <strong>${escapeHtml(call.scenario_name || `Appel #${call.id}`)}</strong>
            <span>Appel #${escapeHtml(call.id)} - ${formatDate(call.created_at)}</span>
          </div>
          <div class="chip-row">${callModeChip(call)}${voskChip(call)}${ttsChip(call)}</div>
        </div>
        <div class="scenario-meta">
          ${kvInline("Categorie", call.scenario_category || "-")}
          ${kvInline("TTS attendu", call.tts || "-")}
          ${kvInline("Mots-cles attendus", call.keyword_expected || call.scenario_keyword || "-")}
          ${kvInline("Mots-cles detectes", call.keyword_detected || "-")}
          ${kvInline("Audio", call.recording_path || "-")}
        </div>
        ${checksHtml(call.keyword_checks, call.voicemail_checks)}
        <p class="transcription">${escapeHtml(call.transcription || "Aucune transcription disponible.")}</p>
      </article>
    `,
    )
    .join("");
}
