// Configuration de l'application
const CONFIG = {
  API_BASE_URL: "",
  API_PREFIX: "/api",

  HEALTH_CHECK_INTERVAL: 30000,
  DEFAULT_PAGE_SIZE: 10,
  MAX_PAGE_SIZE: 100,
  TIMER_UPDATE_INTERVAL: 1000,
  DEBOUNCE_DELAY: 500,
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000,

  DTMF_DEFAULT_DELAY: 4,
  DTMF_DEFAULT_INTERVAL: 3000,
  CALL_TIME_DEFAULT: 30,
  CALL_TIME_MAX: 3600
};

const MESSAGES = {
  LOADING: "Chargement...",
  NO_DATA: "Aucune donnée disponible",
  ERROR_NETWORK: "Erreur réseau",
  ERROR_SERVER: "Erreur serveur",
  SUCCESS_SAVE: "Sauvegardé avec succès",
  SUCCESS_DELETE: "Supprimé avec succès",
  CONFIRM_DELETE: "Êtes-vous sûr de vouloir supprimer ?",
  SYSTEM_OK: "Système OK",
  SYSTEM_DEGRADED: "Système dégradé",
  SYSTEM_ERROR: "Système en erreur",
  OFFLINE: "Hors ligne",

  DTMF_INVALID: "Séquence DTMF invalide (chiffres, * et # seulement)",
  DTMF_DELAY_ERROR: "Le délai DTMF doit être inférieur à la durée totale",
  CALL_TIME_INVALID: "La durée d'appel doit être entre 1 et 3600 secondes"
};

const CALL_STATUS = {
  SUCCESS: "success",
  FAILED: "failed",
  IN_PROGRESS: "in_progress"
};

const ENDPOINTS = {
  ROOT: "",
  HEALTH: "/health",
  HEALTH_DETAILED: "/health/detailed",
  CALLS: "/calls",
  CALLS_HISTORY: "/calls/history",
  CALLS_STATS: "/calls/stats",
  SCENARIOS: "/scenarios",
  SCENARIOS: "/scenarios/export",
  SCENARIOS: "/scenarios/import",
  SYSTEM_INFO: "/system/info",
  SYSTEM_METRICS: "/system/metrics"
};

const STATUS_COLORS = {
  success: "#22c55e",
  failed: "#ef4444",
  in_progress: "#3b82f6",
  warning: "#f59e0b",
  info: "#6366f1"
};

window.CONFIG = CONFIG;
window.MESSAGES = MESSAGES;
window.CALL_STATUS = CALL_STATUS;
window.ENDPOINTS = ENDPOINTS;
window.STATUS_COLORS = STATUS_COLORS;


console.log("✓ Configuration chargée avec support DTMF");

