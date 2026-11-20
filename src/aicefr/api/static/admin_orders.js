// The run-pack orders, the administrator's side (D099): the money of each of the
// last 14 days, how many orders are in each status, every order newest first,
// and, opened one at a time, what the gateway said about it.
(function () {
  const escapeHtml = window.escapeHtml;
  const icon = (name) => window.ui.icon(name);
  const $ = (id) => document.getElementById(id);
  const int = (n) => new Intl.NumberFormat("vi-VN").format(Math.round(Number(n) || 0));
  const dong = (n) => `${int(n)} đ`;
  const when = (iso) =>
    iso
      ? new Date(iso).toLocaleString("vi-VN", {
          timeZone: "Asia/Ho_Chi_Minh",
          day: "2-digit",
          month: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        })
      : "";
  const dayLabel = (iso) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;

  // The statuses of an order (D098), as a chip and the colour of its pill.
  const STATUSES = [
    ["", "Tất cả"],
    ["paid", "Đã trả"],
    ["pending", "Đang chờ"],
    ["expired", "Hết hạn"],
    ["cancelled", "Đã huỷ"],
    ["failed", "Lỗi"],
  ];
  const PILL = { paid: "state-on", pending: "state-warn", failed: "state-bad" };
  // How an event reached the order, for the timeline.
  const KINDS = {
    created: "Tạo đơn",
    checkout: "Mở cổng",
    return: "Người mua quay về",
    notify: "Webhook",
    reconcile: "Tự đối soát",
    credited: "Cộng lượt",
    rejected: "Từ chối",
  };

  let filter = "";

  function chart(days) {
    const top = Math.max(1, ...days.map((d) => d.revenue_vnd));
    const bars = days
      .map((d) => {
        const h = Math.round((d.revenue_vnd / top) * 100);
        const tip = `${dayLabel(d.date)}: ${d.paid} đơn, ${dong(d.revenue_vnd)}`;
        return `<li title="${escapeHtml(tip)}"><span class="order-bar${d.revenue_vnd ? "" : " empty"}" style="--h:${h}%"></span>
          <small>${dayLabel(d.date)}</small><span class="visually-hidden">${escapeHtml(tip)}</span></li>`;
      })
      .join("");
    return `<ol class="order-chart" aria-label="Doanh thu 14 ngày">${bars}</ol>`;
  }

  function tiles(d) {
    const today = d.days[d.days.length - 1] || { paid: 0, revenue_vnd: 0 };
    const total = d.days.reduce((s, x) => s + x.revenue_vnd, 0);
    const waiting = d.counts.pending || 0;
    return `<div class="stat-grid">
      <div class="stat"><b>${dong(today.revenue_vnd)}</b><span>Hôm nay · ${today.paid} đơn</span></div>
      <div class="stat"><b>${dong(total)}</b><span>14 ngày</span></div>
      <div class="stat"><b>${int(d.counts.paid || 0)}</b><span>Đơn đã trả</span></div>
      <div class="stat${waiting ? " attention" : ""}"><b>${int(waiting)}</b><span>Đang chờ</span></div>
    </div>`;
  }

  function row(o) {
    const pill = PILL[o.status] || "state-off";
    return `<tr>
      <td><button type="button" class="link-button order-id" data-order="${escapeHtml(o.order_id)}" aria-expanded="false">${escapeHtml(o.order_id)}</button></td>
      <td>${escapeHtml(o.buyer)}</td>
      <td class="num">${int(o.runs)}</td>
      <td class="num">${dong(o.amount_vnd)}</td>
      <td><span class="badge ${pill}">${escapeHtml(o.status_name)}</span>${o.live ? "" : ' <span class="badge">thử</span>'}</td>
      <td class="muted">${escapeHtml(when(o.created_at))}</td>
    </tr>`;
  }

  function view(d) {
    if (!d.on_sale && !(d.orders || []).length) {
      return `<div class="card empty-state">${icon("inbox")}<p>Chưa bán gói lượt trên bản triển khai này.</p></div>`;
    }
    const chips = STATUSES.map(
      ([value, label]) =>
        `<button type="button" data-status="${value}" aria-pressed="${value === filter}">${label}${
          value && d.counts[value] ? ` · ${int(d.counts[value])}` : ""
        }</button>`,
    ).join("");
    const rows = d.orders.length
      ? d.orders.map(row).join("")
      : `<tr><td colspan="6" class="muted">Không có đơn nào.</td></tr>`;
    return `<section class="card" aria-labelledby="orders-h">
        <div class="card-head"><h2 id="orders-h">${icon("chart")} Doanh thu</h2>
          ${d.live ? '<span class="badge state-on">Tiền thật</span>' : '<span class="badge">Chế độ thử</span>'}</div>
        ${tiles(d)}
        ${chart(d.days)}
      </section>
      <section class="card" aria-label="Danh sách đơn">
        <div class="chips" role="group" aria-label="Lọc theo trạng thái">${chips}</div>
        <div class="table-scroll"><table class="order-table">
          <thead><tr><th>Mã đơn</th><th>Người mua</th><th class="num">Lượt</th><th class="num">Số tiền</th><th>Trạng thái</th><th>Lúc</th></tr></thead>
          <tbody id="order-rows">${rows}</tbody></table></div>
      </section>`;
  }

  function timeline(events) {
    if (!events.length) return '<p class="muted">Chưa có sự kiện.</p>';
    return `<ol class="order-events">${events
      .map((e) => {
        const d = e.detail || {};
        const facts = [d.outcome, d.code, d.reference, d.via, d.amount != null ? dong(d.amount) : ""]
          .filter(Boolean)
          .map((x) => `<code>${escapeHtml(String(x))}</code>`)
          .join(" ");
        const repeats = e.repeats ? ` <span class="badge">×${e.repeats + 1}</span>` : "";
        const kind = e.kind === "rejected" ? "bad" : d.applied ? "ok" : "";
        return `<li class="${kind}"><b>${escapeHtml(KINDS[e.kind] || e.kind)}</b>${repeats}
          <span class="muted">${escapeHtml(when(e.created_at))}</span> ${facts}</li>`;
      })
      .join("")}</ol>`;
  }

  async function toggle(button) {
    const tr = button.closest("tr");
    const open = tr.nextElementSibling;
    if (open && open.classList.contains("order-detail")) {
      open.remove();
      button.setAttribute("aria-expanded", "false");
      return;
    }
    button.setAttribute("aria-expanded", "true");
    tr.insertAdjacentHTML("afterend", '<tr class="order-detail"><td colspan="6"><div class="skeleton skeleton-row"></div></td></tr>');
    const d = await window.apiJson(`/api/v1/admin/credit-orders/${encodeURIComponent(button.dataset.order)}/events`);
    const cell = tr.nextElementSibling.querySelector("td");
    cell.innerHTML = d ? timeline(d.events) : '<p class="muted">Không đọc được.</p>';
  }

  function bind(el) {
    el.querySelectorAll("[data-status]").forEach((b) =>
      b.addEventListener("click", () => {
        filter = b.dataset.status;
        load();
      }),
    );
  }

  let delegated = false;

  async function load() {
    const el = $("orders-body");
    if (!el) return;
    const q = filter ? `?status=${encodeURIComponent(filter)}` : "";
    const d = await window.apiJson(`/api/v1/admin/credit-orders${q}`);
    if (!d) return;
    window.clearBusy && window.clearBusy(el);
    el.innerHTML = view(d);
    bind(el);
    if (!delegated) {
      delegated = true;
      el.addEventListener("click", (e) => {
        const b = e.target.closest("[data-order]");
        if (b) toggle(b);
      });
    }
  }

  window.adminOrders = { load };
})();
