async function fetchHealth() {
  try {
    const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/health/detailed`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return normalizeHealth(await response.json());
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
    const pageSize = 100;
    const firstResponse = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/calls/history?page=1&page_size=${pageSize}`, { cache: "no-store" });
    if (!firstResponse.ok) throw new Error(`HTTP ${firstResponse.status}`);
    const firstPayload = await firstResponse.json();
    const firstRows = Array.isArray(firstPayload) ? firstPayload : firstPayload.items || firstPayload.calls || firstPayload.data || [];
    const total = firstPayload.total ?? firstRows.length;
    const totalPages = Math.min(Math.ceil(total / pageSize), 10);
    const rows = [...firstRows];

    for (let page = 2; page <= totalPages; page += 1) {
      const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/calls/history?page=${page}&page_size=${pageSize}`, { cache: "no-store" });
      if (!response.ok) break;
      const payload = await response.json();
      rows.push(...(Array.isArray(payload) ? payload : payload.items || payload.calls || payload.data || []));
    }

    state.callsTotal = total;
    return rows.map(normalizeCall);
  } catch (error) {
    state.callsTotal = sampleCalls.length;
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
    const rows = Array.isArray(payload) ? payload : payload.items || payload.jobs || payload.data || [];
    return rows.map(normalizeSchedulerJob);
  } catch (error) {
    return sampleSchedulerJobs();
  }
}

async function createScenario(payload) {
  const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/scenarios`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prepareScenarioPayload(payload)),
  });
  await assertOk(response);
  return response.json();
}

async function importScenariosFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/scenarios/import`, {
    method: "POST",
    body: formData,
  });
  await assertOk(response);
  return response.json();
}

async function updateScenario(id, payload) {
  const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/scenarios/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prepareScenarioPayload(payload)),
  });
  await assertOk(response);
  return response.json();
}

async function deleteScenario(id) {
  const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/scenarios/${id}`, { method: "DELETE" });
  await assertOk(response);
  return response.json();
}

async function toggleScenario(id) {
  const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/scenarios/${id}/toggle`, { method: "POST" });
  await assertOk(response);
  return response.json();
}

async function runScenario(id) {
  const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/scenarios/${id}/run-now`, { method: "POST" });
  await assertOk(response);
  return response.json();
}

async function checkScenarioConfig(id) {
  const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/scenarios/${id}/config-check`, { cache: "no-store" });
  await assertOk(response);
  return response.json();
}

async function toggleSchedulerJob(id) {
  const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/scheduler/jobs/${encodeURIComponent(id)}/toggle`, { method: "POST" });
  await assertOk(response);
  return response.json();
}

async function runSchedulerJob(id) {
  const response = await fetch(`${CONFIG.apiBaseUrl}${CONFIG.apiPrefix}/scheduler/jobs/${encodeURIComponent(id)}/run-now`, { method: "POST" });
  await assertOk(response);
  return response.json();
}

async function assertOk(response) {
  if (response.ok) return;

  let detail = "";
  try {
    const payload = await response.json();
    detail = formatApiError(payload.detail || payload.message || payload.error || payload);
  } catch (error) {
    detail = await response.text().catch(() => "");
  }

  throw new Error(detail || `HTTP ${response.status}`);
}

function formatApiError(value) {
  if (!value) return "";

  if (typeof value === "string") {
    return value;
  }

  if (Array.isArray(value)) {
    return value.map(formatApiError).filter(Boolean).join(" | ");
  }

  if (typeof value === "object") {
    const location = Array.isArray(value.loc) ? value.loc.join(".") : value.field || value.path || "";
    const message = value.msg || value.message || value.detail || value.error || "";

    if (location && message) {
      return `${location}: ${message}`;
    }

    if (message) {
      return formatApiError(message);
    }

    return Object.entries(value)
      .map(([key, entryValue]) => `${key}: ${formatApiError(entryValue)}`)
      .join(" | ");
  }

  return String(value);
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

function normalizeHealth(payload) {
  if (payload.checks) {
    const checks = payload.checks;
    const ami = checks.ami || {};
    return {
      api: { status: payload.status === "healthy" || payload.status === "ok" ? "ok" : payload.status, mode: payload.service || "api" },
      database: checks.database || { status: "inconnu" },
      ari: checks.ari || { status: "inconnu" },
      ami: {
        enabled: Boolean(ami.enabled),
        connected: Boolean(ami.running || ami.connected || ami.status === "connected"),
        host: ami.host,
        port: ami.port,
        status: ami.status || "inconnu",
      },
      scheduler: payload.scheduler || { status: "inconnu" },
      raw: payload,
    };
  }

  return payload;
}

function normalizeSchedulerJob(item) {
  if (item.scenario || item.schedule) {
    const scenario = item.scenario || {};
    const schedule = item.schedule || {};
    return {
      id: schedule.job_id || `scenario_${scenario.id}`,
      scenario_id: scenario.id,
      scenario_name: scenario.name,
      scenario_category: scenario.category,
      frequency: schedule.schedule_type || scenario.frequency,
      schedule_date: schedule.schedule_date || scenario.schedule_date || scenario.schedule?.schedule_date,
      last_run_at: schedule.last_run_at || scenario.last_run_at,
      last_run_status: schedule.last_run_status || scenario.last_run_status,
      last_run_error: schedule.last_run_error || scenario.last_run_error,
      next_run_time: schedule.next_run_at,
      active: Boolean(schedule.schedule_enabled || schedule.job_registered),
    };
  }

  return item;
}

function prepareScenarioPayload(payload) {
  const prepared = { ...payload };
  delete prepared.id;
  delete prepared.start_at;

  prepared.active = Boolean(Number(payload.active));

  if (payload.frequency && payload.start_at) {
    const startDate = new Date(payload.start_at);
    prepared.frequency = payload.frequency;
    prepared.schedule_enabled = true;
    prepared.schedule_type = payload.frequency;
    prepared.schedule_date = payload.start_at;
    prepared.schedule_time = Number.isNaN(startDate.getTime())
      ? null
      : `${String(startDate.getHours()).padStart(2, "0")}:${String(startDate.getMinutes()).padStart(2, "0")}`;
    prepared.schedule_timezone = "Europe/Paris";
  }

  return prepared;
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
