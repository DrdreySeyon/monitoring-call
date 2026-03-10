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

      this.scenarios = data || [];

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
          <td colspan="8" class="text-center">Aucun scénario</td>
        </tr>
      `;

      if (this.countBadge) this.countBadge.textContent = "0 scénario";

      return;

    }

    this.tableBody.innerHTML = this.scenarios.map((s) => {

      return `
      <tr>

        <td>${Utils.escapeHtml(s.name)}</td>

        <td>${Utils.escapeHtml(s.keyword)}</td>

        <td>${Utils.escapeHtml(s.category)}</td>

        <td>${Utils.escapeHtml(s.caller)}</td>

        <td>${Utils.escapeHtml(s.callee)}</td>

        <td>${Utils.formatDuration(s.call_time_s)}</td>

        <td>${Utils.getDtmfChip(
          s.dtmf,
          s.time_s_before_dtmf,
          s.time_ms_between_dtmf
        )}</td>

        <td>

          <button class="btn btn-primary btn-sm" onclick="Scenarios.call(${s.id})">
            ▶
          </button>

          <button class="btn btn-secondary btn-sm" onclick="Scenarios.edit(${s.id})">
            ✏
          </button>

          <button class="btn btn-danger btn-sm" onclick="Scenarios.remove(${s.id})">
            🗑
          </button>

        </td>

      </tr>
      `;

    }).join("");

    if (this.countBadge) {

      this.countBadge.textContent = `${this.scenarios.length} scénario(s)`;

    }

  },

  openCreateModal() {

    if (!this.modal) return;

    this.modalTitle.textContent = "Créer un scénario";

    this.form.reset();

    this.form.dataset.id = "";

    this.modal.classList.remove("hidden");

  },

  closeModal() {

    if (!this.modal) return;

    this.modal.classList.add("hidden");

  },

  edit(id) {

    const s = this.scenarios.find((x) => x.id === id);

    if (!s) return;

    this.form.dataset.id = id;

    this.modalTitle.textContent = "Modifier scénario";

    this.form.name.value = s.name;
    this.form.keyword.value = s.keyword;
    this.form.category.value = s.category;
    this.form.caller.value = s.caller;
    this.form.callee.value = s.callee;
    this.form.trunk.value = s.trunk;
    this.form.call_time_s.value = s.call_time_s;
    this.form.dtmf.value = s.dtmf || "";
    this.form.time_s_before_dtmf.value = s.time_s_before_dtmf || "";
    this.form.time_ms_between_dtmf.value = s.time_ms_between_dtmf || "";
    this.form.frequency.value = s.frequency || "";

    this.modal.classList.remove("hidden");

  },

  async submitForm() {

    const id = this.form.dataset.id;

    const payload = {

      name: this.form.name.value,
      keyword: this.form.keyword.value,
      category: this.form.category.value,
      caller: this.form.caller.value,
      callee: this.form.callee.value,
      trunk: this.form.trunk.value,
      call_time_s: Number(this.form.call_time_s.value),
      dtmf: this.form.dtmf.value || null,
      time_s_before_dtmf: this.form.time_s_before_dtmf.value || null,
      time_ms_between_dtmf: this.form.time_ms_between_dtmf.value || null,
      frequency: this.form.frequency.value || null

    };

    try {

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

      Utils.showToast(error.message, "error");

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

      Utils.showToast(error.message, "error");

    }

  },

  async call(id) {

    try {

      await API.post(`${ENDPOINTS.SCENARIOS}/${id}/call`);

      Utils.showToast("Appel lancé", "success");

    } catch (error) {

      Utils.showToast(error.message, "error");

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

    const ok = await Utils.confirmAction(

      `Importer ${file.name} ?`

    );

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

      Utils.showToast(error.message, "error");

    }

  }

};

window.Scenarios = Scenarios;
