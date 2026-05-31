// Module de gestion des onglets avec support des indicateurs
const Tabs = {
  tabs: null,
  tabPlanner: null,
  tabHistory: null,
  tabStats: null,
  tabScheduler: null,
  currentTab: "planner",

  /**
   * Initialise le système d'onglets
   */
  init() {
    this.initElements();
    this.bindEvents();
    this.loadTabState();
    console.log("✓ Module Tabs initialisé");
  },

  /**
   * Initialise les références DOM
   */
  initElements() {
    this.tabs = document.querySelectorAll(".tab-btn");
    this.tabPlanner = document.getElementById("planner");
    this.tabHistory = document.getElementById("history");
    this.tabStats = document.getElementById("stats");
    this.tabScheduler = document.getElementById("scheduler");
  },

  /**
   * Lie les événements
   */
  bindEvents() {
    if (!this.tabs || this.tabs.length === 0) return;

    this.tabs.forEach((tab) => {
      tab.addEventListener("click", (e) => {
        e.preventDefault();
        const tabName = tab.dataset.tab;
        if (tabName && tabName !== this.currentTab) {
          this.switchTab(tabName);
        }
      });

      // Hover léger sur les indicateurs éventuels
      tab.addEventListener("mouseenter", () => {
        const indicator = tab.querySelector(".tab-indicator");
        if (indicator) {
          indicator.style.transform = "scale(1.2)";
        }
      });

      tab.addEventListener("mouseleave", () => {
        const indicator = tab.querySelector(".tab-indicator");
        if (indicator) {
          indicator.style.transform = "scale(1)";
        }
      });
    });

    // Raccourcis clavier
    document.addEventListener("keydown", (e) => {
      if (e.ctrlKey) {
        switch (e.key) {
          case "1":
            e.preventDefault();
            this.switchTab("planner");
            break;
          case "2":
            e.preventDefault();
            this.switchTab("history");
            break;
          case "3":
            e.preventDefault();
            this.switchTab("stats");
            break;
          case "4":
            e.preventDefault();
            this.switchTab("scheduler");
            break;
        }
      }

      if (e.altKey) {
        if (e.key === "ArrowLeft") {
          e.preventDefault();
          this.previousTab();
        } else if (e.key === "ArrowRight") {
          e.preventDefault();
          this.nextTab();
        }
      }
    });
  },

  /**
   * Change d'onglet avec animation
   */
  switchTab(tabName) {
    if (!this.isValidTab(tabName)) return;
    if (this.currentTab === tabName) return;

    const previousTab = this.currentTab;
    this.currentTab = tabName;

    this.updateTabClasses(tabName);
    this.hideTabContent(previousTab);

    setTimeout(() => {
      this.showTabContent(tabName);
      this.onTabChanged(tabName, previousTab);
    }, 150);

    this.saveTabState(tabName);
    console.log(`Onglet changé: ${previousTab} -> ${tabName}`);
  },

  /**
   * Met à jour les classes CSS des onglets
   */
  updateTabClasses(activeTabName) {
    if (!this.tabs) return;

    this.tabs.forEach((tab) => {
      tab.classList.remove("active");
      if (tab.dataset.tab === activeTabName) {
        tab.classList.add("active");
      }
    });
  },

  /**
   * Cache le contenu d'un onglet avec animation
   */
  hideTabContent(tabName) {
    const tabElement = this.getTabElement(tabName);
    if (tabElement && tabElement.classList.contains("active")) {
      tabElement.style.opacity = "0";
      tabElement.style.transform = "translateY(-10px)";

      setTimeout(() => {
        tabElement.classList.remove("active");
        tabElement.style.opacity = "";
        tabElement.style.transform = "";
        tabElement.style.transition = "";
      }, 150);
    }
  },

  /**
   * Affiche le contenu d'un onglet avec animation
   */
  showTabContent(tabName) {
    const tabElement = this.getTabElement(tabName);
    if (tabElement) {
      tabElement.classList.add("active");
      tabElement.style.opacity = "0";
      tabElement.style.transform = "translateY(10px)";
      tabElement.offsetHeight; // force reflow

      tabElement.style.transition = "opacity 0.3s ease, transform 0.3s ease";
      tabElement.style.opacity = "1";
      tabElement.style.transform = "translateY(0)";

      setTimeout(() => {
        tabElement.style.transition = "";
        tabElement.style.opacity = "";
        tabElement.style.transform = "";
      }, 300);
    }
  },

  /**
   * Retourne l’élément DOM du panneau
   */
  getTabElement(tabName) {
    switch (tabName) {
      case "planner":
        return this.tabPlanner;
      case "history":
        return this.tabHistory;
      case "stats":
        return this.tabStats;
      case "scheduler":
        return this.tabScheduler;
      default:
        return null;
    }
  },

  /**
   * Appelé quand un onglet change
   */
  onTabChanged(newTab, previousTab) {
    switch (newTab) {
      case "planner":
        if (window.loadScenarios && typeof window.loadScenarios === "function") {
          window.loadScenarios();
        }
        break;

      case "history":
        if (window.loadHistory && typeof window.loadHistory === "function") {
          window.loadHistory();
        }
        break;

      case "stats":
        if (window.loadStats && typeof window.loadStats === "function") {
          window.loadStats();
        }
        break;

      case "scheduler":
        if (window.loadScheduler && typeof window.loadScheduler === "function") {
          window.loadScheduler();
        }
        break;
    }

    const event = new CustomEvent("tabChanged", {
      detail: {
        newTab,
        previousTab,
        timestamp: new Date().toISOString()
      }
    });
    document.dispatchEvent(event);
  },

  /**
   * Active l'onglet suivant
   */
  nextTab() {
    const tabs = ["planner", "history", "stats", "scheduler"];
    const currentIndex = tabs.indexOf(this.currentTab);
    const nextIndex = (currentIndex + 1) % tabs.length;
    this.switchTab(tabs[nextIndex]);
  },

  /**
   * Active l'onglet précédent
   */
  previousTab() {
    const tabs = ["planner", "history", "stats", "scheduler"];
    const currentIndex = tabs.indexOf(this.currentTab);
    const prevIndex = currentIndex === 0 ? tabs.length - 1 : currentIndex - 1;
    this.switchTab(tabs[prevIndex]);
  },

  /**
   * Ajoute un indicateur sur un onglet
   */
  addTabIndicator(tabName, count = null, type = "info") {
    const tabElement = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
    if (!tabElement) return;

    this.removeTabIndicator(tabName);

    const indicator = document.createElement("span");
    indicator.className = `tab-indicator tab-indicator-${type}`;
    indicator.dataset.tabIndicator = tabName;

    if (count !== null) {
      indicator.textContent = count > 99 ? "99+" : count.toString();
    } else {
      indicator.innerHTML = "&bull;";
    }

    if (getComputedStyle(tabElement).position === "static") {
      tabElement.style.position = "relative";
    }

    indicator.style.cssText = `
      position: absolute;
      top: -6px;
      right: -6px;
      min-width: 18px;
      height: 18px;
      padding: 0 5px;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-weight: 700;
      color: white;
      background: ${this.getIndicatorColor(type)};
      box-shadow: 0 4px 10px rgba(0,0,0,0.25);
      transform: scale(1);
      transition: transform 0.2s ease;
      z-index: 3;
    `;

    tabElement.appendChild(indicator);

    setTimeout(() => {
      indicator.style.transform = "scale(1.2)";
      setTimeout(() => {
        indicator.style.transform = "scale(1)";
      }, 100);
    }, 10);
  },

  /**
   * Supprime un indicateur d'onglet
   */
  removeTabIndicator(tabName) {
    const indicator = document.querySelector(`[data-tab-indicator="${tabName}"]`);
    if (indicator) {
      indicator.style.transform = "scale(0)";
      setTimeout(() => {
        if (indicator.parentNode) {
          indicator.remove();
        }
      }, 200);
    }
  },

  /**
   * Met à jour le compteur d’un indicateur
   */
  updateTabIndicator(tabName, count, type = "info") {
    const indicator = document.querySelector(`[data-tab-indicator="${tabName}"]`);
    if (indicator) {
      indicator.textContent = count > 99 ? "99+" : count.toString();
      indicator.className = `tab-indicator tab-indicator-${type}`;
      indicator.style.background = this.getIndicatorColor(type);

      indicator.style.transform = "scale(1.3)";
      setTimeout(() => {
        indicator.style.transform = "scale(1)";
      }, 150);
    } else {
      this.addTabIndicator(tabName, count, type);
    }
  },

  /**
   * Couleur d’indicateur
   */
  getIndicatorColor(type) {
    switch (type) {
      case "success":
        return "#22c55e";
      case "warning":
        return "#f59e0b";
      case "error":
        return "#ef4444";
      default:
        return "#6366f1";
    }
  },

  /**
   * Sauvegarde l’état courant
   */
  saveTabState(tabName) {
    try {
      localStorage.setItem("currentTab", tabName);
    } catch (error) {
      console.warn("Impossible de sauvegarder l’état des onglets", error);
    }
  },

  /**
   * Recharge l’état depuis le stockage
   */
  loadTabState() {
    try {
      const savedTab = localStorage.getItem("currentTab") || "planner";
      if (savedTab && this.isValidTab(savedTab)) {
        this.currentTab = savedTab;
      }
    } catch (error) {
      this.currentTab = "planner";
    }

    this.updateTabClasses(this.currentTab);

    ["planner", "history", "stats", "scheduler"].forEach((tabName) => {
      const panel = this.getTabElement(tabName);
      if (!panel) return;

      if (tabName === this.currentTab) {
        panel.classList.add("active");
      } else {
        panel.classList.remove("active");
      }
    });
  },

  /**
   * Vérifie un nom d’onglet
   */
  isValidTab(tabName) {
    return ["planner", "history", "stats", "scheduler"].includes(tabName);
  },

  /**
   * Retourne l’onglet courant
   */
  getCurrentTab() {
    return this.currentTab;
  },

  /**
   * Nettoyage
   */
  destroy() {
    document.querySelectorAll("[data-tab-indicator]").forEach((indicator) => {
      indicator.remove();
    });
    console.log("Module Tabs détruit");
  }
};

// Export global
window.Tabs = Tabs;
