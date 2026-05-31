// Module de gestion des statistiques
const Stats = {
  isLoading: false,

  init() {
    this.bindEvents();
    this.initDefaultDates();
    console.log("✓ Module Stats initialisé");
  },

  bindEvents() {
    document.getElementById("load-stats")?.addEventListener("click", async () => {
      await this.load();
    });
  },

  initDefaultDates() {
    const startField = document.getElementById("stats-start");
    const endField = document.getElementById("stats-end");

    if (!startField || !endField) return;

    if (!startField.value || !endField.value) {
      const now = new Date();
      const before = new Date();
      before.setDate(now.getDate() - 7);

      if (!startField.value) startField.value = Utils.formatDateForInput(before);
      if (!endField.value) endField.value = Utils.formatDateForInput(now);
    }
  },

  getFilters() {
    return {
      from_date: document.getElementById("stats-start")?.value || "",
      to_date: document.getElementById("stats-end")?.value || ""
    };
  },

  buildQueryString() {
    const filters = this.getFilters();
    const params = new URLSearchParams();

    if (filters.from_date) params.set("from_date", filters.from_date);
    if (filters.to_date) params.set("to_date", filters.to_date);

    return params.toString();
  },

  async load() {
    if (this.isLoading) return;
    this.isLoading = true;

    try {
      const query = this.buildQueryString();
      const endpoint = query
        ? `${ENDPOINTS.CALLS_STATS}?${query}`
        : ENDPOINTS.CALLS_STATS;

      const result = await Utils.apiGet(endpoint);

      if (!result.success) {
        throw new Error(result.error || "Erreur de chargement des statistiques");
      }

      this.render(result.data || {});
    } catch (error) {
      console.error("Erreur chargement stats:", error);
      Utils.showToast(error.message || MESSAGES.ERROR_SERVER, "error");
    } finally {
      this.isLoading = false;
    }
  },

  render(data) {
    this.setText("stat-total", data.total_calls ?? 0);
    this.setText("stat-success", data.successful_calls ?? 0);
    this.setText("stat-failed", data.failed_calls ?? 0);
    this.setText("stat-success-rate", `${data.success_rate ?? 0}%`);
    this.setText("stat-avg-duration", Utils.formatDuration(data.average_duration_seconds ?? 0));
    this.setText("stat-dtmf-calls", data.dtmf_calls ?? 0);
    this.setText("stat-dtmf-usage", `${data.dtmf_usage_rate ?? 0}%`);
    this.setText("stat-efficiency", `${data.success_rate ?? 0}%`);
  },

  setText(id, value) {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = value;
    }
  },

  async onTabActivated() {
    await this.load();
  }
};

// Export global
window.Stats = Stats;

// Compatibilité ancienne approche
window.loadStats = async function () {
  if (window.Stats && typeof window.Stats.load === "function") {
    await window.Stats.load();
  }
};