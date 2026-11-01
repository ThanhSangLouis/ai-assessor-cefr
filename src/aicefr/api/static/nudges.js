// Reminders on the learner's home (D055): at most three, the most pressing
// first, each a link to the thing to do. Computed by the server when asked.
(async function () {
  const el = document.getElementById("nudges");
  if (!el) return;
  const r = await fetch("/api/v1/me/nudges");
  if (!r.ok) return;
  const { nudges } = await r.json();
  if (!nudges.length) return;
  const escapeHtml = window.escapeHtml;
  el.innerHTML = nudges
    .map(
      (n) => `<a class="nudge${n.urgent ? " nudge-urgent" : ""}" href="${escapeHtml(n.href)}">
        <span class="nudge-kind">${{ streak: "Chuỗi ngày", reviews: "Ôn tập", goal: "Mục tiêu hôm nay", credits: "Lượt chấm" }[n.kind] || ""}</span>
        <span>${escapeHtml(n.text)}</span></a>`,
    )
    .join("");
  el.hidden = false;
})();
