function renderHealth() {
  const health = state.health || {};
  const ami = health.ami || {};
  const apiOk = !health.error;
  const amiOk = ami.connected || ami.status === "connected";
  const schedulerSummary = getSchedulerHealthSummary();
  document.getElementById("apiBadge").className = `pill ${apiOk ? "pill-ok" : "pill-warn"}`;
  document.getElementById("apiBadge").textContent = apiOk ? "API OK" : "Mode demo";
  document.getElementById("amiBadge").className = `pill ${amiOk ? "pill-ok" : "pill-warn"}`;
  document.getElementById("amiBadge").textContent = amiOk ? "AMI connecte" : "AMI non connecte";

  const items = [
    ["API", apiOk ? "Disponible" : "Fallback demo", apiOk ? "pill-ok" : "pill-warn"],
    ["Base de donnees", health.database?.status || "Non verifie", health.database?.status === "ok" ? "pill-ok" : "pill-muted"],
    ["ARI", health.ari?.status || "Non verifie", health.ari?.status === "ok" ? "pill-ok" : "pill-muted"],
    ["AMI", ami.enabled === false ? "Desactive" : ami.status || "Non verifie", amiOk ? "pill-ok" : "pill-warn"],
    ["Planificateur", `${schedulerSummary.activeJobs}/${schedulerSummary.totalJobs} actifs`, schedulerSummary.failedJobs ? "pill-warn" : "pill-info"],
  ];

  document.getElementById("healthGrid").innerHTML = items
    .map(([title, status, cls]) => `<article class="health-card"><strong>${escapeHtml(title)}</strong><span class="pill ${cls}">${escapeHtml(status)}</span></article>`)
    .join("");

  const details = [
    ["API", `Mode: ${health.api?.mode || "prod"} | Statut: ${health.api?.status || "inconnu"}`],
    ["Base de donnees", `Moteur: ${health.database?.engine || "MySQL"} | Statut: ${health.database?.status || "inconnu"}`],
    ["ARI", `URL: ${health.ari?.url || "non renseignee"} | Statut: ${health.ari?.status || "inconnu"}`],
    ["AMI", `Host: ${ami.host || "non renseigne"} | Port: ${ami.port || "-"} | Connecte: ${amiOk ? "oui" : "non"}`],
    ["Planificateur", `Jobs: ${schedulerSummary.totalJobs} | Actifs: ${schedulerSummary.activeJobs} | Erreurs: ${schedulerSummary.failedJobs} | Prochaine: ${schedulerSummary.nextRun}`],
  ];

  document.getElementById("healthDetails").innerHTML = details
    .map(([title, text]) => `<article class="connector-card"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(text)}</span></article>`)
    .join("");
}

function getSchedulerHealthSummary() {
  const jobs = state.schedulerJobs || [];
  const activeJobs = jobs.filter((job) => job.active).length;
  const failedJobs = jobs.filter((job) => String(job.last_run_status || "").toLowerCase() === "failed").length;
  const nextRunDates = jobs
    .map((job) => new Date(job.next_run_time))
    .filter((date) => !Number.isNaN(date.getTime()))
    .sort((a, b) => a - b);

  return {
    totalJobs: jobs.length,
    activeJobs,
    failedJobs,
    nextRun: nextRunDates.length ? formatDate(nextRunDates[0]) : "-",
  };
}
