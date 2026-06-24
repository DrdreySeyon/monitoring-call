function bindScenarioForm() {
  const form = document.getElementById("scenarioForm");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const dtmfDelay = formData.get("time_s_before_dtmf");
    const dtmfInterval = formData.get("time_ms_between_dtmf");
    const payload = {
      id: formData.get("id") || null,
      name: formData.get("name"),
      category: String(formData.get("category") || "").trim(),
      keyword: formData.get("keyword"),
      tts: String(formData.get("tts") || "").trim() || null,
      caller: formData.get("caller"),
      callee: formData.get("callee"),
      trunk: formData.get("trunk"),
      call_time_s: Number(formData.get("call_time_s") || 30),
      ring_timeout_s: Number(formData.get("ring_timeout_s") || 60),
      dtmf: formData.get("dtmf") || null,
      time_s_before_dtmf: dtmfDelay === null || dtmfDelay === "" ? null : Number(dtmfDelay),
      time_ms_between_dtmf: dtmfInterval === null || dtmfInterval === "" ? 3000 : Number(dtmfInterval),
      frequency: formData.get("frequency") || null,
      start_at: formData.get("start_at") || null,
      active: formData.get("active") ? 1 : 0,
    };

    try {
      const created = payload.id ? await updateScenario(payload.id, payload) : await createScenario(payload);
      state.scenarios = [created, ...state.scenarios.filter((scenario) => scenario.id !== created.id)];
      renderScenarios();
      resetScenarioForm();
      setFormMessage(payload.id ? `Scenario "${created.name || payload.name}" modifie avec succes.` : `Scenario "${created.name || payload.name}" cree avec succes.`, "ok");
    } catch (error) {
      if (payload.id) {
        setFormMessage(`Scenario "${payload.name}" non modifie: ${error.message || "erreur technique"}.`, "warn");
        return;
      }
      const created = payload.id ? { ...payload, id: Number(payload.id) || payload.id } : { ...payload, id: Date.now(), created_at: new Date().toISOString() };
      state.scenarios = [created, ...state.scenarios.filter((scenario) => String(scenario.id) !== String(created.id))];
      renderScenarios();
      resetScenarioForm();
      setFormMessage(`Scenario "${created.name || payload.name}" ajoute.`, "warn");
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
  renderScenarioCategoryOptions();
  const query = document.getElementById("scenarioSearchInput").value.trim().toLowerCase();
  const status = document.getElementById("scenarioStatusFilter").value;
  const frequency = document.getElementById("scenarioFrequencyFilter").value;
  state.filteredScenarios = state.scenarios.filter((scenario) => {
    const haystack = [
      scenario.name,
      scenario.category,
      scenario.keyword,
      scenario.tts,
      scenario.caller,
      scenario.callee,
      scenario.trunk,
      scenario.dtmf,
      scenario.time_s_before_dtmf,
      scenario.time_ms_between_dtmf,
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
          ${kvInline("TTS Piper", scenario.tts || "-")}
          ${kvInline("Appel", `${scenario.caller || "-"} vers ${scenario.callee || "-"}`)}
          ${kvInline("Trunk", scenario.trunk || "-")}
          ${kvInline("Duree", formatDuration(scenario.call_time_s))}
          ${kvInline("Timeout sonnerie", formatDuration(scenario.ring_timeout_s || 60))}
          ${kvInline("DTMF", scenario.dtmf || "-")}
          ${kvInline("Delai DTMF", scenario.time_s_before_dtmf != null ? formatDuration(scenario.time_s_before_dtmf) : "-")}
          ${kvInline("Intervalle DTMF", scenario.time_ms_between_dtmf != null ? `${scenario.time_ms_between_dtmf} ms` : "-")}
          ${kvInline("Frequence", formatFrequency(scenario.frequency))}
        </div>
        <div class="row-actions">
          <button class="btn btn-small" type="button" data-scenario-action="run" data-id="${escapeHtml(scenario.id)}">Lancer</button>
          <button class="btn btn-small" type="button" data-scenario-action="check" data-id="${escapeHtml(scenario.id)}">Tester config</button>
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

function renderScenarioCategoryOptions() {
  const datalist = document.getElementById("scenarioCategoryOptions");
  if (!datalist) return;

  const categories = [...new Set(
    state.scenarios
      .map((scenario) => String(scenario.category || "").trim())
      .filter(Boolean),
  )].sort((a, b) => a.localeCompare(b, "fr", { sensitivity: "base" }));

  datalist.innerHTML = categories
    .map((category) => `<option value="${escapeHtml(category)}"></option>`)
    .join("");
}

function setFormMessage(message, type) {
  const element = document.getElementById("scenarioFormMessage");
  element.textContent = message;
  element.className = `form-message ${type === "ok" ? "is-ok" : "is-warn"}`;
}

function renderScenarioConfigChecklist(result) {
  const container = document.getElementById("scenarioConfigChecklist");
  if (!container) return;
  const checks = result?.checks || [];
  container.innerHTML = checks
    .map((check) => `
      <div class="check-row">
        <strong>${escapeHtml(check.name || "-")}</strong>
        <span>${escapeHtml(check.detail || "-")}</span>
        <span class="chip ${check.status === "ok" ? "chip-ok" : "chip-ko"}">${check.status === "ok" ? "OK" : "KO"}</span>
      </div>
    `)
    .join("");
}

async function handleScenarioAction(action, id) {
  if (action === "run") {
    try {
      const result = await runScenario(id);
      setFormMessage(formatScenarioRunMessage(id, result), isRunResultOk(result) ? "ok" : "warn");
      await loadData();
    } catch (error) {
      setFormMessage(`Scenario #${id} non lance: ${error.message || "erreur technique"}.`, "warn");
    }
    return;
  }

  if (action === "check") {
    try {
      const result = await checkScenarioConfig(id);
      renderScenarioConfigChecklist(result);
      setFormMessage(`Configuration de "${result.scenario?.name || `Scenario #${id}`}" verifiee.`, result.status === "ok" ? "ok" : "warn");
    } catch (error) {
      setFormMessage(`Configuration non verifiee: ${error.message || "erreur technique"}.`, "warn");
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
      // La suppression reste visible immediatement dans la liste.
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
  form.elements.tts.value = scenario.tts || "";
  form.elements.caller.value = scenario.caller || "";
  form.elements.callee.value = scenario.callee || "";
  form.elements.trunk.value = scenario.trunk || "";
  form.elements.call_time_s.value = scenario.call_time_s || 30;
  form.elements.ring_timeout_s.value = scenario.ring_timeout_s || 60;
  form.elements.dtmf.value = scenario.dtmf || "";
  form.elements.time_s_before_dtmf.value = scenario.time_s_before_dtmf ?? "";
  form.elements.time_ms_between_dtmf.value = scenario.time_ms_between_dtmf ?? 3000;
  form.elements.frequency.value = scenario.frequency || scenario.schedule?.schedule_type || "";
  form.elements.start_at.value = getScenarioStartAt(scenario);
  form.elements.active.checked = Boolean(Number(scenario.active));
  document.getElementById("scenarioSubmitBtn").textContent = "Modifier le scenario";
  setFormMessage(`Scenario "${scenario.name}" charge en modification. Valide avec "Modifier le scenario" pour enregistrer.`, "warn");
}

function resetScenarioForm() {
  const form = document.getElementById("scenarioForm");
  form.elements.id.value = "";
  form.elements.ring_timeout_s.value = form.elements.ring_timeout_s.value || 60;
  form.elements.tts.value = "";
  form.elements.time_s_before_dtmf.value = form.elements.time_s_before_dtmf.value || 4;
  form.elements.time_ms_between_dtmf.value = form.elements.time_ms_between_dtmf.value || 3000;
  document.getElementById("scenarioSubmitBtn").textContent = "Creer le scenario";
}

function getScenarioStartAt(scenario) {
  return toDatetimeLocalValue(
    scenario.start_at
      || scenario.schedule_date
      || scenario.schedule?.schedule_date
      || scenario.schedule?.next_run_at
      || scenario.next_run_at,
  );
}

function isRunResultOk(result) {
  const status = String(result?.status || "").toLowerCase();
  return !["failed", "error", "skipped"].includes(status);
}

function formatScenarioRunMessage(id, result) {
  const status = result?.status || "demande envoyee";
  const callId = result?.call_id || result?.call?.id || result?.id;
  const channel = result?.channel_id || result?.channel || result?.ari_response?.id;
  const message = result?.message || result?.error;

  if (!isRunResultOk(result)) {
    return `Scenario #${id}: ${status}${message ? ` - ${message}` : ""}.`;
  }

  if (callId || channel) {
    return `Scenario #${id}: appel demande (${callId ? `appel ${callId}` : ""}${callId && channel ? ", " : ""}${channel ? `channel ${channel}` : ""}). Consulte l'historique pour le resultat trunk/AMI.`;
  }

  return `Scenario #${id}: demande envoyee a ARI. Consulte l'historique pour confirmer si le mobile a sonne.`;
}
