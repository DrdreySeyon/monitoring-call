document.addEventListener("DOMContentLoaded", () => {
  mountScenarioDrawer();
  bindTabs();
  bindFilters();
  bindHistoryFilters();
  bindScenarioForm();
  bindScenarioFilters();
  bindSchedulerControls();
  bindVoskFilters();
  document.getElementById("refreshBtn").addEventListener("click", loadData);
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
  state.selectedId = state.calls[0]?.id ?? null;
  applyFilters();
  renderHealth();
  renderScenarios();
  renderSchedulerJobs();
}
