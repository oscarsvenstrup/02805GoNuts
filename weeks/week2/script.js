/* Optional enhancement. The entire analysis is readable without JavaScript. */
"use strict";
(async () => {
  const panel = document.getElementById("comparison");
  const rules = {
    random: "Keeps 277 nodes and 1,421 links. It does not keep each character's degree.",
    swapped: "Keeps every character's degree exactly, with no self-links or duplicate links. This is the main test of structure beyond degrees.",
    configuration: "Keeps degrees before cleanup, but merging duplicate links and removing self-links changes them. The original hub loses neighbours."
  };
  try {
    const response = await fetch("../../data/week2/results.json");
    if (!response.ok) throw new Error("Results unavailable");
    const { models } = await response.json();
    const buttons = [...panel.querySelectorAll("button[data-model]")];
    for (const key of Object.keys(rules)) {
      if (![models[key]?.mean, models[key]?.mean_edges_lost, models[key]?.mean_hub_degree].every(Number.isFinite)) {
        throw new Error("Invalid results");
      }
    }
    const show = (key) => {
      document.getElementById("comparison-rule").textContent = rules[key];
      document.getElementById("comparison-clustering").textContent = models[key].mean.toFixed(3);
      document.getElementById("comparison-loss").textContent = models[key].mean_edges_lost.toFixed(2);
      document.getElementById("comparison-hub").textContent = models[key].mean_hub_degree.toFixed(2);
      for (const button of buttons) button.setAttribute("aria-pressed", String(button.dataset.model === key));
    };
    for (const button of buttons) button.addEventListener("click", () => show(button.dataset.model));
    show("swapped");
    panel.hidden = false;
  } catch (error) {
    // The static figure, table, and explanation remain the complete fallback.
    panel.hidden = true;
    console.warn("Optional baseline comparison could not load:", error.message);
  }
})();
