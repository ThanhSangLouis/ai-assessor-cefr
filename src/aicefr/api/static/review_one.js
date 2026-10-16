// Presentation-only controls for the repository's server-rendered M07 review page.
const player = document.getElementById("phat");
const decisionForm = document.getElementById("decision-form");
const actionSelect = document.getElementById("decision-action");
const finalBand = document.getElementById("final-band");
const reason = document.getElementById("reason");

function updateDecisionFields() {
  if (!actionSelect || !finalBand || !reason) return;
  const action = actionSelect.value;
  finalBand.disabled = action !== "OVERRIDE";
  finalBand.required = action === "OVERRIDE";
  reason.required = action === "OVERRIDE";
  if (action !== "OVERRIDE") finalBand.value = "";
}

if (actionSelect) {
  actionSelect.addEventListener("change", updateDecisionFields);
  updateDecisionFields();
}

if (decisionForm) decisionForm.addEventListener("submit", updateDecisionFields);

document.addEventListener("keydown", (event) => {
  if (!player || ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) return;
  if (event.key === " " && !event.target.closest("button, a, summary, audio")) {
    event.preventDefault();
    if (player.paused) player.play().catch(() => {});
    else player.pause();
  } else if (event.key.toLowerCase() === "j") {
    player.currentTime = Math.max(0, player.currentTime - 5);
  } else if (event.key.toLowerCase() === "l") {
    player.currentTime += 5;
  }
});
