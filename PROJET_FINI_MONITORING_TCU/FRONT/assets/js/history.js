// Module de gestion de l'historique des appels
const History = {
  items: [],
  currentPage: 1,
  totalPages: 1,
  totalItems: 0,
  pageSize: CONFIG.DEFAULT_PAGE_SIZE,
  isLoading: false,

  // Références DOM
  tableBody: null,
  paginationInfo: null,
  prevBtn: null,
  nextBtn: null,

  init() {
    this.initElements();
    this.bindEvents();
    console.log("✓ Module History initialisé");
  },

  initElements() {
    this.tableBody = document.getElementById("history-table-body");
    this.paginationInfo = document.getElementById("pagination-info");
    this.prevBtn = document.getElementById("prev-page");
    this.nextBtn = document.getElementById("next-page");
  },

  bindEvents() {
    const inputs = [
      "history-caller",
      "history-callee",
      "history-category"
    ];

    inputs.forEach(id => {
      const el = document.getElementById(id);
      el?.addEventListener(
        "input",
        Utils.debounce(async () => {
          this.currentPage = 1;
          await this.load();
        }, 500)
      );
    });

    document.getElementById("load-history")?.addEventListener("click", async () => {
      this.currentPage = 1;
      await this.load();
    });

    this.prevBtn?.addEventListener("click", async () => {
      if (this.currentPage > 1) {
        this.currentPage--;
        await this.load();
      }
    });

    this.nextBtn?.addEventListener("click", async () => {
      if (this.currentPage < this.totalPages) {
        this.currentPage++;
        await this.load();
      }
    });

    document.getElementById("history-size")?.addEventListener("change", async (e) => {
      this.pageSize = Number(e.target.value || CONFIG.DEFAULT_PAGE_SIZE);
      this.currentPage = 1;
      await this.load();
    });

    document.getElementById("export-history")?.addEventListener("click", async () => {
      const query = this.buildQueryString();
      const response = await fetch(`${ENDPOINTS.CALLS_HISTORY}/export?${query}`, {
        method: "GET",
      });

      if (!response.ok) {
        Utils.showToast("Erreur lors de l'exportation de l'historique", "error");
        return;
      }

      const blob = await response.blob();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "calls_history_export.json";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    });
  },

  getFilters() {
    return {
      caller: document.getElementById("history-caller")?.value.trim() || "",
      callee: document.getElementById("history-callee")?.value.trim() || "",
      category: document.getElementById("history-category")?.value.trim() || "",
      status: document.getElementById("history-status")?.value || ""
    };
  },

  buildQueryString() {
    const filters = this.getFilters();
    const params = new URLSearchParams();

    params.set("page", String(this.currentPage));
    params.set("page_size", String(this.pageSize));
    params.set("include_duration", "true");

    if (filters.caller) params.set("caller", filters.caller);
    if (filters.callee) params.set("callee", filters.callee);
    if (filters.category) params.set("category", filters.category);
    if (filters.status) params.set("status", filters.status);

    return params.toString();
  },

  async load() {
    if (this.isLoading) return;

    this.isLoading = true;

    try {
      Utils.setLoading(this.tableBody, true);

      const query = this.buildQueryString();
      const result = await Utils.apiGet(
        `${ENDPOINTS.CALLS_HISTORY}?${query}`
      );

      if (!result.success) {
        throw new Error(result.error || "Erreur de chargement de l'historique");
      }

      const data = result.data || {};
      this.items = Array.isArray(data.items) ? data.items : [];
      this.currentPage = Number(data.page || 1);
      this.totalPages = Number(data.total_pages || 1);
      this.totalItems = Number(data.total || 0);

      this.render();
      this.updatePagination();
    } catch (error) {
      console.error("Erreur chargement historique:", error);

      if (this.tableBody) {
        this.tableBody.innerHTML = `
          <tr>
            <td colspan="15">Erreur de chargement de l'historique</td>
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

    if (!this.items.length) {
      this.tableBody.innerHTML = `
        <tr>
          <td colspan="15">${MESSAGES.NO_DATA}</td>
        </tr>
      `;
      return;
    }

    this.tableBody.innerHTML = this.items.map((item) => {
      const scenario = item.scenario_name || "-";
      const keyword = item.scenario_keyword || "-";
      const category = item.scenario_category || "-";

      return `
      <tr>
        <td>#${Utils.escapeHtml(item.id ?? "-")}</td>
        <td>${Utils.escapeHtml(Utils.formatDateTime(item.created_at))}</td>
        <td>${Utils.escapeHtml(item.caller || "-")}</td>
        <td>${Utils.escapeHtml(item.callee || "-")}</td>
        <td>${Utils.escapeHtml(item.trunk || "-")}</td>
        <td>${Utils.escapeHtml(scenario)}</td>
        <td>${Utils.escapeHtml(keyword)}</td>
        <td>${Utils.escapeHtml(category)}</td>
        <td>${Utils.formatDuration(item.call_time_s)}</td>
        <td>${Utils.formatDuration(item.duration)}</td>
        <td>${Utils.getDtmfChip(item.dtmf, item.time_s_before_dtmf, item.time_ms_between_dtmf)}</td>
        <td>
          ${this.getVoskStatusChip(item.vosk_status)}
          ${this.renderKeywordChecks(item.keyword_checks)}
        </td>
        <td>${Utils.getStatusChip(item.status, item.status_label)}</td>
        <td>${Utils.escapeHtml(item.error_display || item.error_message || "-")}</td>
        <td>
          <div class="cell-actions">
            <button class="btn btn-secondary" data-action="channel" data-channel="${Utils.escapeHtml(item.channel_id || "")}">
              Channel
            </button>
          </div>
        </td>
      </tr>
      `;
    }).join("");

    this.bindTableActions();
  },

  bindTableActions() {
    this.tableBody
      ?.querySelectorAll('[data-action="channel"]')
      .forEach((btn) => {
        btn.addEventListener("click", async () => {
          const channel = btn.dataset.channel || "";
          if (!channel) {
            Utils.showToast("Aucun channel disponible", "warning");
            return;
          }
          await Utils.copyToClipboard(channel);
        });
      });
  },

  getVoskStatusChip(status) {
    const normalized = String(status || "").trim().toUpperCase();
    if (normalized === "OK" || normalized === "VALID") return '<span class="pill pill-active">Mot-clé OK</span>';
    if (normalized === "KO" || normalized === "INVALID") return '<span class="pill pill-failed">Mot-clé KO</span>';
    if (normalized === "ERROR") return '<span class="pill pill-failed">Erreur</span>';
    if (normalized === "PENDING") return '<span class="pill pill-inactive">En attente</span>';
    if (status) return `<span class="pill pill-inactive">${Utils.escapeHtml(status)}</span>`;
    return '<span class="pill pill-inactive">-</span>';
  },

  renderKeywordChecks(checks) {
    if (!Array.isArray(checks) || !checks.length) return "";

    return `
      <div class="keyword-checks">
        ${checks.map((item) => `
          <span class="keyword-check ${item.found ? "keyword-check-ok" : "keyword-check-ko"}">
            ${Utils.escapeHtml(item.keyword || "-")} ${item.found ? "OK" : "KO"}
          </span>
        `).join("")}
      </div>
    `;
  },

  shortenText(text, maxLength = 80) {
    if (!text || text.length <= maxLength) return text;
    return `${text.slice(0, maxLength)}...`;
  },

  updatePagination() {
    if (this.paginationInfo) {
      this.paginationInfo.textContent =
        `Page ${this.currentPage} / ${this.totalPages} — ${this.totalItems} résultat(s)`;
    }

    if (this.prevBtn) {
      this.prevBtn.disabled = this.currentPage <= 1;
    }

    if (this.nextBtn) {
      this.nextBtn.disabled = this.currentPage >= this.totalPages;
    }
  },

  async onTabActivated() {
    await this.load();
  }
};

// Export global
window.History = History;

// Compatibilité ancienne approche
window.loadHistory = async function () {
  if (window.History && typeof window.History.load === "function") {
    await window.History.load();
  }
};

window.showChannel = async function (channelId) {
  if (!channelId) {
    Utils.showToast("Aucun channel disponible", "warning");
    return;
  }
  await Utils.copyToClipboard(channelId);
};

