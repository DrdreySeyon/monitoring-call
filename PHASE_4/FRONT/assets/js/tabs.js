function bindTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      activateTab(tab.dataset.tab);
    });
  });
}

function activateInitialTab() {
  const params = new URLSearchParams(window.location.search);
  const tab = params.get("tab") || window.location.hash.replace("#", "");
  if (tab) activateTab(tab);
}

function activateTab(tabName) {
  const tab = document.querySelector(`.tab[data-tab="${CSS.escape(tabName)}"]`);
  const view = document.getElementById(tabName);
  if (!tab || !view) return;
  document.querySelectorAll(".tab, .view").forEach((el) => el.classList.remove("is-active"));
  tab.classList.add("is-active");
  view.classList.add("is-active");
}
