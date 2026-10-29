// The school's plan and its payment, the administrator's side (D033-D035):
// the plans side by side, the plan in force and what is used, buying or
// renewing through one of the payment gateways offered, a licence key from a
// contract.
//
// Students never see this tab or anything from it: the customer is the school
// (BR-29). What a plan adds is a staff tool -- writing the school's own lesson
// paths, class statistics, blind double rating -- and the number of students;
// learning is the same on every plan.
(function () {
  const escapeHtml = window.escapeHtml;
  const icon = (name, cls) => window.ui.icon(name, cls);
  const $ = (id) => document.getElementById(id);
  const STATE = {
    active: ["Đang hiệu lực", "COMPLETED"],
    grace: ["Hết hạn, đang ân hạn", "REVIEW_REQUIRED"],
    free: ["Miễn phí", "QUEUED"],
  };
  const ORDER_BADGE = { paid: "COMPLETED", pending: "QUEUED", failed: "REJECTED", cancelled: "REJECTED" };
  const KIND = {
    new: "Mua mới, có hiệu lực từ hôm nay",
    renewal: "Gia hạn, nối tiếp gói đang dùng",
    upgrade: "Nâng cấp, có hiệu lực từ hôm nay",
    downgrade: "Gói nhỏ hơn, bắt đầu khi gói đang dùng kết thúc",
  };
  const SOURCE = { trial: "dùng thử", order: "mua qua cổng thanh toán", key: "mã giấy phép theo hợp đồng" };
  // Rows every plan has: learning is never what a plan sells (BR-29).
  const ALWAYS = [
    "Sinh viên: bài đánh giá có bằng chứng, lộ trình bài học, ôn tập, thành tựu, tiến độ, tải dữ liệu của mình",
    "Giảng viên: hàng đợi duyệt, sửa kết quả của máy có lý do",
    "Lộ trình mẫu A1 → C2",
  ];
  const SUPPORT = { free: "Tài liệu hướng dẫn", standard: "Giờ hành chính", advanced: "Đào tạo giảng viên, triển khai tại trường" };
  let data = null;
  let quoteTimer = null;
  let lastQuote = null;

  const money = (n) => new Intl.NumberFormat("vi-VN").format(Number(n) || 0) + " đ";
  const dmy = (iso) => window.ui.dmy(iso, "—");
  // Vietnam time, date first, as the receipt and the result page write it.
  const when = (iso) => {
    const d = new Date(iso);
    if (!iso || Number.isNaN(d.getTime())) return "—";
    const zone = { timeZone: "Asia/Ho_Chi_Minh" };
    const day = d.toLocaleDateString("vi-VN", { ...zone, day: "2-digit", month: "2-digit", year: "numeric" });
    const time = d.toLocaleTimeString("vi-VN", { ...zone, hour: "2-digit", minute: "2-digit", hour12: false });
    return `${day} ${time}`;
  };
  const pct = (part, whole) => (whole > 0 ? Math.min(100, Math.round((100 * part) / whole)) : 0);

  const call = window.apiJson;
  const send = (url, method, body) =>
    call(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  // ---------------------------------------------------------------- the ladder
  // The three plans side by side: the rows the school gets on every plan, then
  // what each step up adds, then the numbers. The plan in force is marked.
  function ladder(d) {
    const plans = d.ladder;
    const current = d.enabled ? (d.plan === "trial" ? null : d.plan) : null;
    const head = plans
      .map((p) => {
        const price = p.price_per_student_month
          ? `<b>${money(p.price_per_student_month)}</b><small>/ sinh viên / tháng</small>`
          : "<b>0 đ</b><small>miễn phí, không thời hạn</small>";
        const mark = p.plan === current ? '<span class="badge QUEUED">Đang dùng</span>' : "";
        const best = p.plan === "standard" ? '<span class="ladder-pick">Phổ biến</span>' : "";
        return `<th scope="col" class="ladder-col${p.plan === current ? " is-current" : ""}">${best}<span class="ladder-name">${escapeHtml(p.name)}</span><span class="ladder-price">${price}</span>${mark}</th>`;
      })
      .join("");
    const tick = (on) => (on ? `<td class="ladder-yes">${icon("check")}<span class="visually-hidden">Có</span></td>` : '<td class="ladder-no">—<span class="visually-hidden">Không</span></td>');
    const always = ALWAYS.map((x) => `<tr><th scope="row">${escapeHtml(x)}</th>${plans.map(() => tick(true)).join("")}</tr>`).join("");
    const features = Object.entries(d.feature_names)
      .map(([code, name]) => `<tr class="ladder-gain"><th scope="row">${escapeHtml(name)}</th>${plans.map((p) => tick(p.features.includes(code))).join("")}</tr>`)
      .join("");
    const students = `<tr><th scope="row">Số sinh viên</th>${plans
      .map((p) => `<td>${p.students ? `tối đa ${Number(p.students)}` : "theo số đã mua"}</td>`)
      .join("")}</tr>`;
    const quota = `<tr><th scope="row">Bài đánh giá máy chấm, dự kiến mỗi sinh viên mỗi tháng</th>${plans
      .map((p) => `<td>${Number(p.quota_per_student)}</td>`)
      .join("")}</tr>`;
    const support = `<tr><th scope="row">Hỗ trợ</th>${plans.map((p) => `<td>${escapeHtml(SUPPORT[p.plan] || "")}</td>`).join("")}</tr>`;
    const actions = d.enabled
      ? `<tr class="ladder-actions"><th scope="row"></th>${plans
          .map((p) =>
            p.for_sale
              ? `<td><button type="button" class="${p.plan === "standard" ? "" : "secondary "}small" data-pick="${escapeHtml(p.plan)}">${p.plan === current ? "Gia hạn" : "Chọn gói " + escapeHtml(p.name)}</button></td>`
              : "<td></td>"
          )
          .join("")}</tr>`
      : "";
    return (
      '<section class="card" aria-labelledby="ladder-h">' +
      `<h2 id="ladder-h">So sánh các gói</h2>` +
      `<p class="muted ladder-lede">Gói là của trường, không phải của từng sinh viên. Việc học của sinh viên như nhau ở mọi gói; mỗi bậc thêm công cụ cho giảng viên và số sinh viên dùng được. Trả theo năm học giảm ${Number(d.annual_discount)}%.</p>` +
      '<div class="table-scroll"><table class="ladder">' +
      `<thead><tr><th scope="col"><span class="visually-hidden">Hạng mục</span></th>${head}</tr></thead>` +
      `<tbody>${always}${features}${students}${quota}${support}${actions}</tbody></table></div>` +
      '<p class="muted">Giá trên là giá minh hoạ của môi trường thử, đặt bằng biến môi trường; chưa phải bảng giá.</p>' +
      "</section>"
    );
  }

  function offView(d) {
    return (
      '<div class="notice notice-info"><b>Chế độ thu phí đang tắt.</b> Bản triển khai này chạy như ' +
      "bản nghiên cứu: mọi tính năng mở, không giới hạn số sinh viên, không bán gói. Bật bằng biến " +
      "môi trường <code>AICEFR_BILLING=on</code>.</div>" +
      ladder(d)
    );
  }

  function banners(d) {
    let h = "";
    const problems = d.gateway_problems.length
      ? `<ul class="bill-problems">${d.gateway_problems.map((p) => `<li>${escapeHtml(p)}</li>`).join("")}</ul>`
      : "";
    if (!d.gateways.length) {
      h +=
        '<div class="notice notice-danger"><b>Chưa có cổng thanh toán nào được bật.</b> Kiểm tra ' +
        "<code>AICEFR_PAYMENT_GATEWAYS</code> và khoá của từng cổng; mã giấy phép vẫn cài được." +
        `${problems}</div>`;
    } else if (problems) {
      h += `<div class="notice notice-warn"><b>Cấu hình cổng thanh toán cần xem lại.</b>${problems}</div>`;
    }
    const tests = d.gateways.filter((g) => !g.live).map((g) => escapeHtml(g.title));
    if (tests.length) {
      h +=
        `<div class="notice notice-warn"><b>Môi trường thử: ${tests.join(", ")}.</b> Không có tiền thật ` +
        "nào được chuyển qua các cổng này. Không dùng chúng cho bản triển khai bán thật.</div>";
    }
    if (d.state === "grace") {
      h +=
        `<div class="notice notice-warn"><b>Gói ${escapeHtml(d.plan_name)} đã hết hạn ngày ${dmy(d.license.valid_to)}</b>, ` +
        `vẫn dùng đủ tới ${dmy(d.grace_until)}. Sau đó trường về gói Miễn phí; gia hạn để giữ các công cụ đang dùng.</div>`;
    } else if (d.lapsed) {
      h +=
        `<div class="notice notice-info">Gói ${escapeHtml(d.lapsed.plan_name)} đã kết thúc ngày ${dmy(d.lapsed.valid_to)}; ` +
        "trường đang dùng gói Miễn phí. Mọi thứ đã có vẫn còn: sinh viên học bình thường, lộ trình đã xuất bản vẫn mở.</div>";
    } else if (d.plan === "trial" && d.days_left <= 7) {
      h += `<div class="notice notice-info">Gói dùng thử còn <b>${Number(d.days_left)}</b> ngày, sau đó về gói Miễn phí.</div>`;
    }
    return h;
  }

  function planCard(d) {
    const lic = d.license;
    const [stateName, stateClass] = d.plan === "trial" ? ["Dùng thử", "QUEUED"] : STATE[d.state] || ["", ""];
    const features = Object.entries(d.feature_names)
      .map(([code, name]) => {
        const on = d.features.includes(code);
        return `<li class="${on ? "on" : "off"}">${icon(on ? "check" : "lock")}${escapeHtml(name)}</li>`;
      })
      .join("");
    const next = d.scheduled
      .map(
        (s) =>
          `<p class="bill-next">${icon("hourglass")}Gói đặt trước: <b>${escapeHtml(s.plan_name)}</b>, ` +
          `${Number(s.seats)} sinh viên, từ ${dmy(s.valid_from)} đến ${dmy(s.valid_to)}.</p>`
      )
      .join("");
    const facts = lic
      ? '<dl class="bill-facts">' +
        `<dt>Hiệu lực</dt><dd>${dmy(lic.valid_from)} – ${dmy(lic.valid_to)}</dd>` +
        `<dt>Còn lại</dt><dd>${d.state === "active" ? `${Number(d.days_left)} ngày` : `dùng đủ tới ${dmy(d.grace_until)}`}</dd>` +
        `<dt>Sinh viên</dt><dd>tối đa ${Number(lic.seats)}</dd>` +
        "</dl>"
      : `<dl class="bill-facts"><dt>Sinh viên</dt><dd>tối đa ${Number(d.students_allowed)}</dd><dt>Thời hạn</dt><dd>không thời hạn</dd></dl>`;
    const who = lic ? `${escapeHtml(lic.organization)} · ${escapeHtml(SOURCE[lic.source] || lic.source)}` : escapeHtml(d.organization || "Chưa đặt tên tổ chức");
    return (
      '<section class="card bill-plan" aria-labelledby="bill-plan-h">' +
      `<div class="card-head"><h2 id="bill-plan-h">Gói đang dùng</h2><span class="badge ${stateClass}">${stateName}</span></div>` +
      `<p class="bill-plan-name">${escapeHtml(d.plan_name)}</p>` +
      `<p class="muted">${who}</p>` +
      facts +
      next +
      `<ul class="bill-features">${features}</ul>` +
      "</section>"
    );
  }

  function meter(label, part, whole, warn) {
    const p = pct(part, whole);
    return (
      '<div class="bill-meter">' +
      `<div class="bill-meter-head"><span>${label}</span><b>${Number(part)} / ${Number(whole)}</b></div>` +
      `<div class="progress-bar small${warn ? " failed" : ""}" role="progressbar" aria-label="${escapeHtml(label)}"` +
      ` aria-valuemin="0" aria-valuemax="${Number(whole)}" aria-valuenow="${Number(part)}"><span style="width:${p}%"></span></div>` +
      "</div>"
    );
  }

  function usageCard(d) {
    const u = d.usage;
    let warn = "";
    if (u.warning) {
      warn =
        `<div class="notice notice-warn">Đã dùng <b>${Number(u.percent)}%</b> số bài đánh giá dự kiến của ` +
        "tháng. Đây chỉ là cảnh báo: sinh viên vẫn nộp bài và được chấm bình thường; phần vượt được " +
        "ghi lại để tính theo hợp đồng.</div>";
    }
    return (
      '<section class="card" aria-labelledby="bill-use-h"><h2 id="bill-use-h">Mức đang dùng</h2>' +
      meter("Sinh viên đang có tài khoản", u.students, d.students_allowed, u.students >= d.students_allowed) +
      meter(`Bài đánh giá tháng ${escapeHtml(u.month)}`, u.assessments, u.quota, Boolean(u.warning)) +
      warn +
      "</section>"
    );
  }

  function buyCard(d) {
    const forSale = d.ladder.filter((p) => p.for_sale);
    const chosen = forSale.some((p) => p.plan === d.plan) ? d.plan : "standard";
    const lic = d.license;
    const seats = lic && lic.source !== "trial" ? lic.seats : Math.max(d.limits.min_students, Math.ceil(Math.max(d.usage.students, 30) / 10) * 10);
    const plans = forSale
      .map(
        (p) =>
          '<label class="bill-option">' +
          `<input type="radio" name="bill-plan" value="${escapeHtml(p.plan)}"${p.plan === chosen ? " checked" : ""}>` +
          `<span><b>${escapeHtml(p.name)}</b><small>${money(p.price_per_student_month)} / sinh viên / tháng</small></span>` +
          "</label>"
      )
      .join("");
    const terms = d.terms
      .map((m) => `<option value="${Number(m)}">${Number(m) === 12 ? `12 tháng (giảm ${Number(d.annual_discount)}%)` : `${Number(m)} tháng`}</option>`)
      .join("");
    // D035. Every gateway offered, the first one picked; its test note under it.
    const gateways = d.gateways
      .map(
        (g, i) =>
          '<label class="bill-option bill-gateway">' +
          `<input type="radio" name="bill-gateway" value="${escapeHtml(g.name)}"${i === 0 ? " checked" : ""}>` +
          `<span><b>${escapeHtml(g.title)}${g.live ? "" : ' <em class="badge QUEUED">Thử</em>'}</b>` +
          `<small>${escapeHtml(g.methods)}</small>` +
          (g.note ? `<small class="bill-gateway-note">${escapeHtml(g.note)}</small>` : "") +
          "</span></label>"
      )
      .join("");
    return (
      '<section class="card" id="bill-buy" aria-labelledby="bill-buy-h">' +
      `<h2 id="bill-buy-h">${icon("arrow-up")} Nâng cấp hoặc gia hạn</h2>` +
      '<form id="bill-form" class="bill-form" novalidate>' +
      `<fieldset class="bill-options"><legend>Gói</legend>${plans}</fieldset>` +
      `<div class="field"><label for="bill-seats">Số sinh viên</label><input id="bill-seats" type="number" inputmode="numeric" min="${Number(d.limits.min_students)}" max="${Number(d.limits.max_students)}" value="${Number(seats)}"></div>` +
      `<div class="field"><label for="bill-months">Thời hạn</label><select id="bill-months">${terms}</select></div>` +
      (gateways ? `<fieldset class="bill-options"><legend>Thanh toán qua</legend>${gateways}</fieldset>` : "") +
      "</form>" +
      '<p class="muted bill-hint">Số sinh viên là số tài khoản sinh viên trường được mở cùng lúc. Tài khoản giảng viên và quản trị không tính.</p>' +
      '<div id="bill-quote" class="bill-quote" aria-live="polite"></div>' +
      `<button type="button" id="bill-pay" disabled>${icon("lock")}<span>Thanh toán</span></button>` +
      "</section>"
    );
  }

  function ordersCard(d) {
    if (!d.orders.length) return "";
    const rows = d.orders
      .map(
        (o) =>
          `<tr><td><code>${escapeHtml(o.order_id)}</code></td><td>${when(o.created_at)}</td>` +
          `<td>${escapeHtml(o.plan_name)}, ${Number(o.seats)} sinh viên, ${Number(o.months)} tháng</td>` +
          `<td>${escapeHtml(o.gateway_title)}${o.live || o.gateway === "none" ? "" : " (thử)"}</td>` +
          `<td class="num">${money(o.amount_vnd)}</td>` +
          `<td><span class="badge ${ORDER_BADGE[o.status] || ""}">${escapeHtml(o.status_name)}</span></td>` +
          `<td>${o.status === "paid" ? `<a href="/billing/orders/${encodeURIComponent(o.order_id)}/receipt">Biên nhận</a>` : ""}</td></tr>`
      )
      .join("");
    return (
      '<section class="card" aria-labelledby="bill-orders-h"><h2 id="bill-orders-h">Đơn hàng</h2>' +
      '<table><thead><tr><th>Mã đơn</th><th>Đặt lúc</th><th>Nội dung</th><th>Cổng</th><th class="num">Số tiền</th>' +
      `<th>Trạng thái</th><th></th></tr></thead><tbody>${rows}</tbody></table></section>`
    );
  }

  function settingsCard(d) {
    const keyForm = d.key_install
      ? '<textarea id="bill-key" rows="3" spellcheck="false" placeholder="AICEFR1.…"></textarea>' +
        '<button type="button" id="bill-key-install" class="secondary">Cài mã giấy phép</button>'
      : '<p class="muted">Bản triển khai này chưa đặt <code>AICEFR_LICENSE_SECRET</code> nên chưa cài được mã giấy phép.</p>';
    return (
      '<section class="card" aria-labelledby="bill-org-h"><h2 id="bill-org-h">Tổ chức và hợp đồng</h2>' +
      '<form id="bill-org-form" class="inline-form" novalidate><div class="field">' +
      '<label for="bill-org">Tên tổ chức trên giấy phép và biên nhận</label>' +
      `<input id="bill-org" maxlength="160" autocomplete="organization" value="${escapeHtml(d.organization)}" placeholder="Ví dụ: Khoa Ngoại ngữ, Trường Đại học …">` +
      '</div><button type="submit" class="secondary">Lưu tên</button></form>' +
      '<details class="bill-key"><summary>Có mã giấy phép từ hợp đồng?</summary>' +
      '<p class="muted">Trường thanh toán theo hợp đồng và hoá đơn thì nhận một mã giấy phép; dán vào đây để kích hoạt.</p>' +
      keyForm +
      "</details></section>"
    );
  }

  function enabledView(d) {
    return (
      banners(d) +
      '<div class="bill-grid">' +
      planCard(d) +
      usageCard(d) +
      "</div>" +
      ladder(d) +
      buyCard(d) +
      ordersCard(d) +
      settingsCard(d)
    );
  }

  // ---------------------------------------------------------------- quote and pay
  function chosenPurchase() {
    const plan = document.querySelector('input[name="bill-plan"]:checked');
    return {
      plan: plan ? plan.value : "",
      seats: Number($("bill-seats").value),
      months: Number($("bill-months").value),
    };
  }

  function chosenGateway() {
    const picked = document.querySelector('input[name="bill-gateway"]:checked');
    return data.gateways.find((g) => picked && g.name === picked.value) || null;
  }

  async function refreshQuote() {
    const box = $("bill-quote");
    const pay = $("bill-pay");
    if (!box || !pay) return;
    pay.disabled = true;
    lastQuote = null;
    const r = await fetch("/api/v1/admin/billing/quote", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(chosenPurchase()),
    });
    if (window.redirectToLoginIfExpired(r)) return;
    const q = await r.json().catch(() => ({}));
    if (!r.ok) {
      const why = Array.isArray(q.detail)
        ? `Số sinh viên từ ${data.limits.min_students} đến ${data.limits.max_students}.`
        : q.detail;
      box.innerHTML = `<p class="error">${escapeHtml(why || "Không báo giá được.")}</p>`;
      return;
    }
    lastQuote = q;
    box.innerHTML =
      '<dl class="bill-facts">' +
      `<dt>Loại</dt><dd>${escapeHtml(KIND[q.kind] || q.kind)}</dd>` +
      `<dt>Thời hạn</dt><dd>${dmy(q.starts_on)} – ${dmy(q.ends_on)}</dd>` +
      `<dt>Giá</dt><dd>${Number(q.seats)} sinh viên × ${Number(q.months)} tháng × ${money(q.unit_price)} = ${money(q.list_vnd)}</dd>` +
      (q.discount_vnd ? `<dt>Giảm trả theo năm</dt><dd>−${money(q.discount_vnd)}</dd>` : "") +
      (q.credit_vnd ? `<dt>Trừ phần chưa dùng của gói cũ</dt><dd>−${money(q.credit_vnd)}</dd>` : "") +
      `<dt>Cần thanh toán</dt><dd class="bill-total">${money(q.amount_vnd)}</dd>` +
      "</dl>";
    // Plain text, not HTML: the gateway's name goes in as it is.
    const via = chosenGateway();
    const through = via ? " qua " + via.title : "";
    pay.querySelector("span").textContent = q.amount_vnd
      ? `Thanh toán ${money(q.amount_vnd)}${through}`
      : "Kích hoạt, không cần thanh toán";
    pay.disabled = false;
  }

  function queueQuote() {
    clearTimeout(quoteTimer);
    quoteTimer = setTimeout(refreshQuote, 250);
  }

  async function pay() {
    if (!lastQuote) return;
    const button = $("bill-pay");
    button.disabled = true;
    button.querySelector("span").textContent = "Đang tạo đơn…";
    const via = chosenGateway();
    const d = await send("/api/v1/admin/billing/orders", "POST", { ...chosenPurchase(), gateway: via ? via.name : null });
    if (!d) {
      button.disabled = false;
      refreshQuote();
      return;
    }
    if (d.checkout_url) {
      button.querySelector("span").textContent = "Đang chuyển tới cổng thanh toán…";
      window.location.assign(d.checkout_url);
      return;
    }
    window.toast("Đã kích hoạt gói " + d.order.plan_name + ".", "ok");
    load();
  }

  // ---------------------------------------------------------------- wiring
  async function load() {
    const el = $("billing-body");
    const d = await call("/api/v1/admin/billing");
    window.clearBusy(el);
    if (!d) {
      el.innerHTML = '<p class="error">Không tải được gói dịch vụ.</p>';
      return;
    }
    data = d;
    el.innerHTML = d.enabled ? enabledView(d) : offView(d);
    window.wrapTables(el);
    wire();
    if (d.enabled) refreshQuote();
  }

  // The container's click handler outlives each render, so it is added once;
  // the form's handlers are on elements drawn anew by every render.
  let bodyWired = false;
  function wire() {
    const form = $("bill-form");
    if (form) {
      form.addEventListener("change", queueQuote);
      form.addEventListener("input", queueQuote);
      form.addEventListener("submit", (e) => e.preventDefault());
      $("bill-pay").addEventListener("click", pay);
    }
    if (!bodyWired) {
      bodyWired = true;
      $("billing-body").addEventListener("click", (e) => {
        const b = e.target.closest("[data-pick]");
        if (!b) return;
        const radio = document.querySelector(`input[name="bill-plan"][value="${b.dataset.pick}"]`);
        if (!radio) return;
        radio.checked = true;
        queueQuote();
        $("bill-buy").scrollIntoView({ block: "start" });
        $("bill-seats").focus({ preventScroll: true });
      });
    }
    const org = $("bill-org-form");
    if (org) {
      org.addEventListener("submit", async (e) => {
        e.preventDefault();
        const d = await send("/api/v1/admin/billing/organization", "PATCH", { name: $("bill-org").value });
        if (d) {
          window.toast("Đã lưu tên tổ chức.", "ok");
          load();
        }
      });
    }
    const install = $("bill-key-install");
    if (install) {
      install.addEventListener("click", async () => {
        const d = await send("/api/v1/admin/billing/license", "POST", { key: $("bill-key").value });
        if (d) {
          window.toast("Đã cài giấy phép gói " + d.plan_name + " đến " + dmy(d.valid_to) + ".", "ok");
          load();
        }
      });
    }
  }

  window.adminBilling = { load };
})();
