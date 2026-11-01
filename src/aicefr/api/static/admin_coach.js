// The language model behind the upgraded answer, the administrator's side
// (D072): today's requests against the provider's daily quota -- or the
// budget, on a paid tier -- then tokens, cost, refusals and errors, and the
// last 14 days. Days are the provider's (Google's ends at midnight Pacific),
// because that is the day its quota counts.
(function () {
  const escapeHtml = window.escapeHtml;
  const icon = (name) => window.ui.icon(name);
  const $ = (id) => document.getElementById(id);
  const PROVIDER = { gemini: "Gemini", groq: "Groq", openrouter: "OpenRouter", anthropic: "Claude", off: "Tắt" };
  // Days the global cap refused someone, out of 14, from which a paid tier is worth weighing.
  const CAP_DAYS_SIGNAL = 3;

  const int = (n) => new Intl.NumberFormat("vi-VN").format(Math.round(Number(n) || 0));
  const usd = (n) =>
    "$" + (Number(n) || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: n && n < 0.01 ? 4 : 2 });
  const dm = (day) => day.slice(8, 10) + "/" + day.slice(5, 7);
  const vnTime = (iso) =>
    new Date(iso).toLocaleTimeString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", hour: "2-digit", minute: "2-digit", hour12: false });
  const retries = (d) => Math.max(0, d.requests - d.upgrades - d.failed);
  const sum = (days, k) => days.reduce((a, d) => a + (Number(d[k]) || 0), 0);

  // ---------------------------------------------------------------- today
  function gauge(d) {
    const t = d.today;
    const budget = d.mode === "budget";
    const used = budget ? t.cost_usd : t.requests;
    const limit = budget ? d.daily_budget_usd : d.daily_requests;
    const share = limit > 0 ? used / limit : 0;
    const level = share >= 1 ? "full" : share >= 0.8 ? "high" : "";
    const fmt = budget ? usd : int;
    const left = Math.max(0, limit - used);
    const what = budget ? "ngân sách hôm nay" : "yêu cầu gửi nhà cung cấp hôm nay";
    return `<div class="coach-gauge ${level}">
      <div class="coach-gauge-head">
        <p class="coach-gauge-num"><b>${fmt(used)}</b> <span>/ ${fmt(limit)}</span></p>
        <p class="muted">${what} · còn <b>${fmt(left)}</b> · ${Math.round(share * 100)}%</p>
      </div>
      <div class="coach-meter" role="meter" aria-valuemin="0" aria-valuemax="${limit}" aria-valuenow="${used}"
           aria-label="${escapeHtml(what)}"><span style="width:${Math.min(100, share * 100).toFixed(1)}%"></span></div>
      <p class="muted coach-reset">Ngày của nhà cung cấp kết thúc lúc <b>${escapeHtml(vnTime(d.resets_at))}</b> (giờ Việt Nam);
        ${budget ? "hết ngân sách" : "hết lượt"} thì mọi người phải chờ tới lúc đó.</p>
    </div>`;
  }

  function stats(d) {
    const t = d.today;
    const per = t.upgrades ? Math.round((t.input_tokens + t.output_tokens) / t.upgrades) : 0;
    const refused = t.refused_global + t.refused_user;
    const tile = (value, label, attention) =>
      `<div class="stat${attention ? " attention" : ""}"><b>${value}</b><span>${label}</span></div>`;
    return `<div class="stat-grid coach-stats">
      ${tile(int(t.upgrades), "bản nâng cấp viết xong")}
      ${tile(int(t.failed), `lỗi · ${int(retries(t))} lần gọi lại`, t.failed > 0)}
      ${tile(int(refused), `bị từ chối · ${int(t.refused_global)} do giới hạn chung, ${int(t.refused_user)} do giới hạn mỗi người`, t.refused_global > 0)}
      ${tile(int(t.accounts), "người dùng")}
      ${tile(int(t.input_tokens + t.output_tokens), `token · ${int(t.input_tokens)} vào, ${int(t.output_tokens)} ra${per ? ` · ~${int(per)} mỗi bản` : ""}`)}
      ${tile(usd(t.cost_usd), d.mode === "budget" ? "chi phí" : "chi phí nếu trả phí")}
    </div>`;
  }

  // ---------------------------------------------------------------- 14 days
  // One bar a day: the requests sent, the part that became an upgrade in the
  // brand colour, failures and retries in amber. The dashed line is the daily
  // cap; a dot over a bar marks a day the cap turned someone away.
  function chart(d) {
    const days = d.days;
    const W = 640, H = 200, L = 36, R = 8, T = 14, B = 24;
    const cap = d.mode === "requests" ? d.daily_requests : 0;
    // Headroom above the cap line and the tallest bar, rounded so the ticks read cleanly.
    const peak = Math.max(cap, ...days.map((x) => x.requests), 1) * 1.08;
    const unit = peak > 200 ? 100 : peak > 40 ? 20 : 5;
    const top = Math.ceil(peak / unit) * unit;
    const step = (W - L - R) / days.length;
    const bw = Math.max(6, step * 0.62);
    const y = (v) => T + (H - T - B) * (1 - v / top);
    const ticks = [0, Math.round(top / 2), top];
    let svg = ticks
      .map((v) => `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"></line>` +
        `<text class="axis-label" x="${L - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${int(v)}</text>`)
      .join("");
    days.forEach((x, i) => {
      const cx = L + step * i + (step - bw) / 2;
      const ok = Math.min(x.upgrades, x.requests);
      const rest = x.requests - ok;
      const title = `${dm(x.day)}: ${int(x.requests)} yêu cầu, ${int(x.upgrades)} bản viết xong, ${int(x.failed)} lỗi, ${int(x.refused_global + x.refused_user)} bị từ chối`;
      svg += `<g><title>${escapeHtml(title)}</title>`;
      if (ok) svg += `<rect class="bar-ok" x="${cx.toFixed(1)}" y="${y(ok).toFixed(1)}" width="${bw.toFixed(1)}" height="${(y(0) - y(ok)).toFixed(1)}" rx="2"></rect>`;
      if (rest) svg += `<rect class="bar-rest" x="${cx.toFixed(1)}" y="${y(x.requests).toFixed(1)}" width="${bw.toFixed(1)}" height="${(y(ok) - y(x.requests)).toFixed(1)}" rx="2"></rect>`;
      if (!x.requests) svg += `<rect class="bar-none" x="${cx.toFixed(1)}" y="${(y(0) - 2).toFixed(1)}" width="${bw.toFixed(1)}" height="2"></rect>`;
      if (x.refused_global) svg += `<circle class="cap-hit" cx="${(cx + bw / 2).toFixed(1)}" cy="${(y(x.requests) - 7).toFixed(1)}" r="3.5"></circle>`;
      if (i % 2 === days.length % 2 || i === days.length - 1)
        svg += `<text class="axis-label${i === days.length - 1 ? " today" : ""}" x="${(cx + bw / 2).toFixed(1)}" y="${H - 6}" text-anchor="middle">${i === days.length - 1 ? "hôm nay" : dm(x.day)}</text>`;
      svg += "</g>";
    });
    if (cap) svg += `<line class="cap-line" x1="${L}" x2="${W - R}" y1="${y(cap).toFixed(1)}" y2="${y(cap).toFixed(1)}"></line>`;
    return `<svg class="trend-chart coach-chart" viewBox="0 0 ${W} ${H}" role="img"
        aria-label="Số yêu cầu gửi nhà cung cấp mỗi ngày trong ${days.length} ngày; số liệu chi tiết ở bảng bên dưới.">${svg}</svg>
      <div class="trend-legend">
        <span><i class="key bar-ok"></i>viết xong</span>
        <span><i class="key bar-rest"></i>lỗi và gọi lại</span>
        ${cap ? `<span><i class="key cap-line"></i>giới hạn ${int(cap)}/ngày</span>` : ""}
        <span><i class="key cap-hit"></i>có người bị từ chối vì giới hạn chung</span>
      </div>`;
  }

  function period(d) {
    const days = d.days;
    const ups = sum(days, "upgrades");
    const tokens = sum(days, "input_tokens") + sum(days, "output_tokens");
    const cost = sum(days, "cost_usd");
    const capDays = days.filter((x) => x.refused_global > 0).length;
    const busiest = Math.max(...days.map((x) => x.requests));
    const errors = {};
    days.forEach((x) => Object.entries(x.errors || {}).forEach(([k, n]) => (errors[k] = (errors[k] || 0) + n)));
    const top = Object.entries(errors).sort((a, b) => b[1] - a[1]).slice(0, 5);
    let h = `<dl class="coach-period">
      <div><dt>Yêu cầu</dt><dd>${int(sum(days, "requests"))}</dd></div>
      <div><dt>Bản viết xong</dt><dd>${int(ups)}</dd></div>
      <div><dt>Ngày cao nhất</dt><dd>${int(busiest)}</dd></div>
      <div><dt>Token</dt><dd>${int(tokens)}</dd></div>
      <div><dt>Chi phí ${d.mode === "budget" ? "" : "nếu trả phí"}</dt><dd>${usd(cost)}</dd></div>
      <div><dt>Mỗi bản</dt><dd>${ups ? usd(cost / ups) : "—"}</dd></div>
    </dl>`;
    if (capDays >= CAP_DAYS_SIGNAL && d.mode === "requests") {
      h += `<div class="notice">${icon("alert")} Giới hạn chung đã từ chối người dùng trong <b>${capDays}/${days.length} ngày</b>.
        Nên chuyển khoá sang gói trả phí rồi đặt <code>AICEFR_COACH_DAILY_BUDGET_USD</code>: giới hạn khi đó tính bằng tiền
        (khoảng ${ups ? usd(cost / ups) : usd(0)} mỗi bản theo giá hiện đặt) thay vì số yêu cầu.</div>`;
    }
    if (top.length) {
      h += `<h3>Lỗi thường gặp</h3><ul class="coach-errors">${top
        .map(([k, n]) => `<li><span>${escapeHtml(k)}</span><b>${int(n)}</b></li>`)
        .join("")}</ul>`;
    }
    return h;
  }

  function table(d) {
    const rows = d.days
      .slice()
      .reverse()
      .map((x) => `<tr>
        <th scope="row">${dm(x.day)}</th><td>${int(x.requests)}</td><td>${int(x.upgrades)}</td>
        <td>${int(x.failed)}</td><td>${int(x.refused_global)} / ${int(x.refused_user)}</td>
        <td>${int(x.accounts)}</td><td>${int(x.input_tokens)}</td><td>${int(x.output_tokens)}</td><td>${usd(x.cost_usd)}</td></tr>`)
      .join("");
    return `<details class="coach-table"><summary>Số liệu từng ngày</summary><table>
      <thead><tr><th scope="col">Ngày</th><th scope="col">Yêu cầu</th><th scope="col">Viết xong</th><th scope="col">Lỗi</th>
      <th scope="col">Từ chối (chung / mỗi người)</th><th scope="col">Người dùng</th><th scope="col">Token vào</th>
      <th scope="col">Token ra</th><th scope="col">Chi phí</th></tr></thead><tbody>${rows}</tbody></table></details>`;
  }

  function head(d) {
    const name = PROVIDER[d.provider] || d.provider;
    const state = d.enabled
      ? '<span class="badge COMPLETED">Đang bật</span>'
      : `<span class="badge REJECTED">Chưa bật</span>`;
    const why = d.enabled
      ? ""
      : d.missing_key
        ? `<p class="muted">Thiếu khoá <code>${escapeHtml(d.missing_key)}</code> trong <code>.env</code> của máy chủ; người học chưa thấy nút "Viết lại ở band cao hơn".</p>`
        : '<p class="muted">Đặt <code>AICEFR_COACH_PROVIDER</code> và khoá của nhà cung cấp trong <code>.env</code> để bật.</p>';
    const mode =
      d.mode === "budget"
        ? `Trả phí · ngân sách <b>${usd(d.daily_budget_usd)}</b>/ngày`
        : `Miễn phí · tối đa <b>${int(d.daily_requests)}</b> yêu cầu/ngày`;
    return `<div class="coach-head">
      <h2>${icon("sparkle")} ${escapeHtml(name)} ${d.model ? `<code>${escapeHtml(d.model)}</code>` : ""} ${state}</h2>
      <p class="muted">${mode} · mỗi người <b>${int(d.per_student_daily)}</b> bản/ngày ·
        giá ${usd(d.price_input_usd)} / ${usd(d.price_output_usd)} cho 1 triệu token vào / ra</p>
      ${why}
    </div>`;
  }

  async function load() {
    const el = $("coach-body");
    let r;
    try {
      r = await fetch("/api/v1/admin/coach");
    } catch (e) {
      window.clearBusy(el);
      el.innerHTML = '<div class="card"><p class="error">Không kết nối được máy chủ.</p></div>';
      return;
    }
    if (window.redirectToLoginIfExpired(r)) return;
    if (!r.ok) {
      window.clearBusy(el);
      el.innerHTML = `<div class="card"><p class="error">Không tải được số liệu (HTTP ${escapeHtml(r.status)}).</p></div>`;
      return;
    }
    const d = await r.json();
    window.clearBusy(el);
    el.innerHTML = `
      <div class="card">${head(d)}${gauge(d)}${stats(d)}</div>
      <div class="card">
        <div class="card-head"><h2>${icon("chart")} ${d.days.length} ngày gần nhất</h2>
          <button type="button" class="secondary small" id="coach-refresh">${icon("refresh")} Làm mới</button></div>
        ${chart(d)}${period(d)}${table(d)}
      </div>`;
    $("coach-refresh").addEventListener("click", load);
  }

  window.adminCoach = { load };
})();
