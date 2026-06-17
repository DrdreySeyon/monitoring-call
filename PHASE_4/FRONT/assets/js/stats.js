function renderKpis() {
  const calls = state.calls;
  setText("kpiTotal", state.callsTotal || calls.length);
  setText("kpiAnswered", calls.filter((call) => call.status === "answered").length);
  setText("kpiMissed", calls.filter((call) => ["missed", "no_answer", "not_answered"].includes(call.status)).length);
  setText("kpiKeywordOk", calls.filter((call) => String(call.vosk_status).toUpperCase() === "OK").length);
  setText("kpiVoicemail", calls.filter((call) => String(call.vosk_status).toUpperCase() === "VOICEMAIL").length);
  setText("kpiErrors", calls.filter((call) => call.status === "trunk_error" || call.sip_error_code).length);
}
