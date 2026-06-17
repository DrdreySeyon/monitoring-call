function bindSchedulerControls() {
  const categorySelect = document.getElementById("schedulerCategorySelect");
  const scenarioSelect = document.getElementById("schedulerScenarioSelect");
  const frequencySelect = document.getElementById("schedulerFrequencySelect");
  const planButton = document.getElementById("schedulerPlanBtn");

  if (categorySelect) {
    categorySelect.addEventListener("change", () => {
      renderSchedulerScenarioOptions();
      renderSchedulerJobs();
    });
  }

  if (scenarioSelect) {
    scenarioSelect.addEventListener("change", renderSchedulerJobs);
  }

  if (frequencySelect) {
    frequencySelect.addEventListener("change", renderSchedulerJobs);
  }

  if (planButton) {
    planButton.addEventListener("click", handleSchedulerPlan);
  }
}

function renderSchedulerJobs() {
  const body = document.getElementById("schedulerJobsTable");
  if (!body) return;
  renderSchedulerControls();

  const category = document.getElementById("schedulerCategorySelect")?.value || "";
  const scenarioId = document.getElementById("schedulerScenarioSelect")?.value || "";
  const frequency = document.getElementById("schedulerFrequencySelect")?.value || "";
  const filteredJobs = state.schedulerJobs.filter((job) => {
    const scenario = getSchedulerJobScenario(job);
    const jobCategory = job.scenario_category || scenario?.category || "";
    const jobScenarioId = String(job.scenario_id || scenario?.id || "");
    const jobFrequency = job.frequency || scenario?.frequency || "";

    return (!category || jobCategory === category)
      && (!scenarioId || jobScenarioId === scenarioId)
      && (!frequency || jobFrequency === frequency);
  });

  body.innerHTML = filteredJobs
    .map(
      (job) => `
      <tr>
        <td>${schedulerScenarioCell(job)}</td>
        <td>${escapeHtml(formatFrequency(job.frequency))}</td>
        <td>${formatDate(job.next_run_time)}</td>
        <td><span class="chip ${job.active ? "chip-ok" : "chip-muted"}">${job.active ? "Actif" : "Pause"}</span></td>
        <td>
          <div class="row-actions">
            <button class="btn btn-small" type="button" data-job-action="run" data-id="${escapeHtml(job.id)}">Lancer</button>
            <button class="btn btn-small" type="button" data-job-action="toggle" data-id="${escapeHtml(job.id)}">${job.active ? "Pause" : "Reprise"}</button>
            <button class="btn btn-small" type="button" data-job-action="edit" data-id="${escapeHtml(job.id)}">Modifier</button>
          </div>
        </td>
      </tr>
    `,
    )
    .join("");

  body.querySelectorAll("[data-job-action]").forEach((button) => {
    button.addEventListener("click", () => handleSchedulerAction(button.dataset.jobAction, button.dataset.id));
  });
}

function renderSchedulerControls() {
  renderSchedulerCategoryOptions();
  renderSchedulerScenarioOptions();
}

