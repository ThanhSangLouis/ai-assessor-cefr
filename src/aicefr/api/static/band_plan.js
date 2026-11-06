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
    const done = Number(plan.lessons_completed) || 0;
    const total = Number(plan.lessons_total) || 0;
    const pct = total ? Math.min(100, Math.round(done / total * 100)) : 0;
    return `<div class="bp-current">${icon("path", "icon bp-route-icon")}<div class="bp-current-text">` +
      `<h3>Lộ trình hiện tại: ${escapeHtml(range)}</h3>${by ? `<p>${by.trim()}</p>` : ""}</div>` +
      `<div class="bp-progress"><span class="bp-count">${done}/${total} bài</span><div class="bp-meter" role="progressbar" aria-label="Tiến độ lộ trình" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"><span style="width:${pct}%"></span></div>` +
      `<span class="bp-percent">${pct}%</span></div>` +
      `<button type="button" class="bp-remove" id="band-close" aria-label="Bỏ lộ trình" title="Bỏ lộ trình">${icon("trash")}</button></div>`;
  }

  function render(d) {
    const plan = d.plan;
    const goal = (plan && plan.goal) || {};
    const from = goal.band_from || d.suggested_from;
    const to = goal.band_to || d.suggested_to;
    const hint = d.assessed_band ? ` title="Gợi ý từ kết quả đánh giá: ${escapeHtml(d.assessed_band)}"` : "";
    window.clearBusy(box);
    box.innerHTML =
      '<details class="rm-plan-settings"><summary>' +
      `${icon("target", "icon bp-target")}<span class="bp-heading">Lộ trình học</span>` +
      (plan ? `<span class="bp-status">${icon("check")}Đang học</span><span class="bp-collapsed-progress">${escapeHtml(from === to ? from : `${from} → ${to}`)} · ${Number(plan.lessons_completed) || 0}/${Number(plan.lessons_total) || 0} bài</span>` : '') +
      `<span class="bp-toggle" aria-label="Mở hoặc thu gọn chỉnh lộ trình" title="Mở hoặc thu gọn">${icon("chevron-down")}</span></summary>` +
      '<div class="bp-editor"><form id="band-form" class="bp-form"><div class="bp-selection">' +
      `<div class="bp-field"${hint}><select id="band-from" aria-label="Trình độ hiện tại">${options(from)}</select></div>` +
      `<span class="bp-range-arrow" aria-hidden="true">${icon("arrow-right")}</span>` +
      `<div class="bp-field"><select id="band-to" aria-label="Mục tiêu">${options(to)}</select></div>` +
      `</div><button type="submit" class="bp-submit">${icon("refresh")}<span>${plan ? "Cập nhật lộ trình" : "Tạo lộ trình"}</span></button></form>` +
      `<div class="bp-assessment"><a href="/" class="bp-assessment-button">${icon("sparkle")}<span>Kiểm tra trình độ</span></a></div></div>` +
      (plan ? `<div class="bp-plan">${planNote(plan)}</div>` : '') + '</details>';
    wire(d);
    document.dispatchEvent(new CustomEvent("bandplan", { detail: plan || null }));
  }

  function wire(d) {
    if (window.enhanceSelects) window.enhanceSelects(box);
    const form = document.getElementById("band-form");
    const button = form.querySelector("button[type=submit]");
    let saving = false;
    const unchanged = () => !!d.plan &&
      document.getElementById("band-from").value === d.plan.goal.band_from &&
      document.getElementById("band-to").value === d.plan.goal.band_to;
    const syncButton = () => { button.disabled = saving || unchanged(); };
    form.addEventListener("change", syncButton);
    syncButton();
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (saving || unchanged()) return;
      const from = document.getElementById("band-from").value;
      const to = document.getElementById("band-to").value;
      if (BANDS.indexOf(from) > BANDS.indexOf(to)) {
        window.toast("Band mục tiêu phải cao hơn hoặc bằng band bắt đầu.", "error");
        return;
      }
      if (d.plan && d.plan.goal && d.plan.goal.assigned_by &&
          !window.confirm("Lộ trình hiện tại do giảng viên giao. Tạo lộ trình riêng sẽ thay nó, vẫn tạo?")) return;
      saving = true;
      syncButton();
      const made = await window.apiJson("/api/v1/learn/bands", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ band_from: from, band_to: to }),
      });
      saving = false;
      syncButton();
      if (made) {
        window.toast(`Đã tạo lộ trình ${from} → ${to}.`, "ok");
        load();
      }
    });
    const close = document.getElementById("band-close");
    if (close)
      close.addEventListener("click", async () => {
        showRemoveDialog(close);
      });
  }

  function showRemoveDialog(trigger) {
    if (document.getElementById("bp-remove-dialog")) return;
    const dialog = document.createElement("dialog");
    dialog.id = "bp-remove-dialog";
    dialog.className = "bp-remove-dialog";
    dialog.setAttribute("aria-labelledby", "bp-remove-title");
    dialog.setAttribute("aria-describedby", "bp-remove-description");
    dialog.innerHTML = `<div class="bp-dialog-heading"><span class="bp-dialog-mark">${icon("trash")}</span><h2 id="bp-remove-title">Bỏ lộ trình?</h2></div>` +
      `<p id="bp-remove-description">Tiến độ học vẫn được giữ lại.</p>` +
      `<div class="bp-dialog-actions"><button type="button" class="bp-dialog-cancel" autofocus>Hủy</button>` +
      `<button type="button" class="bp-dialog-confirm">${icon("trash")}<span>Bỏ lộ trình</span></button></div>`;
    document.body.appendChild(dialog);
    let removing = false;
    dialog.addEventListener("close", () => {
      dialog.remove();
      if (trigger.isConnected) trigger.focus();
    });
    dialog.addEventListener("cancel", (event) => { if (removing) event.preventDefault(); });
    dialog.querySelector(".bp-dialog-cancel").onclick = () => dialog.close();
    dialog.addEventListener("click", (event) => {
      const rect = dialog.getBoundingClientRect();
      if (!removing && event.target === dialog &&
          (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
    });
    dialog.querySelector(".bp-dialog-confirm").onclick = async () => {
      if (removing) return;
      removing = true;
      const buttons = dialog.querySelectorAll("button");
      buttons.forEach((button) => { button.disabled = true; });
      const label = dialog.querySelector(".bp-dialog-confirm span");
      label.textContent = "Đang bỏ…";
      try {
        if (await window.apiJson("/api/v1/learn/plan", { method: "DELETE" })) {
          dialog.close();
          window.toast("Đã bỏ lộ trình. Tiến độ học vẫn được giữ lại.", "ok");
          load();
        }
      } finally {
        removing = false;
        buttons.forEach((button) => { button.disabled = false; });
        label.textContent = "Bỏ lộ trình";
      }
    };
    dialog.showModal();
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
