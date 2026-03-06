// Point d'entrée de l'application
const App = {
  initialized: false,

  async init() {
    if (this.initialized) return;

    try {
      console.log("Initialisation application...");

      if (window.Tabs && typeof window.Tabs.init === "function") {
        window.Tabs.init();
      }

      if (window.Health && typeof window.Health.init === "function") {
        window.Health.init();
      }

      if (window.Scenarios && typeof window.Scenarios.init === "function") {
        window.Scenarios.init();
      }

      if (window.History && typeof window.History.init === "function") {
        window.History.init();
      }

      if (window.Stats && typeof window.Stats.init === "function") {
        window.Stats.init();
      }

      await this.loadInitialData();

      this.initialized = true;
      console.log("✓ Application initialisée");
    } catch (error) {
      console.error("Erreur initialisation application:", error);
      Utils.showToast("Erreur lors de l'initialisation de l'application", "error");
    }
  },

  async loadInitialData() {
    const currentTab = window.Tabs?.getCurrentTab?.() || "planner";

    switch (currentTab) {
      case "planner":
        await window.Scenarios?.load?.();
        break;
      case "history":
        await window.History?.load?.();
        break;
      case "stats":
        await window.Stats?.load?.();
        break;
      default:
        await window.Scenarios?.load?.();
        break;
    }
  }
};

// Export global
window.App = App;

document.addEventListener("DOMContentLoaded", async () => {
  await App.init();
});