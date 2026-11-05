// "Học theo band" (D074): the learner chooses the bands to study, from where
// they are -- suggested by their latest assessment, theirs to change -- to
// where they want to be, and gets a path of the published lessons of those
// bands. A path a teacher assigned takes its place, with who assigned it.
// The bar is the one of the mockup (D092); the roadmap below draws the plan,
// told by a "bandplan" event each time the plan is loaded or changed.
(function () {
  const escapeHtml = window.escapeHtml;
  const icon = (name, cls) => window.ui.icon(name, cls);
  const box = document.getElementById("band-plan");
  if (!box) return;
  const BANDS = ["A1", "A2", "B1", "B2", "C1", "C2"];
  const LEVEL = { A1: "Mới bắt đầu", A2: "Sơ cấp", B1: "Trung cấp", B2: "Trung cao cấp", C1: "Cao cấp", C2: "Thành thạo" };

  const PLAY =
    '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
    '<path d="M7 4.8c0-1 1.1-1.6 2-1.1l11.2 7.2c.8.5.8 1.7 0 2.2L9 20.3c-.9.5-2-.1-2-1.1Z" fill="currentColor"/></svg>';

  const options = (chosen) =>
    BANDS.map((b) => `<option value="${b}"${b === chosen ? " selected" : ""}>${b} · ${LEVEL[b]}</option>`).join("");

  // What the plan in force is, under the bar; nothing when there is none.
  function planNote(plan) {
    if (!plan) return "";
    const goal = plan.goal || {};
    const range = goal.band_from === goal.band_to ? goal.band_from : `${goal.band_from} → ${goal.band_to}`;
    const by = goal.assigned_by
      ? ` do giảng viên <b>${escapeHtml(goal.assigned_by)}</b> giao${goal.path_title ? ` (“${escapeHtml(goal.path_title)}”)` : ""}`
      : "";
    const warnings = (plan.warnings || []).map((w) => `<span class="rm-band-warn">${escapeHtml(w)}</span>`).join("");
    return (
      `<p class="rm-band-note">${icon("path")}<span>Lộ trình đang học: <b>${escapeHtml(range)}</b>${by}, ` +
      `${Number(plan.lessons_completed)}/${Number(plan.lessons_total)} bài.</span>` +
      '<button type="button" class="rm-link" id="band-close">Bỏ lộ trình này</button>' +
      `${warnings}</p>`
    );
  }

  function render(d) {
    const plan = d.plan;
    const goal = (plan && plan.goal) || {};
    const from = goal.band_from || d.suggested_from;
    const to = goal.band_to || d.suggested_to;
    const hint = d.assessed_band ? ` title="Gợi ý từ kết quả đánh giá: ${escapeHtml(d.assessed_band)}"` : "";
    window.clearBusy(box);
    box.innerHTML =
      '<div class="rm-band-bar">' +
      `<h2 class="rm-band-title">${icon("target", "icon rm-band-icon")}Học theo band</h2>` +
      '<form id="band-form" class="rm-band-form">' +
      `<div class="rm-field"${hint}><label for="band-from"><span class="rm-desk">Trình độ hiện tại</span>` +
      '<span class="rm-mob">Học theo band</span></label>' +
      `<select id="band-from">${options(from)}</select></div>` +
      `<div class="rm-field"><label for="band-to">Mục tiêu</label><select id="band-to">${options(to)}</select></div>` +
      '<button type="submit" class="rm-btn rm-btn-orange">' +
      `<span class="rm-mob">${PLAY}</span><span class="rm-desk">Tạo lộ trình</span>` +
      `<span class="rm-mob">Tạo lộ trình học</span><span class="rm-desk">${icon("arrow-right")}</span></button>` +
      "</form>" +
      `<a class="rm-btn rm-btn-outline" href="/">${icon("sparkle")}Kiểm tra trình độ</a>` +
      "</div>" +
      planNote(plan);
    wire(d);
    document.dispatchEvent(new CustomEvent("bandplan", { detail: plan || null }));
  }

  function wire(d) {
    if (window.enhanceSelects) window.enhanceSelects(box);
    const form = document.getElementById("band-form");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const from = document.getElementById("band-from").value;
      const to = document.getElementById("band-to").value;
      if (BANDS.indexOf(from) > BANDS.indexOf(to)) {
        window.toast("Band mục tiêu phải cao hơn hoặc bằng band bắt đầu.", "error");
        return;
      }
      if (d.plan && d.plan.goal && d.plan.goal.assigned_by &&
          !window.confirm("Lộ trình hiện tại do giảng viên giao. Tạo lộ trình riêng sẽ thay nó, vẫn tạo?")) return;
      const button = form.querySelector("button[type=submit]");
      button.disabled = true;
      const made = await window.apiJson("/api/v1/learn/bands", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ band_from: from, band_to: to }),
      });
      button.disabled = false;
      if (made) {
        window.toast(`Đã tạo lộ trình ${from} → ${to}.`, "ok");
        load();
      }
    });
    const close = document.getElementById("band-close");
    if (close)
      close.addEventListener("click", async () => {
        if (!window.confirm("Bỏ lộ trình này? Tiến độ các bài đã học vẫn giữ nguyên.")) return;
        if (await window.apiJson("/api/v1/learn/plan", { method: "DELETE" })) load();
      });
  }

  async function load() {
    const d = await window.apiJson("/api/v1/learn/bands");
    if (d) {
      render(d);
      return;
    }
    // Bands are a learner's: anyone else sees the path alone.
    window.clearBusy(box);
    box.hidden = true;
    document.dispatchEvent(new CustomEvent("bandplan", { detail: null }));
  }

  load();
})();
