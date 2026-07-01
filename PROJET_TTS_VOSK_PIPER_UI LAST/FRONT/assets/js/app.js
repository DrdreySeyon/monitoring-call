document.addEventListener("DOMContentLoaded", () => {
  mountScenarioDrawer();
  bindTabs();
  bindFilters();
  bindHistoryFilters();
  bindScenarioForm();
  bindScenarioFilters();
  bindScenarioImport();
  bindSchedulerControls();
  bindVoskFilters();
  bindRefreshControls();
  document.getElementById("reloadScenariosBtn").addEventListener("click", loadScenarios);
  activateInitialTab();
  loadData();
});

function mountScenarioDrawer() {
  const form = document.getElementById("scenarioForm");
  const panel = form?.closest(".panel");
  if (!panel) return;
  panel.classList.add("scenario-drawer");
  document.querySelector(".app-shell")?.appendChild(panel);
}

async function loadData() {
  if (state.isRefreshing) return;
  const previousSelectedId = state.selectedId;
  setRefreshState(true);
  try {
    const [health, calls, scenarios, schedulerJobs] = await Promise.all([
      fetchHealth(),
      fetchCalls(),
      fetchScenarios(),
      fetchSchedulerJobs(),
    ]);
    state.health = health;
    state.calls = calls.length ? calls : sampleCalls;
    state.scenarios = scenarios.length ? scenarios : sampleScenarios();
    state.schedulerJobs = schedulerJobs.length ? schedulerJobs : sampleSchedulerJobs();
    state.selectedId = state.calls.some((call) => String(call.id) === String(previousSelectedId))
      ? previousSelectedId
      : state.calls[0]?.id ?? null;
    state.lastRefreshAt = new Date();
    applyFilters();
    renderHealth();
    renderScenarios();
    renderSchedulerJobs();
    setRefreshMessage("ok");
  } catch (error) {
    setRefreshMessage("warn", error.message || "Erreur de rafraichissement");
  } finally {
    setRefreshState(false);
  }
}

function bindRefreshControls() {
  document.getElementById("refreshBtn").addEventListener("click", loadData);
  document.getElementById("autoRefreshSelect").addEventListener("change", (event) => {
    const seconds = Number(event.target.value || 0);
    if (state.refreshTimer) {
      window.clearInterval(state.refreshTimer);
      state.refreshTimer = null;
    }
    if (seconds > 0) {
      state.refreshTimer = window.setInterval(loadData, seconds * 1000);
    }
  });
}

function setRefreshState(isRefreshing) {
  state.isRefreshing = isRefreshing;
  const button = document.getElementById("refreshBtn");
  if (button) {
    button.disabled = isRefreshing;
    button.textContent = isRefreshing ? "Rafraichissement..." : "Rafraichir";
  }
}

function setRefreshMessage(type, message = "") {
  const badge = document.getElementById("lastRefreshBadge");
  if (!badge) return;
  if (type === "warn") {
    badge.textContent = message || "Rafraichissement incomplet";
    badge.className = "pill pill-warn";
    return;
  }
  badge.textContent = state.lastRefreshAt ? `Maj ${state.lastRefreshAt.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}` : "Jamais rafraichi";
  badge.className = "pill pill-info";
}