function renderSchedulerCategoryOptions() {
  const select = document.getElementById("schedulerCategorySelect");
  if (!select) return;

  const currentValue = select.value;
  const categories = [...new Set(
    state.scenarios
      .map((scenario) => String(scenario.category || "").trim())
      .filter(Boolean),
  )].sort((a, b) => a.localeCompare(b, "fr", { sensitivity: "base" }));

  select.innerHTML = [
    `<option value="">Toutes les categories</option>`,
    ...categories.map((category) => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`),
  ].join("");
  select.value = categories.includes(currentValue) ? currentValue : "";
}

function renderSchedulerScenarioOptions() {
  const select = document.getElementById("schedulerScenarioSelect");
  if (!select) return;

  const currentValue = select.value;
  const category = document.getElementById("schedulerCategorySelect")?.value || "";
  const scenarios = state.scenarios
    .filter((scenario) => !category || scenario.category === category)
    .sort((a, b) => String(a.name || "").localeCompare(String(b.name || ""), "fr", { sensitivity: "base" }));

  select.innerHTML = [
    `<option value="">Tous les scenarios</option>`,
    ...scenarios.map((scenario) => `<option value="${escapeHtml(scenario.id)}">${escapeHtml(scenario.name || `Scenario #${scenario.id}`)}${scenario.category ? ` - ${escapeHtml(scenario.category)}` : ""}</option>`),
  ].join("");
  select.value = scenarios.some((scenario) => String(scenario.id) === currentValue) ? currentValue : "";
}

function getSchedulerJobScenario(job) {
  return state.scenarios.find((scenario) => String(scenario.id) === String(job.scenario_id));
}

function schedulerScenarioCell(job) {
  const scenario = getSchedulerJobScenario(job);
  const name = job.scenario_name || scenario?.name || `Scenario #${job.scenario_id || "-"}`;
  const category = job.scenario_category || scenario?.category || "-";
  return `<strong>${escapeHtml(name)}</strong><br><small class="muted">${escapeHtml(category)} - ${escapeHtml(job.id || "-")}</small>`;
}

function setSchedulerMessage(message, type) {
  const element = document.getElementById("schedulerFormMessage");
  if (!element) return;
  element.textContent = message;
  element.className = `form-message ${type === "ok" ? "is-ok" : "is-warn"}`;
}

async function handleSchedulerPlan() {
  const scenarioId = document.getElementById("schedulerScenarioSelect")?.value || "";
  const frequency = document.getElementById("schedulerFrequencySelect")?.value || "";
  const startAt = document.getElementById("schedulerStartAtInput")?.value || "";
  const scenario = state.scenarios.find((item) => String(item.id) === String(scenarioId));

  if (!scenarioId || !scenario) {
    setSchedulerMessage("Choisis un scenario reel avant de planifier.", "warn");
    return;
  }

  if (!frequency) {
    setSchedulerMessage("Choisis une frequence de planification.", "warn");
    return;
  }

  if (!startAt) {
    setSchedulerMessage("Choisis une date et heure de debut.", "warn");
    return;
  }

  try {
    const updated = await updateScenario(scenarioId, {
      frequency,
      start_at: startAt,
      active: Number(scenario.active) ? 1 : 0,
    });
    state.scenarios = state.scenarios.map((item) => (String(item.id) === String(scenarioId) ? updated : item));
    setSchedulerMessage(`Planification modifiee avec succes pour "${updated.name || scenario.name}".`, "ok");
    await loadData();
  } catch (error) {
    setSchedulerMessage(`Planification non appliquee: ${error.message || "erreur technique"}.`, "warn");
  }
}

async function handleSchedulerAction(action, id) {
  const job = state.schedulerJobs.find((item) => String(item.id) === String(id));
  if (!job) return;

  if (action === "edit") {
    const categorySelect = document.getElementById("schedulerCategorySelect");
    const scenarioSelect = document.getElementById("schedulerScenarioSelect");
    const frequencySelect = document.getElementById("schedulerFrequencySelect");
    const startInput = document.getElementById("schedulerStartAtInput");
    const scenario = getSchedulerJobScenario(job);

    if (categorySelect) categorySelect.value = job.scenario_category || scenario?.category || "";
    renderSchedulerScenarioOptions();
    if (scenarioSelect) scenarioSelect.value = String(job.scenario_id || scenario?.id || "");
    if (frequencySelect) frequencySelect.value = job.frequency || scenario?.frequency || "";
    if (startInput) {
      startInput.value = getSchedulerStartAt(job, scenario);
      startInput.focus();
    }
    setSchedulerMessage(`Planification de "${job.scenario_name || scenario?.name || id}" chargee en modification. Valide avec "Planifier" pour enregistrer.`, "warn");
    return;
  }

  if (action === "run") {
    try {
      await runSchedulerJob(id);
      setSchedulerMessage(`Execution demandee pour ${job.scenario_name || id}.`, "ok");
      await loadData();
    } catch (error) {
      setSchedulerMessage(`Execution non lancee pour ${job.scenario_name || id}: ${error.message || "erreur technique"}.`, "warn");
    }
    return;
  }

  if (action === "toggle") {
    try {
      const updated = await toggleSchedulerJob(id);
      state.schedulerJobs = state.schedulerJobs.map((item) => (String(item.id) === String(id) ? updated : item));
      setSchedulerMessage(`Statut de planification modifie pour ${job.scenario_name || id}.`, "ok");
    } catch (error) {
      state.schedulerJobs = state.schedulerJobs.map((item) =>
        String(item.id) === String(id) ? { ...item, active: !item.active } : item,
      );
    }
    renderSchedulerJobs();
  }
}

function getSchedulerStartAt(job, scenario) {
  return toDatetimeLocalValue(
    job.schedule_date
      || scenario?.schedule_date
      || scenario?.schedule?.schedule_date
      || job.next_run_time
      || scenario?.next_run_at
      || scenario?.schedule?.next_run_at,
  );
}
