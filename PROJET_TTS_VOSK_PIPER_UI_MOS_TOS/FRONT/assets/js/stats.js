function renderKpis() {
  const calls = state.calls;
  setText("kpiTotal", state.callsTotal || calls.length);
  setText("kpiAnswered", calls.filter((call) => call.status === "answered").length);
  setText("kpiMissed", calls.filter((call) => ["missed", "no_answer", "not_answered"].includes(call.status)).length);
  setText("kpiKeywordOk", calls.filter((call) => String(call.vosk_status).toUpperCase() === "OK").length);
  setText("kpiVoicemail", calls.filter((call) => String(call.vosk_status).toUpperCase() === "VOICEMAIL").length);
  setText("kpiErrors", calls.filter((call) => call.status === "trunk_error" || call.sip_error_code).length);
  setText("kpiTtsCalls", calls.filter((call) => ["tts", "tts_dtmf"].includes(callMode(call))).length);
  setText("kpiTtsOk", calls.filter((call) => ttsStatus(call) === "ok").length);
  const mosValues = calls
    .map((call) => call.mos_score == null || call.mos_score === "" ? null : Number(call.mos_score))
    .filter((value) => Number.isFinite(value));
  const mosAverage = mosValues.length
    ? mosValues.reduce((sum, value) => sum + value, 0) / mosValues.length
    : null;
  setText("kpiMosAvg", mosAverage == null ? "-" : formatMos(mosAverage));
  setText("kpiQosKo", calls.filter((call) => {
    const score = call.mos_score == null || call.mos_score === "" ? null : Number(call.mos_score);
    return Number.isFinite(score) && score < 3.6;
  }).length);
}
