// Module de monitoring de santé du système
const Health = {
  // Éléments DOM
  healthIndicator: null,

  // État
  currentStatus: "unknown",
  checkInterval: null,
  isChecking: false,

  /**
   * Initialise le module de santé
   */
  init() {
    this.initElements();
    this.startHealthChecking();
    console.log("✓ Module Health initialisé");
  },

  /**
   * Initialise les références DOM
   */
  initElements() {
    this.healthIndicator = document.getElementById("system-status");
  },

  /**
   * Démarre la vérification périodique de santé
   */
  startHealthChecking() {
    this.checkHealth();

    this.checkInterval = setInterval(() => {
      this.checkHealth();
    }, CONFIG.HEALTH_CHECK_INTERVAL);

    document.addEventListener("visibilitychange", () => {
      if (!document.hidden && !this.isChecking) {
        this.checkHealth();
      }
    });

    window.addEventListener("online", () => {
      setTimeout(() => this.checkHealth(), 1000);
    });

    window.addEventListener("offline", () => {
      this.updateHealthStatus("error", MESSAGES.OFFLINE, {
        database: { status: "unknown", message: "Hors ligne" },
        ari: { status: "unknown", message: "Hors ligne" }
      });
    });
  },

  /**
   * Effectue une vérification de santé complète
   */
  async checkHealth() {
    if (this.isChecking) return;

    this.isChecking = true;

    try {
      if (!navigator.onLine) {
        this.updateHealthStatus("error", MESSAGES.OFFLINE);
        return;
      }

      const result = await Utils.fetchWithErrorHandling(
        `${CONFIG.API_BASE_URL}${CONFIG.API_PREFIX}${ENDPOINTS.HEALTH_DETAILED}`
      );

      if (result.success) {
        const health = result.data;
        this.processHealthResponse(health);
      } else {
        this.updateHealthStatus("error", `Erreur API : ${result.error}`);
      }
    } catch (error) {
      console.error("Erreur lors de la vérification de santé:", error);
      this.updateHealthStatus("error", "Erreur de vérification");
    } finally {
      this.isChecking = false;
    }
  },

  /**
   * Traite la réponse de santé de l'API
   */
  processHealthResponse(health) {
    const status = health.status || "unknown";
    const checks = health.checks || {};

    let message = MESSAGES.SYSTEM_OK;
    let displayStatus = "ok";

    const dbCheck = checks.database || {};
    const ariCheck = checks.ari || {};

    if (status === "degraded") {
      displayStatus = "degraded";
      message = MESSAGES.SYSTEM_DEGRADED;

      const issues = [];
      if (dbCheck.status === "error") issues.push("BDD");
      if (ariCheck.status === "error") issues.push("ARI");

      if (issues.length > 0) {
        message += ` (${issues.join(", ")})`;
      }
    } else if (status === "error" || status !== "ok") {
      displayStatus = "error";
      message = MESSAGES.SYSTEM_ERROR;
    }

    this.updateHealthStatus(displayStatus, message, checks);
    this.updateTabIndicators(checks);
  },

  /**
   * Met à jour le statut de santé affiché
   */
  updateHealthStatus(status, message, checks = {}) {
    this.currentStatus = status;

    if (this.healthIndicator) {
      this.healthIndicator.textContent = message;
      this.healthIndicator.classList.remove("status-ok", "status-fail");

      if (status === "ok") {
        this.healthIndicator.classList.add("status-ok");
      } else {
        this.healthIndicator.classList.add("status-fail");
      }

      const details = this.buildHealthTooltip(checks);
      if (details) {
        this.healthIndicator.title = details;
      }
    }

    console.log(`Santé du système: ${status} - ${message}`);
  },

  /**
   * Construit le tooltip de santé détaillé
   */
  buildHealthTooltip(checks) {
    if (!checks || Object.keys(checks).length === 0) {
      return "État détaillé du système indisponible";
    }

    const lines = ["État détaillé du système :"];

    if (checks.database) {
      const db = checks.database;
      lines.push(`• Base de données : ${db.status || "unknown"}${db.message ? ` (${db.message})` : ""}`);
    }

    if (checks.ari) {
      const ari = checks.ari;
      lines.push(`• Asterisk ARI : ${ari.status || "unknown"}${ari.message ? ` (${ari.message})` : ""}`);

      if (ari.asterisk_version) {
        lines.push(`  Version : ${ari.asterisk_version}`);
      }
    }

    lines.push(`• Dernière vérification : ${new Date().toLocaleTimeString("fr-FR")}`);

    return lines.join("\n");
  },

  /**
   * Met à jour les indicateurs d'onglets en fonction de la santé
   */
  updateTabIndicators(checks) {
    if (!window.Tabs) return;

    // Problème ARI => onglet planificateur
    if (checks.ari && checks.ari.status === "error") {
      window.Tabs.addTabIndicator("planner", null, "error");
    } else {
      window.Tabs.removeTabIndicator("planner");
    }

    // Problème base => historique + stats
    if (checks.database && checks.database.status === "error") {
      window.Tabs.addTabIndicator("history", null, "error");
      window.Tabs.addTabIndicator("stats", null, "error");
    } else {
      window.Tabs.removeTabIndicator("history");
      window.Tabs.removeTabIndicator("stats");
    }
  },

  /**
   * Retourne le statut courant
   */
  getCurrentStatus() {
    return this.currentStatus;
  },

  /**
   * Force une vérification immédiate
   */
  async forceCheck() {
    if (this.isChecking) return;

    Utils.showToast("🔄 Vérification de la santé du système...", "info", 1500);
    await this.checkHealth();
  },

  /**
   * Active / désactive la vérification auto
   */
  toggleAutoCheck(enabled = true) {
    if (enabled && !this.checkInterval) {
      this.startHealthChecking();
    } else if (!enabled && this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
  },

  /**
   * Retourne les statistiques de santé détaillées
   */
  async getDetailedHealthStats() {
    const result = await Utils.fetchWithErrorHandling(
      `${CONFIG.API_BASE_URL}${CONFIG.API_PREFIX}${ENDPOINTS.HEALTH_DETAILED}`
    );

    if (result.success) {
      return {
        ...result.data,
        client_info: {
          user_agent: navigator.userAgent,
          online: navigator.onLine,
          language: navigator.language,
          platform: navigator.platform,
          memory: navigator.deviceMemory || "unknown",
          connection: navigator.connection
            ? {
                type: navigator.connection.effectiveType,
                downlink: navigator.connection.downlink,
                rtt: navigator.connection.rtt
              }
            : "unknown"
        }
      };
    }

    return null;
  },

  /**
   * Nettoyage
   */
  destroy() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
    console.log("Module Health détruit");
  }
};

// Export global
window.Health = Health;

// Compatibilité avec l’ancienne approche simple
window.loadHealth = async function () {
  if (window.Health && typeof window.Health.checkHealth === "function") {
    await window.Health.checkHealth();
  }
};
