const Scheduler = {
  status: null,
  items: [],
  isLoading: false,

  init() {
    this.initElements();
    this.bindEvents();
    console.log("Module Planificateur initialise");
  },

  initElements() {
    this.statusBadge = document.getElementById("scheduler-status-badge");
    this.runningEl = document.getElementById("scheduler-running");
    this.jobCountEl = document.getElementById("scheduler-job-count");
    this.activeCountEl = document.getElementById("scheduler-active-count");
    this.errorCountEl = document.getElementById("scheduler-error-count");
    this.tableBody = document.getElementById("scheduler-table-body");
    this.refreshBtn = document.getElementById("refresh-scheduler");
    this.syncBtn = document.getElementById("sync-scheduler");
  },

  bindEvents() {
    this.refreshBtn?.addEventListener("click", async () => {
      await this.load();
    });

    this.syncBtn?.addEventListener("click", async () => {
      await this.sync();
    });
  },

  async load() {
    if (this.isLoading) return;
    this.isLoading = true;

    try {
      Utils.setLoading(this.tableBody, true);
      const data = await API.get(ENDPOINTS.SCHEDULER_JOBS);
      this.status = data.scheduler || {};
      this.items = Array.isArray(data.items) ? data.items : [];
      this.render();
    } catch (error) {
      console.error("Erreur chargement scheduler:", error);
      if (this.tableBody) {
        this.tableBody.innerHTML = `
          <tr>
            <td colspan="10">Erreur de chargement du planificateur</td>
          </tr>
        `;
      }
      Utils.showToast(error.message || "Erreur planificateur", "error");
    } finally {
      Utils.setLoading(this.tableBody, false);
      this.isLoading = false;
    }
  },

  render() {
    const running = !!this.status?.running;
    const jobCount = Number(this.status?.job_count || 0);
    const activeCount = this.items.filter((item) => item.schedule?.schedule_enabled).length;
    const errorCount = this.items.filter((item) => {
      const status = item.schedule?.last_run_status;
      return status === "failed" || status === "schedule_error";
    }).length;

    this.setText(this.runningEl, running ? "Actif" : "Arrêté");
    this.setText(this.jobCountEl, jobCount);
    this.setText(this.activeCountEl, activeCount);
    this.setText(this.errorCountEl, errorCount);

    if (this.statusBadge) {
      this.statusBadge.textContent = running
        ? `Actif - ${jobCount} job(s)`
        : "Planificateur arrêté";
    }

    if (!this.tableBody) return;

    if (!this.items.length) {
      this.tableBody.innerHTML = `
        <tr>
          <td colspan="10">Aucune tâche planifiée</td>
        </tr>
      `;
      return;
    }

    this.tableBody.innerHTML = this.items.map((item) => {
      const scenario = item.scenario || {};
      const schedule = item.schedule || {};
      return `
        <tr>
          <td>
            <strong>${Utils.escapeHtml(scenario.name || "-")}</strong><br>
            <small>${Utils.escapeHtml(scenario.caller || "-")} → ${Utils.escapeHtml(scenario.callee || "-")}</small>
          </td>
          <td>${Utils.escapeHtml(schedule.schedule_type || scenario.frequency || "-")}</td>
          <td>${Utils.escapeHtml(Utils.formatDateTime(schedule.schedule_date))}</td>
          <td>${Utils.escapeHtml(schedule.schedule_time || "-")}</td>
          <td>${Utils.escapeHtml(schedule.schedule_day_of_week || "-")}</td>
          <td>${Utils.escapeHtml(Utils.formatDateTime(schedule.last_run_at))}</td>
          <td>${this.runStatusChip(schedule)}</td>
          <td>${Utils.escapeHtml(Utils.formatDateTime(schedule.next_run_at))}</td>
          <td>${this.jobChip(schedule)}</td>
          <td>
            <div class="row-actions">
              <button class="btn btn-success btn-sm" onclick="Scheduler.runNow(${scenario.id})">Now</button>
              <button class="btn btn-secondary btn-sm" onclick="Scheduler.syncOne(${scenario.id})">Sync</button>
              <button class="btn btn-ghost btn-sm" onclick="Scenarios.edit(${scenario.id})">Modifier</button>
            </div>
          </td>
        </tr>
      `;
    }).join("");
  },

  runStatusChip(schedule) {
    const status = schedule.last_run_status || "-";
    if (status === "success") return '<span class="pill pill-active">Réussi</span>';
    if (status === "running") return '<span class="pill pill-active">En cours</span>';
    if (status === "failed" || status === "schedule_error") {
      const error = schedule.last_run_error ? Utils.escapeHtml(schedule.last_run_error) : "Erreur";
      return `<span class="pill pill-failed" title="${error}">Erreur</span>`;
    }
    if (status === "skipped") return '<span class="pill pill-inactive">Ignoré</span>';
    return '<span class="pill pill-inactive">Jamais lancé</span>';
  },

  jobChip(schedule) {
    if (!schedule.schedule_enabled) return '<span class="pill pill-inactive">Désactivé</span>';
    if (schedule.job_registered) return '<span class="pill pill-active">Enregistré</span>';
    return '<span class="pill pill-failed">Absent</span>';
  },

  async sync() {
    try {
      await API.post(ENDPOINTS.SCHEDULER_SYNC);
      Utils.showToast("Planificateur synchronisé", "success");
      await this.load();
    } catch (error) {
      Utils.showToast(error.message || "Erreur synchronisation", "error");
    }
  },

  async syncOne(id) {
    try {
      await API.post(`${ENDPOINTS.SCENARIOS}/${id}/schedule/sync`);
      Utils.showToast("Tâche synchronisée", "success");
      await this.load();
      await window.Scenarios?.load?.();
    } catch (error) {
      Utils.showToast(error.message || "Erreur synchronisation tâche", "error");
    }
  },

  async runNow(id) {
    try {
      await API.post(`${ENDPOINTS.SCENARIOS}/${id}/run-now`);
      Utils.showToast("Exécution lancée", "success");
      await this.load();
      await window.History?.load?.();
    } catch (error) {
      Utils.showToast(error.message || "Erreur exécution immédiate", "error");
    }
  },

  setText(element, value) {
    if (element) {
      element.textContent = value;
    }
  },

  async onTabActivated() {
    await this.load();
  }
};

window.Scheduler = Scheduler;

window.loadScheduler = async function () {
  await window.Scheduler?.load?.();
};
