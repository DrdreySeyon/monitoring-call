// Module de gestion des scénarios
const Scenarios = {
  items: [],
  isLoading: false,

  // Références DOM
  tableBody: null,
  countBadge: null,
  modal: null,
  form: null,
  modalTitle: null,

  init() {
    this.initElements();
    this.bindEvents();
    console.log("✓ Module Scenarios initialisé");
  },

  initElements() {
    this.tableBody = document.getElementById("scenarios-table-body");
    this.countBadge = document.getElementById("scenario-count");
    this.modal = document.getElementById("scenario-modal");
    this.form = document.getElementById("scenario-form");
    this.modalTitle = document.getElementById("modal-title");
  },

  bindEvents() {
    document.getElementById("open-create-modal")?.addEventListener("click", () => {
      this.openCreateModal();
    });

    document.getElementById("close-modal")?.addEventListener("click", () => {
      this.closeModal();
    });

    document.getElementById("cancel-modal")?.addEventListener("click", () => {
      this.closeModal();
    });

    this.modal?.addEventListener("click", (e) => {
      if (e.target === this.modal) {
        this.closeModal();
      }
    });

    this.form?.addEventListener("submit", async (e) => {
      e.preventDefault();
      await this.submitForm();
    });
  },

  async load() {
    if (this.isLoading) return;
    this.isLoading = true;

    try {
      Utils.setLoading(this.tableBody, true);

      const result = await Utils.apiGet(ENDPOINTS.SCENARIOS);

      if (!result.success) {
        throw new Error(result.error || "Erreur de chargement des scénarios");
      }

      const data = result.data;
      this.items = Array.isArray(data)
        ? data
        : Array.isArray(data.items)
        ? data.items
        : [];

      this.render();
    } catch (error) {
      console.error("Erreur chargement scénarios:", error);
      if (this.tableBody) {
        this.tableBody.innerHTML = `
          <tr>
            <td colspan="13">Erreur de chargement des scénarios</td>
          </tr>
        `;
      }
      Utils.showToast(error.message || MESSAGES.ERROR_SERVER, "error");
    } finally {
      Utils.setLoading(this.tableBody, false);
      this.isLoading = false;
    }
  },

  render() {
    if (!this.tableBody) return;

    if (this.countBadge) {
      this.countBadge.textContent = `${this.items.length} scénario(x)`;
    }

    if (this.items.length === 0) {
      this.tableBody.innerHTML = `
        <tr>
          <td colspan="13">${MESSAGES.NO_DATA}</td>
        </tr>
      `;
      return;
    }

    this.tableBody.innerHTML = this.items.map((scenario) => `
      <tr>
        <td>${Utils.escapeHtml(scenario.name || "-")}</td>
        <td>${Utils.escapeHtml(scenario.keyword || "-")}</td>
        <td>${Utils.escapeHtml(scenario.category || "-")}</td>
        <td>${Utils.escapeHtml(scenario.caller || "-")}</td>
        <td>${Utils.escapeHtml(scenario.callee || "-")}</td>
        <td>${Utils.escapeHtml(scenario.trunk || "-")}</td>
        <td>${Utils.escapeHtml(String(scenario.call_time_s ?? "-"))}</td>
        <td>${Utils.getDtmfChip(
          scenario.dtmf,
          scenario.time_s_before_dtmf,
          scenario.time_ms_between_dtmf
        )}</td>
        <td>${scenario.time_s_before_dtmf ?? "-"}${scenario.time_s_before_dtmf !== null && scenario.time_s_before_dtmf !== undefined ? " s" : ""}</td>
        <td>${scenario.time_ms_between_dtmf ?? "-"}${scenario.time_ms_between_dtmf !== null && scenario.time_ms_between_dtmf !== undefined ? " ms" : ""}</td>
        <td>${Utils.escapeHtml(scenario.frequency || "-")}</td>
        <td>
          ${scenario.active
            ? '<span class="pill pill-active">Actif</span>'
            : '<span class="pill pill-inactive">Inactif</span>'}
        </td>
        <td>
          <div class="cell-actions">
            <button class="btn btn-success" data-action="call" data-id="${scenario.id}">Appeler</button>
            <button class="btn btn-secondary" data-action="edit" data-id="${scenario.id}">Modifier</button>
            <button class="btn btn-warning" data-action="toggle" data-id="${scenario.id}">
              ${scenario.active ? "Désactiver" : "Activer"}
            </button>
            <button class="btn btn-danger" data-action="delete" data-id="${scenario.id}">Supprimer</button>
          </div>
        </td>
      </tr>
    `).join("");

    this.bindTableActions();
  },

  bindTableActions() {
    this.tableBody?.querySelectorAll("[data-action]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const action = btn.dataset.action;
        const id = Number(btn.dataset.id);

        if (!id) return;

        switch (action) {
          case "call":
            await this.callScenario(id);
            break;
          case "edit":
            this.openEditModal(id);
            break;
          case "toggle":
            await this.toggleScenario(id);
            break;
          case "delete":
            await this.deleteScenario(id);
            break;
        }
      });
    });
  },

  getById(id) {
    return this.items.find((item) => Number(item.id) === Number(id)) || null;
  },

  resetForm() {
    this.form?.reset();

    const idField = document.getElementById("scenario-id");
    if (idField) idField.value = "";

    const durationField = document.getElementById("expected_duration");
    const delayField = document.getElementById("dtmf_delay");
    const intervalField = document.getElementById("interval_ms");
    const activeField = document.getElementById("is_active");

    if (durationField) durationField.value = CONFIG.CALL_TIME_DEFAULT;
    if (delayField) delayField.value = CONFIG.DTMF_DEFAULT_DELAY;
    if (intervalField) intervalField.value = CONFIG.DTMF_DEFAULT_INTERVAL;
    if (activeField) activeField.checked = true;
  },

  openCreateModal() {
    this.resetForm();
    if (this.modalTitle) this.modalTitle.textContent = "Nouveau scénario";
    this.modal?.classList.remove("hidden");
  },

  openEditModal(id) {
    const scenario = this.getById(id);
    if (!scenario) {
      Utils.showToast("Scénario introuvable", "error");
      return;
    }

    this.resetForm();

    if (this.modalTitle) this.modalTitle.textContent = "Modifier scénario";

    document.getElementById("scenario-id").value = scenario.id ?? "";
    document.getElementById("task_name").value = scenario.name ?? "";
    document.getElementById("keyword").value = scenario.keyword ?? "";
    document.getElementById("category").value = scenario.category ?? "";
    document.getElementById("caller").value = scenario.caller ?? "";
    document.getElementById("callee").value = scenario.callee ?? "";
    document.getElementById("trunk").value = scenario.trunk ?? "";
    document.getElementById("expected_duration").value = scenario.call_time_s ?? CONFIG.CALL_TIME_DEFAULT;
    document.getElementById("dtmf_digits").value = scenario.dtmf ?? "";
    document.getElementById("dtmf_delay").value = scenario.time_s_before_dtmf ?? CONFIG.DTMF_DEFAULT_DELAY;
    document.getElementById("interval_ms").value = scenario.time_ms_between_dtmf ?? CONFIG.DTMF_DEFAULT_INTERVAL;
    document.getElementById("frequency").value = scenario.frequency ?? "";
    document.getElementById("is_active").checked = !!scenario.active;

    this.modal?.classList.remove("hidden");
  },

  closeModal() {
    this.modal?.classList.add("hidden");
    this.resetForm();
  },

  buildPayloadFromForm() {
    const name = document.getElementById("task_name")?.value.trim() || "";
    const keyword = document.getElementById("keyword")?.value.trim() || "";
    const category = document.getElementById("category")?.value.trim() || "";
    const caller = document.getElementById("caller")?.value.trim() || "";
    const callee = document.getElementById("callee")?.value.trim() || "";
    const trunk = document.getElementById("trunk")?.value.trim() || "";
    const callTime = Number(document.getElementById("expected_duration")?.value || CONFIG.CALL_TIME_DEFAULT);
    const dtmf = document.getElementById("dtmf_digits")?.value.trim() || "";
    const dtmfDelay = document.getElementById("dtmf_delay")?.value;
    const dtmfInterval = document.getElementById("interval_ms")?.value;
    const frequency = document.getElementById("frequency")?.value || null;
    const active = !!document.getElementById("is_active")?.checked;

    if (!name) throw new Error("Le nom du scénario est obligatoire");
    if (!keyword) throw new Error("Le mot-clé est obligatoire");
    if (!category) throw new Error("La catégorie est obligatoire");
    if (!Utils.validatePhoneNumber(caller)) throw new Error("Numéro appelant invalide");
    if (!Utils.validatePhoneNumber(callee)) throw new Error("Numéro appelé invalide");
    if (!trunk) throw new Error("Le trunk SIP est obligatoire");
    if (!Utils.validateCallTime(callTime)) throw new Error(MESSAGES.CALL_TIME_INVALID);
    if (!Utils.validateDtmfSequence(dtmf)) throw new Error(MESSAGES.DTMF_INVALID);

    const parsedDelay = dtmfDelay === "" ? null : Number(dtmfDelay);
    const parsedInterval = dtmfInterval === "" ? null : Number(dtmfInterval);

    if (!Utils.validateDtmfParams(dtmf, parsedDelay, callTime)) {
      throw new Error(MESSAGES.DTMF_DELAY_ERROR);
    }

    return {
      name,
      keyword,
      category,
      caller,
      callee,
      trunk,
      call_time_s: callTime,
      dtmf: dtmf || null,
      time_s_before_dtmf: parsedDelay,
      time_ms_between_dtmf: parsedInterval,
      frequency,
      active
    };
  },

  async submitForm() {
    try {
      const id = document.getElementById("scenario-id")?.value;
      const payload = this.buildPayloadFromForm();

      let result;
      if (id) {
        result = await Utils.apiPatch(`${ENDPOINTS.SCENARIOS}/${id}`, payload);
      } else {
        result = await Utils.apiPost(ENDPOINTS.SCENARIOS, payload);
      }

      if (!result.success) {
        throw new Error(result.error || MESSAGES.ERROR_SERVER);
      }

      Utils.showToast(MESSAGES.SUCCESS_SAVE, "success");
      this.closeModal();
      await this.load();
    } catch (error) {
      console.error("Erreur sauvegarde scénario:", error);
      Utils.showToast(error.message || MESSAGES.ERROR_SERVER, "error");
    }
  },

  async deleteScenario(id) {
    const ok = await Utils.confirmAction("Voulez-vous supprimer ce scénario ?", "Suppression");
    if (!ok) return;

    try {
      const result = await Utils.apiDelete(`${ENDPOINTS.SCENARIOS}/${id}`);

      if (!result.success) {
        throw new Error(result.error || MESSAGES.ERROR_SERVER);
      }

      Utils.showToast(MESSAGES.SUCCESS_DELETE, "success");
      await this.load();
    } catch (error) {
      console.error("Erreur suppression scénario:", error);
      Utils.showToast(error.message || MESSAGES.ERROR_SERVER, "error");
    }
  },

  async toggleScenario(id) {
    try {
      const result = await Utils.apiPost(`${ENDPOINTS.SCENARIOS}/${id}/toggle`);

      if (!result.success) {
        throw new Error(result.error || MESSAGES.ERROR_SERVER);
      }

      Utils.showToast(result.data?.message || "Statut modifié", "success");
      await this.load();
    } catch (error) {
      console.error("Erreur toggle scénario:", error);
      Utils.showToast(error.message || MESSAGES.ERROR_SERVER, "error");
    }
  },

  async callScenario(id) {
    try {
      const result = await Utils.apiPost(`${ENDPOINTS.SCENARIOS}/${id}/call`);

      if (!result.success) {
        throw new Error(result.error || MESSAGES.ERROR_SERVER);
      }

      Utils.showToast(result.data?.message || "Appel lancé", "success");

      if (window.History && typeof window.History.load === "function") {
        await window.History.load();
      }

      if (window.Stats && typeof window.Stats.load === "function") {
        await window.Stats.load();
      }
    } catch (error) {
      console.error("Erreur appel scénario:", error);
      Utils.showToast(error.message || MESSAGES.ERROR_SERVER, "error");
    }
  },

  async onTabActivated() {
    await this.load();
  }
};

// Export global
window.Scenarios = Scenarios;

// Compatibilité ancienne approche
window.loadScenarios = async function () {
  if (window.Scenarios && typeof window.Scenarios.load === "function") {
    await window.Scenarios.load();
  }
};

window.openModal = function () {
  window.Scenarios?.openCreateModal();
};

window.closeModal = function () {
  window.Scenarios?.closeModal();
};

window.editScenario = function (id) {
  window.Scenarios?.openEditModal(id);
};

window.callScenario = async function (id) {
  await window.Scenarios?.callScenario(id);
};

window.toggleScenario = async function (id) {
  await window.Scenarios?.toggleScenario(id);
};

window.deleteScenario = async function (id) {
  await window.Scenarios?.deleteScenario(id);
};

window.saveScenario = async function (event) {
  event?.preventDefault?.();
  await window.Scenarios?.submitForm();
};