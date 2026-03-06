// Fonctions utilitaires globales avec support DTMF
const Utils = {
  /**
   * Formate une durée en secondes en format HH:MM:SS ou MM:SS
   */
  formatDuration(seconds) {
    if (seconds === null || seconds === undefined || isNaN(seconds) || seconds < 0) return "-";
    const total = Number(seconds);
    const s = total % 60;
    const m = Math.floor(total / 60) % 60;
    const h = Math.floor(total / 3600);
    const pad = (n) => n.toString().padStart(2, "0");

    if (h > 0) return `${pad(h)}:${pad(m)}:${pad(s)}`;
    return `${pad(m)}:${pad(s)}`;
  },

  /**
   * Formate une date ISO en format local français
   */
  formatDateTime(isoString) {
    if (!isoString) return "-";
    try {
      return new Date(isoString).toLocaleString("fr-FR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
      });
    } catch {
      return isoString;
    }
  },

  /**
   * Formate une date pour input datetime-local
   */
  formatDateForInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    const hours = String(date.getHours()).padStart(2, "0");
    const minutes = String(date.getMinutes()).padStart(2, "0");
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  },

  /**
   * Génère un chip de statut HTML
   */
  getStatusChip(status) {
    const statusMap = {
      [CALL_STATUS.SUCCESS]: { class: "status-chip success", text: "✅ Réussi" },
      [CALL_STATUS.FAILED]: { class: "status-chip failed", text: "❌ Échoué" },
      [CALL_STATUS.IN_PROGRESS]: { class: "status-chip in-progress", text: "⏳ En cours" }
    };

    const info = statusMap[status] || { class: "status-chip", text: status || "-" };
    return `<span class="${info.class}">${info.text}</span>`;
  },

  /**
   * Génère un chip DTMF si présent
   */
  getDtmfChip(dtmf, delay, interval) {
    if (!dtmf) return "-";
    const title =
      `DTMF: ${dtmf}` +
      `${delay ? ` (délai: ${delay}s)` : ""}` +
      `${interval ? ` (intervalle: ${interval}ms)` : ""}`;

    return `<span class="chip-dtmf" title="${title}">🎛 ${this.escapeHtml(dtmf)}</span>`;
  },

  /**
   * Affiche un message de statut dans un élément
   */
  setStatus(element, message, type = "") {
    if (typeof element === "string") {
      element = document.getElementById(element);
    }

    if (element) {
      element.textContent = message;
      element.className = `status ${type}`.trim();

      if (message) {
        element.style.opacity = "0";
        element.style.transform = "translateY(-5px)";
        setTimeout(() => {
          element.style.transition = "opacity 0.3s ease, transform 0.3s ease";
          element.style.opacity = "1";
          element.style.transform = "translateY(0)";
        }, 10);
      }
    }
  },

  /**
   * Effectue une requête fetch avec gestion d'erreur et retry
   */
  async fetchWithErrorHandling(url, options = {}) {
    const defaultOptions = {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      },
      ...options
    };

    for (let attempt = 1; attempt <= CONFIG.RETRY_ATTEMPTS; attempt++) {
      try {
        const response = await fetch(url, defaultOptions);

        if (!response.ok) {
          let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

          try {
            const errorData = await response.json();
            if (errorData.detail) {
              errorMessage = errorData.detail;
            }
          } catch {
            // ignore JSON parse error
          }

          throw new Error(errorMessage);
        }

        const contentType = response.headers.get("content-type") || "";
        const data = contentType.includes("application/json")
          ? await response.json()
          : await response.text();

        return { success: true, data, response };
      } catch (error) {
        console.error(`Tentative ${attempt}/${CONFIG.RETRY_ATTEMPTS} échouée pour ${url}:`, error);

        if (attempt === CONFIG.RETRY_ATTEMPTS) {
          return {
            success: false,
            error: error.message || MESSAGES.ERROR_NETWORK,
            attempt
          };
        }

        if (attempt < CONFIG.RETRY_ATTEMPTS) {
          await this.delay(CONFIG.RETRY_DELAY * attempt);
        }
      }
    }
  },

  /**
   * Debounce function pour limiter les appels
   */
  debounce(func, wait = CONFIG.DEBOUNCE_DELAY) {
    let timeout;
    return (...args) => {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  /**
   * Throttle function pour limiter la fréquence d'appels
   */
  throttle(func, limit = 1000) {
    let inThrottle;
    return function (...args) {
      const context = this;
      if (!inThrottle) {
        func.apply(context, args);
        inThrottle = true;
        setTimeout(() => {
          inThrottle = false;
        }, limit);
      }
    };
  },

  /**
   * Échappe les caractères HTML
   */
  escapeHtml(text) {
    if (text === null || text === undefined) return "";
    const map = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;"
    };
    return String(text).replace(/[&<>"']/g, (m) => map[m]);
  },

  /**
   * Formate un nombre avec séparateurs
   */
  formatNumber(num) {
    if (typeof num !== "number" || isNaN(num)) return "-";
    return num.toLocaleString("fr-FR");
  },

  /**
   * Crée un délai
   */
  delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  },

  /**
   * Valide un numéro de téléphone
   */
  validatePhoneNumber(phone) {
    if (!phone || typeof phone !== "string") return false;
    const cleaned = phone.trim();
    return /^[\d+\-\s()#*]+$/.test(cleaned) && cleaned.length > 0;
  },

  /**
   * Valide une séquence DTMF
   */
  validateDtmfSequence(dtmf) {
    if (!dtmf || typeof dtmf !== "string") return true;
    const cleaned = dtmf.trim();
    if (cleaned.length === 0) return true;
    return /^[\d*#\s]+$/.test(cleaned);
  },

  /**
   * Valide la durée d'appel
   */
  validateCallTime(seconds) {
    return typeof seconds === "number" &&
      seconds >= 1 &&
      seconds <= CONFIG.CALL_TIME_MAX;
  },

  /**
   * Valide la cohérence des paramètres DTMF
   */
  validateDtmfParams(dtmf, delay, callTime) {
    if (!dtmf) return true;

    if (delay !== null && delay !== undefined) {
      if (delay < 0) return false;
      if (callTime && delay >= callTime) return false;
    }

    return true;
  },

  /**
   * Copie texte presse-papier
   */
  async copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      this.showToast("📋 Copié dans le presse-papier", "success");
      return true;
    } catch (error) {
      console.error("Erreur copie presse-papier:", error);
      this.showToast("❌ Erreur lors de la copie", "error");
      return false;
    }
  },

  /**
   * Toast notification
   */
  showToast(message, type = "info", duration = 3000) {
    document.querySelectorAll(".toast").forEach((toast) => toast.remove());

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    const colors = {
      success: STATUS_COLORS.success,
      error: STATUS_COLORS.failed,
      warning: STATUS_COLORS.warning,
      info: STATUS_COLORS.info
    };

    toast.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: ${colors[type] || colors.info};
      color: white;
      padding: 1rem 1.5rem;
      border-radius: 8px;
      z-index: 10000;
      max-width: 350px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.3);
      transform: translateX(400px);
      transition: transform 0.3s ease;
      font-size: 0.9rem;
      font-weight: 500;
      border-left: 4px solid rgba(255,255,255,0.3);
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.transform = "translateX(0)";
    }, 10);

    setTimeout(() => {
      toast.style.transform = "translateX(400px)";
      setTimeout(() => {
        if (toast.parentNode) {
          toast.remove();
        }
      }, 300);
    }, duration);
  },

  /**
   * Confirmation personnalisée
   */
  async confirmAction(message, title = "Confirmation") {
    return new Promise((resolve) => {
      const modal = document.createElement("div");
      modal.className = "modal-overlay";
      modal.innerHTML = `
        <div class="modal-content">
          <div class="modal-header">
            <h3>${this.escapeHtml(title)}</h3>
          </div>
          <div class="modal-body">
            <p>${this.escapeHtml(message)}</p>
          </div>
          <div class="modal-footer" style="display:flex; gap:10px; justify-content:flex-end; margin-top:20px;">
            <button data-action="cancel" class="btn btn-ghost">Annuler</button>
            <button data-action="confirm" class="btn btn-primary">Confirmer</button>
          </div>
        </div>
      `;

      modal.style.cssText = `
        position: fixed;
        inset: 0;
        background: rgba(0,0,0,0.55);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10001;
        opacity: 0;
        transition: opacity 0.3s ease;
      `;

      const content = modal.querySelector(".modal-content");
      content.style.cssText = `
        background: #1a2241;
        padding: 24px;
        border-radius: 16px;
        border: 1px solid rgba(165, 120, 255, 0.28);
        max-width: 500px;
        width: 90%;
        transform: scale(0.9);
        transition: transform 0.3s ease;
        box-shadow: 0 20px 50px rgba(0,0,0,0.5);
        color: #edf1ff;
      `;

      document.body.appendChild(modal);

      setTimeout(() => {
        modal.style.opacity = "1";
        content.style.transform = "scale(1)";
      }, 10);

      modal.addEventListener("click", (e) => {
        const action = e.target.dataset.action;
        if (action === "confirm" || action === "cancel") {
          modal.style.opacity = "0";
          content.style.transform = "scale(0.9)";
          setTimeout(() => {
            modal.remove();
            resolve(action === "confirm");
          }, 300);
        } else if (e.target === modal) {
          modal.style.opacity = "0";
          content.style.transform = "scale(0.9)";
          setTimeout(() => {
            modal.remove();
            resolve(false);
          }, 300);
        }
      });

      const handleKeydown = (e) => {
        if (e.key === "Escape") {
          document.removeEventListener("keydown", handleKeydown);
          modal.style.opacity = "0";
          content.style.transform = "scale(0.9)";
          setTimeout(() => {
            modal.remove();
            resolve(false);
          }, 300);
        } else if (e.key === "Enter") {
          document.removeEventListener("keydown", handleKeydown);
          modal.style.opacity = "0";
          content.style.transform = "scale(0.9)";
          setTimeout(() => {
            modal.remove();
            resolve(true);
          }, 300);
        }
      };

      document.addEventListener("keydown", handleKeydown);
    });
  },

  /**
   * Ajoute une classe loading
   */
  setLoading(element, loading = true) {
    if (typeof element === "string") {
      element = document.getElementById(element);
    }

    if (element) {
      if (loading) {
        element.classList.add("loading");
        element.style.position = "relative";
      } else {
        element.classList.remove("loading");
        element.style.position = "";
      }
    }
  },

  /**
   * Parse paramètres DTMF
   */
  parseDtmfString(dtmfString) {
    if (!dtmfString) return null;

    const cleaned = dtmfString.replace(/\s+/g, "");
    if (!this.validateDtmfSequence(cleaned)) {
      return null;
    }

    return {
      sequence: cleaned,
      keys: cleaned.split(""),
      duration: cleaned.length
    };
  },

  /**
   * Formate paramètres d'appel
   */
  formatCallParams(call) {
    const params = [];

    if (call.call_time_s) {
      params.push(`Durée: ${this.formatDuration(call.call_time_s)}`);
    }

    if (call.dtmf) {
      params.push(`DTMF: ${call.dtmf}`);

      if (call.time_s_before_dtmf !== null && call.time_s_before_dtmf !== undefined) {
        params.push(`Délai: ${call.time_s_before_dtmf}s`);
      }

      if (call.time_ms_between_dtmf !== null && call.time_ms_between_dtmf !== undefined) {
        params.push(`Intervalle: ${call.time_ms_between_dtmf}ms`);
      }
    }

    return params.join(" • ");
  },

  /**
   * Construit une URL API
   */
  buildApiUrl(endpoint) {
    return `${CONFIG.API_BASE_URL}${CONFIG.API_PREFIX}${endpoint}`;
  },

  /**
   * GET JSON
   */
  async apiGet(endpoint) {
    return this.fetchWithErrorHandling(this.buildApiUrl(endpoint), {
      method: "GET"
    });
  },

  /**
   * POST JSON
   */
  async apiPost(endpoint, payload = null) {
    return this.fetchWithErrorHandling(this.buildApiUrl(endpoint), {
      method: "POST",
      body: payload ? JSON.stringify(payload) : null
    });
  },

  /**
   * PATCH JSON
   */
  async apiPatch(endpoint, payload) {
    return this.fetchWithErrorHandling(this.buildApiUrl(endpoint), {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
  },

  /**
   * DELETE JSON
   */
  async apiDelete(endpoint) {
    return this.fetchWithErrorHandling(this.buildApiUrl(endpoint), {
      method: "DELETE"
    });
  }
};

// Compatibilité globale
window.Utils = Utils;

// Compatibilité avec le code simple qu’on a posé avant
window.apiUrl = function (path) {
  return Utils.buildApiUrl(path);
};

window.API = {
  async get(path) {
    const result = await Utils.apiGet(path);
    if (!result.success) throw new Error(result.error);
    return result.data;
  },

  async post(path, body = null) {
    const result = await Utils.apiPost(path, body);
    if (!result.success) throw new Error(result.error);
    return result.data;
  },

  async patch(path, body) {
    const result = await Utils.apiPatch(path, body);
    if (!result.success) throw new Error(result.error);
    return result.data;
  },

  async delete(path) {
    const result = await Utils.apiDelete(path);
    if (!result.success) throw new Error(result.error);
    return result.data;
  }
};