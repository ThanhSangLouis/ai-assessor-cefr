// The prices of the runs, the administrator's side (D078): what a recording, a
// practice attempt and an upgraded answer cost, what a run is in IDPoint, the
// free runs each month and the run packs on sale. Saving makes a new version;
// charges already made keep the version they were held under.
(function () {
  const escapeHtml = window.escapeHtml;
  const icon = (name) => window.ui.icon(name);
  const $ = (id) => document.getElementById(id);
  const int = (n) => new Intl.NumberFormat("vi-VN").format(Math.round(Number(n) || 0));
  const when = (iso) => (iso ? new Date(iso).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" }) : "");

  const FIELDS = [
    ["first_minute_runs", "Bài nói đến 1 phút", "lượt", "0.1"],
    ["extra_minute_runs", "Mỗi phút thêm", "lượt", "0.1"],
    ["practice_factor", "Hệ số bài luyện", "× giá bài đánh giá", "0.05"],
    ["upgrade_runs", "Một lần AI viết lại / soạn bài", "lượt", "0.1"],
    ["idpoint_per_run", "Một lượt bằng", "IDPoint", "100"],
    ["free_runs", "Lượt miễn phí mỗi tháng", "lượt / người", "1"],
  ];

  function packRow(p) {
    return `<tr>
      <td><input type="number" min="1" step="1" class="pack-runs" value="${Number(p.runs) || ""}" aria-label="Số lượt"></td>
      <td><input type="number" min="1" step="1000" class="pack-price" value="${Number(p.price_vnd) || ""}" aria-label="Giá (đồng)"></td>
      <td class="muted pack-per">${p.runs && p.price_vnd ? int(p.price_vnd / p.runs) + " đ/lượt" : ""}</td>
      <td><button type="button" class="icon-only secondary" data-drop-pack aria-label="Bỏ gói này">${icon("trash")}</button></td>
    </tr>`;
  }

  function view(d) {
    const source = d.from_settings
      ? '<span class="badge">Đang dùng giá mặc định của máy chủ</span>'
      : `<span class="badge state-on">${escapeHtml(d.version)}</span>
         <span class="muted">đổi lúc ${escapeHtml(when(d.changed_at))}</span>`;
    const fields = FIELDS.map(
      ([k, label, unit, step]) => `<div class="price-field">
        <label for="price-${k}">${label}</label>
        <div class="price-input"><input id="price-${k}" type="number" min="0" step="${step}" value="${Number(d[k])}" required>
          <span class="muted">${unit}</span></div></div>`,
    ).join("");
    const history = (d.history || []).length
      ? `<details class="price-history"><summary>${d.history.length} phiên bản trước</summary><ul class="plain-list">${d.history
          .map((h) => `<li>${escapeHtml(h.version || "")} · ${escapeHtml(when(h.changed_at))}</li>`)
          .join("")}</ul></details>`
      : "";
    return `<div class="card-head"><h2 id="prices-h">${icon("star")} Giá lượt</h2><div class="price-source">${source}</div></div>
      ${d.metering ? "" : '<p class="notice">Bản triển khai này chưa tính lượt (<code>AICEFR_METERING</code> tắt): giá lưu ở đây chỉ áp dụng khi bật.</p>'}
      <form id="price-form" class="stack" novalidate>
        <div class="price-grid">${fields}</div>
        <h3>Gói lượt bán qua Stripe</h3>
        <table class="price-packs"><thead><tr><th>Số lượt</th><th>Giá (đồng)</th><th></th><th></th></tr></thead>
          <tbody id="price-packs">${(d.packs || []).map(packRow).join("")}</tbody></table>
        <div class="button-row">
          <button type="button" class="secondary small" id="price-add-pack">${icon("plus")}<span>Thêm gói</span></button>
        </div>
        <p class="field-hint">Lưu là tạo phiên bản giá mới. Các lượt đã trừ giữ giá lúc trừ.</p>
        <div class="button-row"><button type="submit" id="price-save">Lưu giá mới</button></div>
      </form>
      ${history}`;
  }

  function bind(el) {
    const packs = $("price-packs");
    $("price-add-pack").addEventListener("click", () => packs.insertAdjacentHTML("beforeend", packRow({})));
    packs.addEventListener("click", (e) => {
      const drop = e.target.closest("[data-drop-pack]");
      if (drop) drop.closest("tr").remove();
    });
    $("price-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = Object.fromEntries(FIELDS.map(([k]) => [k, Number($("price-" + k).value)]));
      body.packs = [...packs.querySelectorAll("tr")]
        .map((tr) => ({ runs: Number(tr.querySelector(".pack-runs").value), price_vnd: Number(tr.querySelector(".pack-price").value) }))
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
