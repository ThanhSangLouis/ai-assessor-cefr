// The prices of the runs, the administrator's side (D078): what a recording, an
// upgraded answer, a reading passage and (D094) a lesson recording cost, how
// many lesson recordings a day are free or allowed, what a run is in IDPoint, the
// free runs each month and the run packs on sale. Saving makes a new version;
// charges already made keep the version they were held under.
(function () {
  const escapeHtml = window.escapeHtml;
  const icon = (name) => window.ui.icon(name);
  const $ = (id) => document.getElementById(id);
  const int = (n) => new Intl.NumberFormat("vi-VN").format(Math.round(Number(n) || 0));
  const when = (iso) => (iso ? new Date(iso).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" }) : "");

  // [key, label, unit, step], in three groups: one field each, the same width.
  const GROUPS = [
    ["Chấm bài", "mic", [
      ["first_minute_runs", "Phút đầu", "lượt", "0.1"],
      ["extra_minute_runs", "Mỗi phút thêm", "lượt", "0.1"],
      ["upgrade_runs", "AI viết lại / soạn bài", "lượt", "0.1"],
      ["passage_runs", "Đoạn đọc AI viết", "lượt", "0.1"],
    ]],
    // D094: a recording on the lesson path, and how many a day are free or allowed.
    ["Bài học", "book-open", [
      ["lesson_minute_runs", "Mỗi phút nói", "lượt", "0.05"],
      ["lesson_free_per_day", "Miễn phí mỗi ngày", "bản ghi", "1"],
      ["lesson_daily_cap", "Tối đa mỗi ngày", "bản ghi", "1"],
    ]],
    ["Ví", "star", [
      ["free_runs", "Miễn phí mỗi tháng", "lượt", "1"],
      ["idpoint_per_run", "Một lượt bằng", "IDPoint", "100"],
    ]],
  ];
  const FIELDS = GROUPS.flatMap(([, , fields]) => fields);

  function packRow(p) {
    const per = p.runs && p.price_vnd ? `${int(p.price_vnd / p.runs)} đ/lượt` : "";
    return `<li class="pack-row">
      <label class="unit-input"><input type="number" min="1" step="1" class="pack-in-runs" value="${Number(p.runs) || ""}" aria-label="Số lượt"><span>lượt</span></label>
      <label class="unit-input"><input type="number" min="1" step="1000" class="pack-in-price" value="${Number(p.price_vnd) || ""}" aria-label="Giá (đồng)"><span>đ</span></label>
      <span class="muted pack-per">${per}</span>
      <button type="button" class="icon-only secondary" data-drop-pack aria-label="Bỏ gói này">${icon("trash")}</button>
    </li>`;
  }

  function field([k, label, unit, step], d) {
    return `<div class="price-field"><label for="price-${k}">${label}</label>
      <span class="unit-input"><input id="price-${k}" type="number" min="0" step="${step}" value="${Number(d[k])}" required><span>${unit}</span></span></div>`;
  }

  function view(d) {
    const source = d.from_settings
      ? '<span class="badge">Mặc định</span>'
      : `<span class="badge state-on">${escapeHtml(d.version)}</span>
         <span class="muted">${escapeHtml(when(d.changed_at))}</span>`;
    const groups = GROUPS.map(
      ([title, mark, fields]) => `<fieldset class="price-group"><legend>${icon(mark)} ${title}</legend>
        ${fields.map((f) => field(f, d)).join("")}</fieldset>`,
    ).join("");
    const history = (d.history || []).length
      ? `<details class="price-history"><summary>${d.history.length} phiên bản trước</summary><ul class="plain-list">${d.history
          .map((h) => `<li>${escapeHtml(h.version || "")} · ${escapeHtml(when(h.changed_at))}</li>`)
          .join("")}</ul></details>`
      : "";
    return `<div class="card-head"><h2 id="prices-h">${icon("star")} Giá lượt</h2><div class="price-source">${source}</div></div>
      ${d.metering ? "" : '<p class="notice">Chưa bật tính lượt: giá chỉ áp dụng khi bật.</p>'}
      <form id="price-form" class="stack" novalidate>
        <div class="price-groups">${groups}</div>
        <fieldset class="price-group price-packs-group"><legend>${icon("plus")} Gói lượt đang bán</legend>
          <ul class="pack-list" id="price-packs">${(d.packs || []).map(packRow).join("")}</ul>
          <button type="button" class="secondary small" id="price-add-pack">${icon("plus")}<span>Thêm gói</span></button>
        </fieldset>
        <div class="button-row"><button type="submit" id="price-save">Lưu giá mới</button>
          <span class="muted">Lượt đã trừ giữ giá cũ.</span></div>
      </form>
      ${history}`;
  }

  function bind(el) {
    const packs = $("price-packs");
    $("price-add-pack").addEventListener("click", () => packs.insertAdjacentHTML("beforeend", packRow({})));
    packs.addEventListener("click", (e) => {
      const drop = e.target.closest("[data-drop-pack]");
      if (drop) drop.closest("li").remove();
    });
    $("price-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = Object.fromEntries(FIELDS.map(([k]) => [k, Number($("price-" + k).value)]));
      body.packs = [...packs.querySelectorAll("li")]
        .map((li) => ({ runs: Number(li.querySelector(".pack-in-runs").value), price_vnd: Number(li.querySelector(".pack-in-price").value) }))
        .filter((p) => p.runs && p.price_vnd);
      if (!body.packs.length) {
        window.toast("Cần ít nhất một gói lượt.", "error");
        return;
      }
      const d = await window.apiJson("/api/v1/admin/prices", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!d) return;
      paint(el, d);
      window.toast(`Đã lưu giá mới (${d.version}).`, "ok");
    });
  }

  function paint(el, d) {
    el.innerHTML = view(d);
    el.hidden = false;
    bind(el);
  }

  async function load() {
    const el = $("prices");
    if (!el) return;
    const d = await window.apiJson("/api/v1/admin/prices");
    if (d) paint(el, d);
  }

  window.adminPrices = { load };
})();
