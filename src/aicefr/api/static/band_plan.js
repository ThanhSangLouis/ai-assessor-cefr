// "Học theo band" (D074): the learner chooses the bands to study, from where
// they are -- suggested by their latest assessment, theirs to change -- to
// where they want to be, and gets a path of the published lessons of those
// bands. A path a teacher assigned shows in its place, with who assigned it.
(function () {
  const escapeHtml = window.escapeHtml;
  const icon = (name) => window.ui.icon(name);
  const box = document.getElementById("band-plan");
  if (!box) return;
  const BANDS = ["A1", "A2", "B1", "B2", "C1", "C2"];
  const LEVEL = { A1: "Mới bắt đầu", A2: "Sơ cấp", B1: "Trung cấp", B2: "Trung cao cấp", C1: "Cao cấp", C2: "Thành thạo" };
  const STATUS = {
    completed: ["Đã xong", "state-on"],
    started: ["Đang học", "state-warn"],
    new: ["Chưa học", "state-off"],
    unavailable: ["Không còn mở", "state-off"],
  };

  const options = (chosen) =>
    BANDS.map((b) => `<option value="${b}"${b === chosen ? " selected" : ""}>${b} · ${LEVEL[b]}</option>`).join("");

  function chooser(d, plan) {
    const goal = (plan && plan.goal) || {};
    const from = goal.band_from || d.suggested_from;
    const to = goal.band_to || d.suggested_to;
    const hint = d.assessed_band
      ? `Gợi ý từ bài đánh giá gần nhất của bạn: <b>${escapeHtml(d.assessed_band)}</b>. Bạn đổi được.`
      : "Bạn chưa có bài đánh giá nào, nên gợi ý bắt đầu từ A1. Làm một bài đánh giá để có gợi ý sát hơn.";
    return `<form id="band-form" class="band-form">
      <div class="field"><label for="band-from">Bắt đầu từ</label><select id="band-from">${options(from)}</select></div>
      <span class="band-arrow" aria-hidden="true">${icon("arrow-right")}</span>
      <div class="field"><label for="band-to">Mục tiêu</label><select id="band-to">${options(to)}</select></div>
      <button type="submit">${icon("path")} ${plan ? "Tạo lại lộ trình" : "Tạo lộ trình"}</button>
    </form>
    <p class="muted small-note">${hint} Mỗi band khoảng 6 bài, lấy từ các bài giảng viên đã xuất bản.</p>`;
  }

  function lessonsOf(plan) {
    const parts = [];
    plan.units.forEach((u) => {
      const last = parts[parts.length - 1];
      if (last && last.band === u.band) last.lessons.push(...u.lessons);
      else parts.push({ band: u.band, lessons: [...u.lessons] });
    });
    return parts
      .map(
        (p) => `<section class="band-part" aria-label="Band ${escapeHtml(p.band)}">
          <h3><span class="band-badge">${escapeHtml(p.band)}</span> ${escapeHtml(LEVEL[p.band] || "")}</h3>
          <ol class="band-lessons">${p.lessons
            .map((l) => {
              const [label, cls] = STATUS[l.status] || STATUS.new;
              const title = escapeHtml(l.title);
              const link = l.status === "unavailable" ? title : `<a href="/practice/lessons/${encodeURIComponent(l.lesson_id)}">${title}</a>`;
              return `<li><span>${link}</span><span class="badge ${cls}">${label}</span></li>`;
            })
            .join("")}</ol>
        </section>`,
      )
      .join("");
  }

  function render(d) {
    const plan = d.plan;
    window.clearBusy(box);
    if (!plan) {
      box.innerHTML = `<div class="card-head"><h2>${icon("target")} Học theo band</h2></div>
        <p class="muted">Chọn band bạn đang ở và band muốn đạt; hệ thống ghép lộ trình gồm các bài của đúng những band đó.</p>
        ${chooser(d, null)}`;
      wire(d);
      return;
    }
    const goal = plan.goal || {};
    const range = goal.band_from === goal.band_to ? escapeHtml(goal.band_from) : `${escapeHtml(goal.band_from)} → ${escapeHtml(goal.band_to)}`;
    const by = goal.assigned_by
      ? `<p class="band-assigned">${icon("user")} Giảng viên <b>${escapeHtml(goal.assigned_by)}</b> giao lộ trình “${escapeHtml(goal.path_title || "")}”.</p>`
      : "";
    const pct = plan.lessons_total ? Math.round((100 * plan.lessons_completed) / plan.lessons_total) : 0;
    box.innerHTML = `<div class="card-head"><h2>${icon("target")} Lộ trình ${range}</h2>
        <span class="muted">${plan.lessons_completed}/${plan.lessons_total} bài · ${pct}%</span></div>
      ${by}
      <div class="band-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}" aria-label="Tiến độ lộ trình"><span style="width:${pct}%"></span></div>
      ${(plan.warnings || []).map((w) => `<p class="muted small-note">${escapeHtml(w)}</p>`).join("")}
      ${lessonsOf(plan)}
      <details class="band-change"><summary>Đổi band</summary>${chooser(d, plan)}
        <button type="button" class="secondary small" id="band-close">Bỏ lộ trình này</button></details>`;
    wire(d);
  }

  function wire(d) {
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
    if (d) render(d);
  }

  load();
})();
