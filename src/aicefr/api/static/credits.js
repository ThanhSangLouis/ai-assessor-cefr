// "My runs" (D049, D053): balance, charges, and buying a run pack.
//
// Two services answer: metering for the balance and the ledger, billing for
// the packs and the orders. A pack is paid on the gateway's own page; the
// runs reach the wallet when the payment is settled, not when this page says so.
const escapeHtml = window.escapeHtml;
const balanceEl = document.getElementById("balance");
const historyEl = document.getElementById("history");

const ACTION = { assessment: "Bài đánh giá", practice: "Bài luyện tập", upgrade: "Bản nâng cấp (AI)", lesson_draft: "Soạn bài bằng AI", drill_passage: "Đoạn đọc (AI)", lesson: "Bản ghi bài học" };
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
    <div class="wallet-hero">
      <div class="wallet-total"><b>${num(total)}</b><span>lượt còn dùng được</span></div>
      <div class="wallet-split">
        <div><span class="wallet-dot free"></span><b>${num(credits.free_runs_left)}</b><span>miễn phí · làm mới ngày 16</span></div>
        <div><span class="wallet-dot paid"></span><b>${num(credits.wallet_runs)}</b><span>đã mua · không hết hạn</span></div>
      </div>
    </div>${credits.free_locked ? verifyNudge(credits.free_runs_per_cycle) : ""}`;
  showPrices(credits.prices, credits.one_minute, credits.lesson);
  historyEl.innerHTML = credits.history.length
    ? `<ul class="ledger">${credits.history.map(ledgerRow).join("")}</ul>`
    : '<p class="muted">Chưa có bài nào được tính lượt.</p>';
  if (packs && packs.on_sale) showPacks(packs);
}

const num = (n) => Number(n).toLocaleString("vi-VN", { maximumFractionDigits: 3 });

// D101: the free runs wait for a verified email.
function verifyNudge(perCycle) {
  return `<a class="verify-nudge" href="/account#email-card">${window.ui.icon("message")}
    <span>Xác minh email để nhận <b>${num(perCycle)} lượt miễn phí</b> mỗi tháng</span></a>`;
}
const icon = (name) => window.ui.icon(name);
const ACTION_ICON = { assessment: "mic", practice: "target", upgrade: "sparkle", lesson_draft: "pencil", drill_passage: "book-open", lesson: "path" };

// One line of the ledger: what, when, and the runs it moved.
function ledgerRow(e) {
  const free = e.free_slot && e.state === "charged";
  const amount = free ? "0" : num(e.state === "charged" ? e.charged_runs : e.held_runs);
  const state = free ? "Miễn phí trong ngày" : STATE[e.state] || escapeHtml(e.state);
  return `<li class="ledger-row">
    <span class="ledger-mark">${icon(ACTION_ICON[e.action] || "star")}</span>
    <span class="ledger-what"><b>${ACTION[e.action] || escapeHtml(e.action)}</b><small>${state} · ${when(e.created_at)}</small></span>
    <span class="ledger-runs${e.state === "released" ? " back" : ""}">${e.state === "released" ? "+" : "−"}${amount}</span></li>`;
}

// The price list as tiles: what one thing costs, in runs, IDPoint underneath.
function showPrices(p, oneMinute, lesson) {
  const tile = (mark, value, label, sub = "") =>
    `<li><span class="cost-mark">${icon(mark)}</span><b>${value}</b><span>${label}</span>${sub ? `<small>${sub}</small>` : ""}</li>`;
  const tiles = [
    tile("mic", num(oneMinute.assessment), "lượt · bài nói 1 phút", `+${num(p.extra_minute_runs)} mỗi phút thêm`),
    tile("sparkle", num(p.upgrade_runs), "lượt · AI viết lại", idp(p.upgrade_runs)),
    tile("book-open", num(p.passage_runs ?? 0.1), "lượt · đoạn đọc AI", idp(p.passage_runs ?? 0.1)),
  ];
  // D094: the lesson path: some recordings a day free, then by the minute.
  if (lesson) {
    tiles.push(
      tile("path", `${Number(lesson.free_left_today)}/${Number(lesson.free_per_day)}`, "bài học miễn phí hôm nay",
        `sau đó ${num(lesson.minute_runs)} lượt/phút`),
    );
  }
  document.getElementById("price-tiles").innerHTML = tiles.join("");
  document.getElementById("price-card").hidden = false;
}

function showPacks(d) {
  document.getElementById("packs-card").hidden = false;
  const test = d.gateways.length && d.gateways.every((g) => !g.live);
  document.getElementById("packs-note").textContent = test ? "Môi trường thử" : "Không hết hạn";
  const select = document.getElementById("gateway");
  select.innerHTML = d.gateways
    .map((g) => `<option value="${escapeHtml(g.name)}">${escapeHtml(g.title)}</option>`)
    .join("");
  document.getElementById("gateway-field").hidden = d.gateways.length < 2;
  const packsEl = document.getElementById("packs");
  const cheapest = Math.min(...d.packs.map((p) => p.per_run_vnd));
  const best = (p) => d.packs.length > 1 && p.per_run_vnd === cheapest;
  packsEl.innerHTML = d.packs
    .map(
      (p) => `<div class="pack${best(p) ? " best" : ""}">${best(p) ? '<span class="pack-flag">Lợi nhất</span>' : ""}
        <div class="pack-runs">${runs(p.runs)}</div>
        <div class="pack-price">${vnd(p.price_vnd)}</div>
        <div class="muted small">${vnd(p.per_run_vnd)}/lượt</div>
        <button type="button" class="button small" data-runs="${p.runs}">Mua gói này</button>
      </div>`,
    )
    .join("");
  packsEl.querySelectorAll("button[data-runs]").forEach((b) =>
    b.addEventListener("click", () => buy(Number(b.dataset.runs), b)),
  );
  const orders = d.orders.filter((o) => o.status !== "expired" || o.credited);
  document.getElementById("orders-card").hidden = !orders.length;
  const PILL = { paid: "state-on", pending: "state-warn", failed: "state-bad" };
  document.getElementById("orders").innerHTML = `<ul class="ledger">${orders
    .map(
      (o) => `<li class="ledger-row">
        <span class="ledger-mark">${icon({ paid: "check-circle", pending: "clock" }[o.status] || "x")}</span>
        <span class="ledger-what"><b>${escapeHtml(o.plan_name)} · ${vnd(o.amount_vnd)}</b>
          <small><span class="badge ${PILL[o.status] || "state-off"}">${escapeHtml(o.status_name)}</span>${
            o.status === "paid" && !o.credited ? " đang cộng lượt" : ""
          } · ${when(o.created_at)}</small></span>
        ${o.status === "paid" ? `<a class="button small secondary" href="/billing/orders/${encodeURIComponent(o.order_id)}/receipt">Biên nhận</a>` : ""}</li>`,
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
