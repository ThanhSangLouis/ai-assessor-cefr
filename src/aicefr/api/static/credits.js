// "My runs" (D049, D053): balance, charges, and buying a run pack.
//
// Two services answer: metering for the balance and the ledger, billing for
// the packs and the orders. A pack is paid on the gateway's own page; the
// runs reach the wallet when the payment is settled, not when this page says so.
const escapeHtml = window.escapeHtml;
const balanceEl = document.getElementById("balance");
const historyEl = document.getElementById("history");

const ACTION = { assess: "Bài đánh giá", practice: "Bài luyện tập" };
const STATE = { held: "Đang giữ", charged: "Đã trừ", released: "Đã trả lại" };
const runs = (n) => `${Number(n).toLocaleString("vi-VN", { maximumFractionDigits: 3 })} lượt`;
const vnd = (n) => `${Number(n).toLocaleString("vi-VN")} ₫`;
let idpPerRun = 0;
const idp = (r) => `${Math.round(r * idpPerRun).toLocaleString("vi-VN")} IDPoint`;
const when = (iso) => (iso ? new Date(iso).toLocaleString("vi-VN") : "—");

async function load() {
  const [credits, packs] = await Promise.all([
    window.apiJson("/api/v1/me/credits"),
    window.apiJson("/api/v1/me/credit-packs"),
  ]);
  window.clearBusy(balanceEl);
  if (!credits) return;
  if (!credits.metering) {
    balanceEl.innerHTML =
      '<p class="muted">Bản triển khai này không tính lượt: mọi bài đều được chấm.</p>';
    historyEl.innerHTML = "";
    return;
  }
  idpPerRun = credits.prices.idpoint_per_run;
  const total = credits.free_runs_left + credits.wallet_runs;
  balanceEl.innerHTML = `
    <div class="stat-grid">
      <div class="stat"><b>${runs(total)}</b><span>Còn dùng được</span></div>
      <div class="stat"><b>${runs(credits.free_runs_left)}</b><span>Miễn phí chu kỳ ${escapeHtml(credits.cycle)}</span></div>
      <div class="stat"><b>${runs(credits.wallet_runs)}</b><span>Đã mua</span></div>
    </div>
    <p class="muted">Bài đánh giá tới 1 phút: <b>${runs(credits.one_minute.assess)}</b> (${idp(credits.prices.first_minute_runs)}), mỗi phút thêm ${runs(credits.prices.extra_minute_runs)} (${idp(credits.prices.extra_minute_runs)}), tối đa ${credits.prices.max_minutes} phút. Bài luyện tập trả ${Math.round(credits.prices.practice_factor * 100)}%. Lượt miễn phí được dùng trước và làm mới vào ngày 16 hằng tháng.</p>`;
  historyEl.innerHTML = credits.history.length
    ? `<ul class="plain-list">${credits.history
        .map(
          (e) => `<li><b>${ACTION[e.action] || escapeHtml(e.action)}</b> · ${STATE[e.state] || escapeHtml(e.state)}
            · ${e.state === "charged" ? runs(e.charged_runs) : runs(e.held_runs)}
            <span class="muted">· ${when(e.created_at)}</span></li>`,
        )
        .join("")}</ul>`
    : '<p class="muted">Chưa có bài nào được tính lượt.</p>';
  if (packs && packs.on_sale) showPacks(packs);
}

function showPacks(d) {
  document.getElementById("packs-card").hidden = false;
  const test = d.gateways.length && d.gateways.every((g) => !g.live);
  document.getElementById("packs-note").textContent = test
    ? "Môi trường thử: không có tiền thật nào được chuyển."
    : "Lượt mua không hết hạn theo chu kỳ.";
  const select = document.getElementById("gateway");
  select.innerHTML = d.gateways
    .map((g) => `<option value="${escapeHtml(g.name)}">${escapeHtml(g.title)}</option>`)
    .join("");
  document.getElementById("gateway-field").hidden = d.gateways.length < 2;
  const packsEl = document.getElementById("packs");
  packsEl.innerHTML = d.packs
    .map(
      (p) => `<div class="pack">
        <div class="pack-runs">${runs(p.runs)}</div>
        <div class="pack-price">${vnd(p.price_vnd)}</div>
        <div class="muted small">${vnd(p.per_run_vnd)} mỗi lượt</div>
        <button type="button" class="button small" data-runs="${p.runs}">Mua gói này</button>
      </div>`,
    )
    .join("");
  packsEl.querySelectorAll("button[data-runs]").forEach((b) =>
    b.addEventListener("click", () => buy(Number(b.dataset.runs), b)),
  );
  const orders = d.orders.filter((o) => o.status !== "expired" || o.credited);
  document.getElementById("orders-card").hidden = !orders.length;
  document.getElementById("orders").innerHTML = `<ul class="plain-list">${orders
    .map(
      (o) => `<li><code>${escapeHtml(o.order_id)}</code> · ${escapeHtml(o.plan_name)} · ${vnd(o.amount_vnd)}
        · ${escapeHtml(o.status_name)}${o.status === "paid" ? (o.credited ? " · đã cộng lượt" : " · đang cộng lượt") : ""}
        ${o.status === "paid" ? `· <a href="/billing/orders/${encodeURIComponent(o.order_id)}/receipt">biên nhận</a>` : ""}</li>`,
    )
    .join("")}</ul>`;
}

async function buy(n, button) {
  button.disabled = true;
  const d = await window.apiJson("/api/v1/me/credit-orders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ runs: n, gateway: document.getElementById("gateway").value || null }),
  });
  button.disabled = false;
  if (d && d.checkout_url) window.location.assign(d.checkout_url);
}

load();
