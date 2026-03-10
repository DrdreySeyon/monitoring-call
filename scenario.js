const Scenarios = {
  scenarios: [],

  init() {
    this.initElements();
    this.bindEvents();
    this.load();
  },

  initElements() {
    this.tableBody = document.getElementById("scenarios-table-body");
    this.countBadge = document.getElementById("scenario-count");

    this.modal = document.getElementById("scenario-modal");
    this.form = document.getElementById("scenario-form");
    this.modalTitle = document.getElementById("modal-title");

    this.exportBtn = document.getElementById("export-scenarios-btn");
    this.importBtn = document.getElementById("import-scenarios-btn");
    this.importFileInput = document.getElementById("import-scenarios-file");

    // Champs du formulaire
    this.scenarioIdField = document.getElementById("scenario-id");
    this.nameField = document.getElementById("task_name");
    this.keywordField = document.getElementById("keyword");
    this.categoryField = document.getElementById("category");
    this.callerField = document.getElementById("caller");
    this.calleeField = document.getElementById("callee");
    this.trunkField = document.getElementById("trunk");
    this.callTimeField = document.getElementById("expected_duration");
    this.dtmfField = document.getElementById("dtmf_digits");
    this.dtmfDelayField = document.getElementById("dtmf_delay");
    this.dtmfIntervalField = document.getElementById("interval_ms");
    this.frequencyField = document.getElementById("frequency");
    this.activeField = document.getElementById("is_active");
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

    this.exportBtn?.addEventListener("click", async () => {
      await this.exportScenarios();
    });

    this.importBtn?.addEventListener("click", () => {
      this.importFileInput?.click();
    });

    this.importFileInput?.addEventListener("change", async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;

      await this.importScenarios(file);
      e.target.value = "";
    });
  },

  async load() {
    try {
      const data = await API.get(ENDPOINTS.SCENARIOS);
      this.scenarios = Array.isArray(data) ? data : [];
      this.render();
    } catch (error) {
      console.error("Erreur chargement scénarios:", error);
      Utils.showToast("Erreur chargement scénarios", "error");
    }
  },

  render() {
    if (!this.tableBody) return;

    if (!this.scenarios.length) {
      this.tableBody.innerHTML = `
        <tr>
          <td colspan="13" class="text-center">Aucun scénario</td>
        </tr>
      `;

      if (this.countBadge) this.countBadge.textContent = "0 scénario(x)";
      return;
    }

    this.tableBody.innerHTML = this.scenarios.map((s) => {
      return `
      <tr>
        <td>${Utils.escapeHtml(s.name || "-")}</td>
        <td>${Utils.escapeHtml(s.keyword || "-")}</td>
        <td>${Utils.escapeHtml(s.category || "-")}</td>
        <td>${Utils.escapeHtml(s.caller || "-")}</td>
        <td>${Utils.escapeHtml(s.callee || "-")}</td>
        <td>${Utils.escapeHtml(s.trunk || "-")}</td>
        <td>${s.call_time_s ?? "-"}</td>
        <td>${Utils.getDtmfChip(s.dtmf, s.time_s_before_dtmf, s.time_ms_between_dtmf)}</td>
        <td>${s.time_s_before_dtmf ?? "-"}</td>
        <td>${s.time_ms_between_dtmf ?? "-"}</td>
        <td>${Utils.escapeHtml(s.frequency || "-")}</td>
        <td>
          ${s.active
            ? '<span class="pill pill-active">Actif</span>'
            : '<span class="pill pill-inactive">Inactif</span>'}
        </td>
        <td>
          <div class="row-actions">
            <button class="btn btn-primary btn-sm" onclick="Scenarios.call(${s.id})" title="Appeler">▶</button>
            <button class="btn btn-secondary btn-sm" onclick="Scenarios.edit(${s.id})" title="Modifier">✏</button>
            <button class="btn btn-ghost btn-sm" onclick="Scenarios.toggle(${s.id})" title="${s.active ? "Désactiver" : "Activer"}">
              ${s.active ? "⏸" : "✓"}
            </button>
            <button class="btn btn-danger btn-sm" onclick="Scenarios.remove(${s.id})" title="Supprimer">🗑</button>
          </div>
        </td>
      </tr>
      `;
    }).join("");

    if (this.countBadge) {
      this.countBadge.textContent = `${this.scenarios.length} scénario(x)`;
    }
  },

  resetForm() {
    this.form?.reset();

    if (this.scenarioIdField) this.scenarioIdField.value = "";
    if (this.callTimeField) this.callTimeField.value = CONFIG.CALL_TIME_DEFAULT ?? 30;
    if (this.dtmfDelayField) this.dtmfDelayField.value = CONFIG.DTMF_DEFAULT_DELAY ?? 3;
    if (this.dtmfIntervalField) this.dtmfIntervalField.value = CONFIG.DTMF_DEFAULT_INTERVAL ?? 3000;
    if (this.activeField) this.activeField.checked = true;
  },

  openCreateModal() {
    if (!this.modal) return;

    this.resetForm();
    this.modalTitle.textContent = "Créer un scénario";
    this.modal.classList.remove("hidden");
  },

  closeModal() {
    if (!this.modal) return;
    this.modal.classList.add("hidden");
  },

  edit(id) {
    const s = this.scenarios.find((x) => Number(x.id) === Number(id));
    if (!s) return;

    this.modalTitle.textContent = "Modifier scénario";

    if (this.scenarioIdField) this.scenarioIdField.value = s.id ?? "";
    if (this.nameField) this.nameField.value = s.name ?? "";
    if (this.keywordField) this.keywordField.value = s.keyword ?? "";
    if (this.categoryField) this.categoryField.value = s.category ?? "";
    if (this.callerField) this.callerField.value = s.caller ?? "";
    if (this.calleeField) this.calleeField.value = s.callee ?? "";
    if (this.trunkField) this.trunkField.value = s.trunk ?? "";
    if (this.callTimeField) this.callTimeField.value = s.call_time_s ?? 30;
    if (this.dtmfField) this.dtmfField.value = s.dtmf ?? "";
    if (this.dtmfDelayField) this.dtmfDelayField.value = s.time_s_before_dtmf ?? "";
    if (this.dtmfIntervalField) this.dtmfIntervalField.value = s.time_ms_between_dtmf ?? "";
    if (this.frequencyField) this.frequencyField.value = s.frequency ?? "";
    if (this.activeField) this.activeField.checked = !!s.active;

    this.modal.classList.remove("hidden");
  },

  buildPayload() {
    const name = this.nameField?.value.trim() || "";
    const keyword = this.keywordField?.value.trim() || "";
    const category = this.categoryField?.value.trim() || "";
    const caller = this.callerField?.value.trim() || "";
    const callee = this.calleeField?.value.trim() || "";
    const trunk = this.trunkField?.value.trim() || "";
    const callTime = Number(this.callTimeField?.value || 30);
    const dtmf = this.dtmfField?.value.trim() || "";
    const delayValue = this.dtmfDelayField?.value;
    const intervalValue = this.dtmfIntervalField?.value;
    const frequency = this.frequencyField?.value || null;
    const active = !!this.activeField?.checked;

    if (!name) throw new Error("Le nom du scénario est obligatoire");
    if (!keyword) throw new Error("Le mot-clé est obligatoire");
    if (!category) throw new Error("La catégorie est obligatoire");
    if (!Utils.validatePhoneNumber(caller)) throw new Error("Numéro appelant invalide");
    if (!Utils.validatePhoneNumber(callee)) throw new Error("Numéro appelé invalide");
    if (!trunk) throw new Error("Le trunk SIP est obligatoire");
    if (!Utils.validateCallTime(callTime)) throw new Error(MESSAGES.CALL_TIME_INVALID);
    if (!Utils.validateDtmfSequence(dtmf)) throw new Error(MESSAGES.DTMF_INVALID);

    const parsedDelay = delayValue === "" ? null : Number(delayValue);
    const parsedInterval = intervalValue === "" ? null : Number(intervalValue);

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
    const id = this.scenarioIdField?.value || "";

    try {
      const payload = this.buildPayload();

      if (id) {
        await API.patch(`${ENDPOINTS.SCENARIOS}/${id}`, payload);
        Utils.showToast("Scénario modifié", "success");
      } else {
        await API.post(ENDPOINTS.SCENARIOS, payload);
        Utils.showToast("Scénario créé", "success");
      }

      this.closeModal();
      await this.load();
    } catch (error) {
      console.error(error);
      Utils.showToast(error.message || "Erreur", "error");
    }
  },

  async remove(id) {
    const ok = await Utils.confirmAction("Supprimer ce scénario ?");
    if (!ok) return;

    try {
      await API.delete(`${ENDPOINTS.SCENARIOS}/${id}`);
      Utils.showToast("Scénario supprimé", "success");
      await this.load();
    } catch (error) {
      Utils.showToast(error.message || "Erreur suppression", "error");
    }
  },

  async toggle(id) {
    try {
      const data = await API.post(`${ENDPOINTS.SCENARIOS}/${id}/toggle`);
      Utils.showToast(data.message || "Statut modifié", "success");
      await this.load();
    } catch (error) {
      console.error(error);
      Utils.showToast(error.message || "Erreur changement statut", "error");
    }
  },

  async call(id) {
    try {
      const data = await API.post(`${ENDPOINTS.SCENARIOS}/${id}/call`);
      Utils.showToast(data.message || "Appel lancé", "success");
    } catch (error) {
      Utils.showToast(error.message || "Erreur lancement appel", "error");
    }
  },

  async exportScenarios() {
    try {
      await Utils.downloadFile(
        Utils.buildApiUrl(ENDPOINTS.SCENARIOS_EXPORT),
        "scenarios_export.json"
      );

      Utils.showToast("Export réussi", "success");
    } catch (error) {
      Utils.showToast("Erreur export", "error");
    }
  },

  async importScenarios(file) {
    const ok = await Utils.confirmAction(`Importer ${file.name} ?`);
    if (!ok) return;

    try {
      const result = await Utils.uploadFile(
        ENDPOINTS.SCENARIOS_IMPORT,
        file
      );

      if (!result.success) {
        throw new Error(result.error);
      }

      Utils.showToast("Import terminé", "success");
      await this.load();
    } catch (error) {
      console.error(error);
      Utils.showToast(error.message || "Erreur import", "error");
    }
  }
};

window.Scenarios = Scenarios;
