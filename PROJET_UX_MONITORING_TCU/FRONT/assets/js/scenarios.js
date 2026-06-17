function bindScenarioForm() {
  const form = document.getElementById("scenarioForm");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const payload = {
      id: formData.get("id") || null,
      name: formData.get("name"),
      category: formData.get("category"),
      keyword: formData.get("keyword"),
      caller: formData.get("caller"),
      callee: formData.get("callee"),
      trunk: formData.get("trunk"),
      call_time_s: Number(formData.get("call_time_s") || 30),
      dtmf: formData.get("dtmf") || null,
      frequency: formData.get("frequency") || null,
      start_at: formData.get("start_at") || null,
      active: formData.get("active") ? 1 : 0,
    };

    try {
      const created = payload.id ? await updateScenario(payload.id, payload) : await createScenario(payload);
      state.scenarios = [created, ...state.scenarios.filter((scenario) => scenario.id !== created.id)];
      renderScenarios();
      resetScenarioForm();
      setFormMessage(payload.id ? "Scenario modifie dans le backend UX." : "Scenario cree dans le backend UX.", "ok");
    } catch (error) {
      const created = payload.id ? { ...payload, id: Number(payload.id) || payload.id } : { ...payload, id: Date.now(), created_at: new Date().toISOString() };
      state.scenarios = [created, ...state.scenarios.filter((scenario) => String(scenario.id) !== String(created.id))];
      renderScenarios();
      resetScenarioForm();
      setFormMessage(payload.id ? "Scenario modifie en mode demo local." : "Scenario ajoute en mode demo local.", "warn");
    }
  });

  form.addEventListener("reset", () => {
    window.setTimeout(resetScenarioForm, 0);
  });
}

function bindScenarioFilters() {
  document.getElementById("scenarioSearchInput").addEventListener("input", renderScenarios);
  document.getElementById("scenarioStatusFilter").addEventListener("change", renderScenarios);
  document.getElementById("scenarioFrequencyFilter").addEventListener("change", renderScenarios);
}

function renderScenarios() {
  const list = document.getElementById("scenariosList");
  if (!list) return;
  const query = document.getElementById("scenarioSearchInput").value.trim().toLowerCase();
  const status = document.getElementById("scenarioStatusFilter").value;
  const frequency = document.getElementById("scenarioFrequencyFilter").value;
  state.filteredScenarios = state.scenarios.filter((scenario) => {
    const haystack = [
      scenario.name,
      scenario.category,
      scenario.keyword,
      scenario.caller,
      scenario.callee,
      scenario.trunk,
      scenario.dtmf,
      scenario.frequency,
    ]
      .join(" ")
      .toLowerCase();
    const active = Boolean(Number(scenario.active));
    const statusOk = !status || (status === "active" ? active : !active);
    const frequencyOk = !frequency || scenario.frequency === frequency;
    return (!query || haystack.includes(query)) && statusOk && frequencyOk;
  });

  list.innerHTML = state.filteredScenarios
    .map(
      (scenario) => `
      <article class="scenario-card">
        <div class="scenario-card-head">
          <div>
            <strong>${escapeHtml(scenario.name || "-")}</strong>
            <span>${escapeHtml(scenario.category || "-")}</span>
          </div>
          <span class="chip ${Number(scenario.active) ? "chip-ok" : "chip-muted"}">${Number(scenario.active) ? "Actif" : "Inactif"}</span>
        </div>
        <div class="scenario-meta">
          ${kvInline("Mots-cles", scenario.keyword || "-")}
          ${kvInline("Appel", `${scenario.caller || "-"} vers ${scenario.callee || "-"}`)}
          ${kvInline("Trunk", scenario.trunk || "-")}
          ${kvInline("Duree", formatDuration(scenario.call_time_s))}
          ${kvInline("DTMF", scenario.dtmf || "-")}
          ${kvInline("Frequence", formatFrequency(scenario.frequency))}
        </div>
        <div class="row-actions">
          <button class="btn btn-small" type="button" data-scenario-action="run" data-id="${escapeHtml(scenario.id)}">Lancer</button>
          <button class="btn btn-small" type="button" data-scenario-action="edit" data-id="${escapeHtml(scenario.id)}">Modifier</button>
          <button class="btn btn-small" type="button" data-scenario-action="toggle" data-id="${escapeHtml(scenario.id)}">${Number(scenario.active) ? "Desactiver" : "Activer"}</button>
          <button class="btn btn-small" type="button" data-scenario-action="delete" data-id="${escapeHtml(scenario.id)}">Supprimer</button>
        </div>
      </article>
    `,
    )
    .join("");

  list.querySelectorAll("[data-scenario-action]").forEach((button) => {
    button.addEventListener("click", () => handleScenarioAction(button.dataset.scenarioAction, button.dataset.id));
  });
}

function setFormMessage(message, type) {
  const element = document.getElementById("scenarioFormMessage");
  element.textContent = message;
  element.className = `form-message ${type === "ok" ? "is-ok" : "is-warn"}`;
}

async function handleScenarioAction(action, id) {
  if (action === "run") {
    try {
      await runScenario(id);
      setFormMessage(`Scenario #${id} lance.`, "ok");
    } catch (error) {
      setFormMessage(`Scenario #${id} lance en mode demo local.`, "warn");
    }
    return;
  }

  if (action === "edit") {
    const scenario = state.scenarios.find((item) => String(item.id) === String(id));
    if (scenario) fillScenarioForm(scenario);
    return;
  }

  if (action === "toggle") {
    try {
      const updated = await toggleScenario(id);
      state.scenarios = state.scenarios.map((scenario) =>
        String(scenario.id) === String(id) ? { ...scenario, ...updated } : scenario,
      );
    } catch (error) {
      state.scenarios = state.scenarios.map((scenario) =>
        String(scenario.id) === String(id) ? { ...scenario, active: Number(scenario.active) ? 0 : 1 } : scenario,
      );
    }
    renderScenarios();
    return;
  }

  if (action === "delete") {
    try {
      await deleteScenario(id);
    } catch (error) {
      // Le mode demo local supprime quand meme l'element cote front.
    }
    state.scenarios = state.scenarios.filter((scenario) => String(scenario.id) !== String(id));
    renderScenarios();
  }
}

function fillScenarioForm(scenario) {
  const form = document.getElementById("scenarioForm");
  form.elements.id.value = scenario.id || "";
  form.elements.name.value = scenario.name || "";
  form.elements.category.value = scenario.category || "";
  form.elements.keyword.value = scenario.keyword || "";
  form.elements.caller.value = scenario.caller || "";
  form.elements.callee.value = scenario.callee || "";
  form.elements.trunk.value = scenario.trunk || "";
  form.elements.call_time_s.value = scenario.call_time_s || 30;
  form.elements.dtmf.value = scenario.dtmf || "";
  form.elements.frequency.value = scenario.frequency || "";
  form.elements.start_at.value = scenario.start_at || "";
  form.elements.active.checked = Boolean(Number(scenario.active));
  document.getElementById("scenarioSubmitBtn").textContent = "Modifier le scenario";
  setFormMessage(`Modification du scenario ${scenario.name}`, "warn");
}

function resetScenarioForm() {
  const form = document.getElementById("scenarioForm");
  form.elements.id.value = "";
  document.getElementById("scenarioSubmitBtn").textContent = "Creer le scenario";
}
