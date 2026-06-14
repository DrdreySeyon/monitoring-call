async function fetchHealth() {
  try {
    const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/health/detailed`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (error) {
    return {
      api: { status: "fallback" },
      database: { status: "inconnu" },
      ari: { status: "inconnu" },
      ami: { enabled: false, connected: false, status: "non verifie" },
      scheduler: { status: "inconnu" },
      error: error.message,
    };
  }
}

async function fetchCalls() {
  try {
    const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/calls/history?page=1&page_size=25`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    const rows = Array.isArray(payload) ? payload : payload.items || payload.calls || payload.data || [];
    return rows.map(normalizeCall);
  } catch (error) {
    return sampleCalls;
  }
}

async function fetchScenarios() {
  try {
    const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/scenarios`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    return Array.isArray(payload) ? payload : payload.items || payload.scenarios || payload.data || [];
  } catch (error) {
    return sampleScenarios();
  }
}

async function fetchSchedulerJobs() {
  try {
    const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/scheduler/jobs`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    return Array.isArray(payload) ? payload : payload.items || payload.jobs || payload.data || [];
  } catch (error) {
    return sampleSchedulerJobs();
  }
}

async function createScenario(payload) {
  const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/scenarios`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function updateScenario(id, payload) {
  const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/scenarios/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function deleteScenario(id) {
  const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/scenarios/${id}`, { method: "DELETE" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function toggleScenario(id) {
  const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/scenarios/${id}/toggle`, { method: "POST" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function runScenario(id) {
  const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/scenarios/${id}/run-now`, { method: "POST" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function toggleSchedulerJob(id) {
  const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/scheduler/jobs/${encodeURIComponent(id)}/toggle`, { method: "POST" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function runSchedulerJob(id) {
  const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/scheduler/jobs/${encodeURIComponent(id)}/run-now`, { method: "POST" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function loadScenarios() {
  state.scenarios = await fetchScenarios();
  renderScenarios();
}

function normalizeCall(call) {
  return {
    ...call,
    id: call.id ?? call.call_id ?? call.channel_id,
    created_at: call.created_at ?? call.calldate,
    scenario_name: call.scenario_name ?? call.name ?? "-",
    scenario_category: call.scenario_category ?? call.category ?? "-",
    status: call.status ?? "unknown",
    status_label: call.status_label ?? formatStatus(call.status),
    vosk_status: call.vosk_status ?? call.keyword_status ?? "-",
    keyword_checks: ensureChecks(call.keyword_checks, call.scenario_keyword, call.keyword_status),
    voicemail_checks: ensureChecks(call.voicemail_checks, null, null),
  };
}

function ensureChecks(value, fallbackKeywords, fallbackStatus) {
  if (Array.isArray(value)) return value;
  if (!fallbackKeywords) return [];
  return String(fallbackKeywords)
    .split(",")
    .map((keyword) => keyword.trim())
    .filter(Boolean)
    .map((keyword) => ({ keyword, status: fallbackStatus || "KO" }));
}
