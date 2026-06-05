const SpeechValidation = {
  status: { ready: true },
  items: [],
  isLoading: false,

  init() {
    this.initElements();
    this.bindEvents();
    console.log("Module VoskResults initialise");
  },

  initElements() {
    this.statusBadge = document.getElementById("speech-status-badge");
    this.fetchModeEl = document.getElementById("speech-fetch-mode");
    this.transcriptionModeEl = document.getElementById("speech-transcription-mode");
    this.sftpHostEl = document.getElementById("speech-sftp-host");
    this.pendingCountEl = document.getElementById("speech-pending-count");
    this.statusFilter = document.getElementById("speech-status-filter");
    this.tableBody = document.getElementById("speech-table-body");
    this.refreshBtn = document.getElementById("refresh-speech");
  },

  bindEvents() {
    this.refreshBtn?.addEventListener("click", async () => {
      await this.load();
    });

    this.statusFilter?.addEventListener("change", async () => {
      await this.loadResults();
      this.render();
    });
  },

  async load() {
    if (this.isLoading) return;
    this.isLoading = true;

    try {
      Utils.setLoading(this.tableBody, true);
      await this.loadResults();
      this.render();
    } catch (error) {
      console.error("Erreur resultats Vosk:", error);
      if (this.tableBody) {
        this.tableBody.innerHTML = `
          <tr>
            <td colspan="7">Erreur de chargement des resultats Vosk</td>
          </tr>
        `;
      }
      Utils.showToast(error.message || "Erreur resultats Vosk", "error");
    } finally {
      Utils.setLoading(this.tableBody, false);
      this.isLoading = false;
    }
  },

  async loadResults() {
    const params = new URLSearchParams();
    const selectedStatus = this.statusFilter?.value || "";
    if (selectedStatus) params.set("vosk_status", selectedStatus);
    params.set("page_size", "50");

    const data = await API.get(`${ENDPOINTS.VOSK_RESULTS}?${params.toString()}`);
    this.items = Array.isArray(data.items) ? data.items : [];
  },

  render() {
    this.renderStatus();
    this.renderTable();
  },

  renderStatus() {
    this.setText(this.fetchModeEl, "Base SQL");
    this.setText(this.transcriptionModeEl, "Amont");
    this.setText(this.sftpHostEl, "calls");
    this.setText(this.pendingCountEl, this.items.length);

    if (this.statusBadge) {
      this.statusBadge.textContent = "Lecture seule";
      this.statusBadge.classList.add("status-ok");
      this.statusBadge.classList.remove("status-fail");
    }
  },

  renderTable() {
    if (!this.tableBody) return;

    if (!this.items.length) {
      this.tableBody.innerHTML = `
        <tr>
          <td colspan="7">Aucun resultat Vosk pour ce filtre</td>
        </tr>
      `;
      return;
    }

    this.tableBody.innerHTML = this.items.map((item) => `
      <tr>
        <td>#${Utils.escapeHtml(item.id ?? "-")}</td>
        <td>${Utils.escapeHtml(Utils.formatDateTime(item.created_at))}</td>
        <td>${Utils.escapeHtml(item.call_id ?? "-")}</td>
        <td>${Utils.escapeHtml(item.channel_id || "-")}</td>
        <td>${this.voskStatusChip(item.vosk_status)}</td>
        <td>${Utils.escapeHtml(this.shorten(item.transcription || "-", 160))}</td>
        <td>
          <div class="row-actions">
            <button class="btn btn-secondary btn-sm" onclick="SpeechValidation.copyTranscription(${item.id})">Copier</button>
          </div>
        </td>
      </tr>
    `).join("");
  },

  voskStatusChip(status) {
    const normalized = String(status || "").trim().toUpperCase();
    if (normalized === "OK" || normalized === "VALID") return '<span class="pill pill-active">Mot-clé OK</span>';
    if (normalized === "KO" || normalized === "INVALID") return '<span class="pill pill-failed">Mot-clé KO</span>';
    if (normalized === "ERROR") return '<span class="pill pill-failed">Erreur</span>';
    if (normalized === "PENDING") return '<span class="pill pill-inactive">En attente</span>';
    if (status) return `<span class="pill pill-inactive">${Utils.escapeHtml(status)}</span>`;
    return '<span class="pill pill-inactive">-</span>';
  },

  async copyTranscription(id) {
    const item = this.items.find((row) => Number(row.id) === Number(id));
    if (!item?.transcription) {
      Utils.showToast("Aucune transcription disponible", "warning");
      return;
    }
    await Utils.copyToClipboard(item.transcription);
  },

  shorten(value, maxLength) {
    if (!value || value.length <= maxLength) return value;
    return `${value.slice(0, maxLength)}...`;
  },

  setText(element, value) {
    if (element) element.textContent = value;
  },

  async onTabActivated() {
    await this.load();
  }
};

window.SpeechValidation = SpeechValidation;
window.VoskResults = SpeechValidation;

window.loadSpeechValidation = async function () {
  await window.SpeechValidation?.load?.();
};
