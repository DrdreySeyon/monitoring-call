function renderSchedulerJobs() {
  const body = document.getElementById("schedulerJobsTable");
  if (!body) return;
  body.innerHTML = state.schedulerJobs
    .map(
      (job) => `
      <tr>
        <td><strong>${escapeHtml(job.scenario_name || `Scenario #${job.scenario_id || "-"}`)}</strong><br><small class="muted">${escapeHtml(job.id || "-")}</small></td>
        <td>${escapeHtml(formatFrequency(job.frequency))}</td>
        <td>${formatDate(job.next_run_time)}</td>
        <td><span class="chip ${job.active ? "chip-ok" : "chip-muted"}">${job.active ? "Actif" : "Pause"}</span></td>
        <td>
          <div class="row-actions">
            <button class="btn btn-small" type="button" data-job-action="run" data-id="${escapeHtml(job.id)}">Lancer</button>
            <button class="btn btn-small" type="button" data-job-action="toggle" data-id="${escapeHtml(job.id)}">${job.active ? "Pause" : "Reprise"}</button>
            <button class="btn btn-small" type="button" data-job-action="edit" data-id="${escapeHtml(job.id)}">Modifier</button>
          </div>
        </td>
      </tr>
    `,
    )
    .join("");

  body.querySelectorAll("[data-job-action]").forEach((button) => {
    button.addEventListener("click", () => handleSchedulerAction(button.dataset.jobAction, button.dataset.id));
  });
}

async function handleSchedulerAction(action, id) {
  const job = state.schedulerJobs.find((item) => String(item.id) === String(id));
  if (!job) return;

  if (action === "edit") {
    document.querySelector("#scheduler select").value = job.scenario_name || "";
    document.querySelector("#scheduler input[type='datetime-local']").focus();
    return;
  }

  if (action === "run") {
    try {
      await runSchedulerJob(id);
    } catch (error) {
      // Action simulee en mode demo local.
    }
    return;
  }

  if (action === "toggle") {
    try {
      const updated = await toggleSchedulerJob(id);
      state.schedulerJobs = state.schedulerJobs.map((item) => (String(item.id) === String(id) ? updated : item));
    } catch (error) {
      state.schedulerJobs = state.schedulerJobs.map((item) =>
        String(item.id) === String(id) ? { ...item, active: !item.active } : item,
      );
    }
    renderSchedulerJobs();
  }
}
