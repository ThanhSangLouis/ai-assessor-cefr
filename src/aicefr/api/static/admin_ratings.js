// Blind double rating, the administrator's side (D030): create batches, follow
// them, send disagreements to a third rater, read the agreement report.
//
// The report reads top to bottom in the order the analysis must be read:
// first how far the two humans agree, then how far the machine agrees with
// them. Every number carries how many responses it rests on and, where the
// server computed one, its 95% interval over speakers.
(function () {
  const escapeHtml = window.escapeHtml;
  const $ = (id) => document.getElementById(id);
  const ROLE = { teacher: "Giảng viên", admin: "Quản trị" };
  const CRITERION = {
    range: "Vốn từ",
    accuracy: "Ngữ pháp",
    fluency: "Độ trôi chảy",
    coherence: "Mạch lạc",
    phonology: "Phát âm dễ nghe",
  };
  const BANDS = ["A2", "B1", "B2"];
  let raters = [];

  const call = window.apiJson;

  const post = (url, body) =>
    call(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });

  async function whileDisabled(button, action) {
    if (button.disabled) return null;
    button.disabled = true;
    try {
      return await action();
    } finally {
      button.disabled = false;
    }
  }

  // ---------------------------------------------------------------- setup
  async function loadSetup() {
    const d = await call("/api/v1/admin/ratings/setup");
    if (!d) return;
    raters = d.raters || [];
    $("batch-eligible").innerHTML =
      `Bài đủ điều kiện chấm mù: <b>${d.eligible_responses}</b> ` +
      "(bài có bản ghi, người học đang đồng thuận cho nghiên cứu).";
    $("batch-limit").placeholder = String(d.eligible_responses || "");
    $("batch-raters").innerHTML = raters.length
      ? raters
          .map(
            (r) =>
              `<label class="check-row"><input type="checkbox" value="${escapeHtml(r.actor_id)}">` +
              ` ${escapeHtml(r.actor_id)} <span class="muted">· ${escapeHtml(ROLE[r.role] || r.role)}</span></label>`
          )
          .join("")
      : '<p class="muted">Chưa có tài khoản giảng viên nào. Tạo ở tab Tài khoản.</p>';
  }

  $("batch-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const chosen = [...$("batch-raters").querySelectorAll("input:checked")].map((i) => i.value);
    const name = $("batch-name").value.trim();
    if (name.length < 3) {
      window.toast("Hãy đặt tên đợt (từ 3 ký tự).", "error");
      $("batch-name").focus();
      return;
    }
    if (chosen.length < 2) {
      window.toast("Cần chọn ít nhất hai giám khảo.", "error");
      return;
    }
    const body = { name, rater_ids: chosen, only_new: $("batch-only-new").checked };
    const limit = Number($("batch-limit").value);
    if (limit > 0) body.limit = limit;
    const seed = $("batch-seed").value.trim();
    if (seed !== "") body.seed = Number(seed);
    if ($("batch-form").dataset.submitting === "true") return;
    $("batch-form").dataset.submitting = "true";
    let d;
    try {
      d = await whileDisabled($("batch-create"), () => post("/api/v1/admin/ratings/batches", body));
    } finally {
      $("batch-form").dataset.submitting = "false";
    }
    if (!d) return;
    window.toast(
      `Đã tạo đợt: ${d.responses} bài, ${chosen.length} giám khảo, ${d.assignments} phiếu, hạt giống ${d.seed}.` +
        (d.skipped
          ? ` ${d.skipped} bài không được gán đủ hai phiếu.`
          : ""),
      "ok"
    );
    $("batch-form").reset();
    loadSetup();
    loadBatches();
  });

  // ---------------------------------------------------------------- batches
  function batchRow(b) {
    const open = b.state === "OPEN";
    const adjudicators = raters
      .map((r) => `<option value="${escapeHtml(r.actor_id)}">${escapeHtml(r.actor_id)}</option>`)
      .join("");
    const id = escapeHtml(b.batch_id);
    const shortId = escapeHtml(String(b.batch_id).slice(0, 8));
    return `<tr>
      <td><b>Đợt ${shortId}</b><span class="cell-sub">${escapeHtml(window.ui.localTime(b.created_at))} · seed ${b.seed}</span>
        <span class="cell-sub">${open ? '<span class="badge COMPLETED">Đang mở</span>' : '<span class="badge">Đã đóng</span>'}</span></td>
      <td>${b.submitted}/${b.assignments} phiếu đã nộp${b.void ? ` · ${b.void} phiếu không còn mù` : ""}</td>
      <td>${b.needs_adjudication ? `<b>${b.needs_adjudication}</b> bài cần phân xử` : '<span class="muted">Không có</span>'}
        ${b.needs_adjudication && open
          ? `<span class="adjudicate-form"><label class="visually-hidden" for="adj-${id}">Người phân xử</label>
             <select id="adj-${id}">${adjudicators}</select>
             <button type="button" class="small" data-adjudicate="${id}">Giao phân xử</button></span>`
          : ""}
        ${b.void
          ? `<span class="adjudicate-form"><label class="visually-hidden" for="rep-${id}">Giám khảo nhận lại</label>
             <select id="rep-${id}">${adjudicators}</select>
             <button type="button" class="small secondary" data-replace="${id}">Giao lại ${b.void} phiếu</button></span>`
          : ""}</td>
      <td class="action-cell"><div class="row-actions">
        <button type="button" class="small" data-report="${id}">Báo cáo</button>
        <a class="button small secondary" href="/api/v1/admin/ratings/batches/${encodeURIComponent(b.batch_id)}/export.csv">CSV</a>
        <button type="button" class="small secondary" data-status="${open ? "close" : "reopen"}" data-batch="${id}">${open ? "Đóng" : "Mở lại"}</button>
      </div></td>
    </tr>`;
  }

  async function loadBatches() {
    const el = $("batches-body");
    const data = await call("/api/v1/admin/ratings/batches");
    window.clearBusy(el);
    if (!data) return;
    const rows = Array.isArray(data.batches) ? data.batches : [];
    el.innerHTML = rows.length
      ? `<table><thead><tr><th>Đợt</th><th>Tiến độ</th><th>Phân xử</th><th>Thao tác</th></tr></thead>
         <tbody>${rows.map(batchRow).join("")}</tbody></table>`
      : '<p class="muted">Chưa có đợt chấm nào.</p>';
  }

  $("batches-body").addEventListener("click", async (e) => {
    const report = e.target.closest("[data-report]");
    if (report) {
      openReport(report.dataset.report);
      return;
    }
    const adjudicate = e.target.closest("[data-adjudicate]");
    if (adjudicate) {
      const batch = adjudicate.dataset.adjudicate;
      const who = $(`adj-${batch}`).value;
      adjudicate.disabled = true;
      const d = await post(`/api/v1/admin/ratings/batches/${encodeURIComponent(batch)}/adjudicate`, {
        adjudicator_id: who,
      });
      adjudicate.disabled = false;
      if (!d) return;
      window.toast(
        `Đã giao ${d.created} bài phân xử` +
          (d.skipped_own ? `; ${d.skipped_own} bài bỏ qua vì người này đã chấm bài đó` : "") +
          (d.skipped_seen ? `; ${d.skipped_seen} bài bỏ qua vì người này đã xem kết quả của máy` : "") +
          ".",
        "ok"
      );
      loadBatches();
      return;
    }
    const replace = e.target.closest("[data-replace]");
    if (replace) {
      const batch = replace.dataset.replace;
      const who = $(`rep-${batch}`).value;
      replace.disabled = true;
      const d = await post(`/api/v1/admin/ratings/batches/${encodeURIComponent(batch)}/replace`, {
        rater_id: who,
      });
      replace.disabled = false;
      if (!d) return;
      window.toast(
        `Đã giao lại ${d.created} phiếu` +
          (d.skipped_own ? `; ${d.skipped_own} phiếu bỏ qua vì người này đã chấm bài đó` : "") +
          (d.skipped_seen ? `; ${d.skipped_seen} phiếu bỏ qua vì người này đã xem kết quả của máy` : "") +
          ".",
        "ok"
      );
      loadBatches();
      return;
    }
    const status = e.target.closest("[data-status]");
    if (status) {
      if (status.disabled) return;
      const action = status.dataset.status;
      if (
        action === "close" &&
        !window.confirm(
          "Đóng đợt? Giám khảo không nộp thêm phiếu được và sẽ xem được kết quả của máy cho các bài này." +
            " Ai đã xem thì phiếu đó không nhận điểm nữa, kể cả khi mở lại đợt."
        )
      )
        return;
      await whileDisabled(status, async () => {
        const d = await post(
          `/api/v1/admin/ratings/batches/${encodeURIComponent(status.dataset.batch)}/${action}`
        );
        if (d) loadBatches();
      });
    }
  });

  // ---------------------------------------------------------------- report
  const fmt = (v, digits = 2) => (v === null || v === undefined ? "—" : Number(v).toFixed(digits));
  const ci = (m) =>
    m && m.ci ? ` <span class="muted">[${fmt(m.ci[0])}; ${fmt(m.ci[1])}]</span>` : "";
  const metric = (m, digits = 2) => (m ? `<b>${fmt(m.value, digits)}</b>${ci(m)}` : "—");

  function confusionTable(matrix, rowLabel, colLabel) {
    const head = `<tr><th>${escapeHtml(rowLabel)} \\ ${escapeHtml(colLabel)}</th>${BANDS.map((b) => `<th>${b}</th>`).join("")}</tr>`;
    const body = matrix
      .map((row, i) => `<tr><th>${BANDS[i]}</th>${row.map((n) => `<td>${n}</td>`).join("")}</tr>`)
      .join("");
    return `<table class="confusion">${head}${body}</table>`;
  }

  function reportHtml(d) {
    const r = d.report;
    const h = r.human_human;
    const m = r.machine_human;
    const c = r.counts;
    const criteria = Object.entries(h.per_criterion)
      .map(([k, v]) => `<tr><td>${escapeHtml(CRITERION[k] || k)}</td><td>${fmt(v.pearson)}</td><td>${v.n}</td></tr>`)
      .join("");
    const perBand = Object.entries(m.per_band)
      .map(
        ([band, v]) =>
          `<tr><td>${band}</td><td>${v.support}</td><td>${fmt(v.recall)}</td><td>${fmt(v.precision)}</td></tr>`
      )
      .join("");
    const notes = r.notes.length
      ? `<details><summary>${r.notes.length} ghi chú về chỉ số không tính được</summary><ul>${r.notes
          .map((n) => `<li><code>${escapeHtml(n)}</code></li>`)
          .join("")}</ul></details>`
      : "";
    return `<div class="sheet-head"><div><h2 id="report-h">Báo cáo đồng thuận · Đợt ${escapeHtml(String(d.batch_id).slice(0, 8))}</h2>
        <p class="muted">${c.responses} bài · ${c.speakers} người nói · ${c.rated_twice} bài đủ hai phiếu ·
        ${c.adjudicated} đã phân xử, ${c.pending} chờ phân xử · ${c.unscorable} không chấm được</p></div>
        <button type="button" class="secondary icon-only" id="report-close" aria-label="Đóng">${window.ui.icon("x")}</button></div>
      <div class="notice">Khoảng tin cậy 95% lấy mẫu lại theo <b>người nói</b>
        (${r.bootstrap.n_boot} lần, hạt giống ${r.bootstrap.seed}). Các giá trị là phép đo của batch này,
        không phải kết luận về chất lượng hệ thống.</div>
      <h3>1. Hai giám khảo với nhau (${h.n} bài, ${h.speakers} người nói)</h3>
      <dl class="facts">
        <div><dt>Kappa có trọng số bậc hai, band</dt><dd>${metric(h.qwk_band)}</dd></div>
        <div><dt>${escapeHtml(h.icc_overall.kind || "ICC")} trên điểm tổng 0–6</dt><dd><b>${fmt(h.icc_overall.value)}</b></dd></div>
        <div><dt>Trùng band tuyệt đối</dt><dd>${metric(h.exact_band_agreement)}</dd></div>
        <div><dt>Kappa trên điểm tổng làm tròn nửa điểm</dt><dd>${metric(h.qwk_overall_half_points)}</dd></div>
        <div><dt>Tương quan Pearson, điểm tổng</dt><dd><b>${fmt(h.pearson_overall)}</b></dd></div>
        <div><dt>Chênh lệch tuyệt đối trung bình</dt><dd><b>${fmt(h.mean_abs_diff)}</b> điểm</dd></div>
      </dl>
      ${confusionTable(h.confusion_band, "Giám khảo 1", "Giám khảo 2")}
      <table><thead><tr><th>Tiêu chí</th><th>Pearson giữa hai giám khảo</th><th>Số bài</th></tr></thead><tbody>${criteria}</tbody></table>
      <h3>2. Máy so với điểm đối chiếu của người (${m.n} bài, ${m.speakers} người nói)</h3>
      <p class="muted small-note">Điểm đối chiếu: trung bình hai giám khảo (${m.reference_kinds.mean_of_two || 0} bài)
        hoặc trung vị ba người khi có phân xử (${m.reference_kinds.median_of_three || 0} bài). Điểm máy là kết quả của
        máy trước mọi quyết định của giảng viên.</p>
      <dl class="facts">
        <div><dt>Pearson</dt><dd>${metric(m.pearson)}</dd></div>
        <div><dt>RMSE</dt><dd>${metric(m.rmse)}</dd></div>
        <div><dt>Kappa có trọng số bậc hai, band</dt><dd>${metric(m.qwk_band)}</dd></div>
      </dl>
      ${confusionTable(m.confusion_band, "Người", "Máy")}
      <table><thead><tr><th>Band</th><th>Số bài (người)</th><th>Recall</th><th>Precision</th></tr></thead><tbody>${perBand}</tbody></table>
      <h3>3. Cờ chuyển giảng viên có đặt đúng chỗ không (RQ4)</h3>
      <dl class="facts">
        <div><dt>Sai số tuyệt đối trung bình, bài máy chuyển giảng viên</dt><dd><b>${fmt(r.routing.flagged.mean_abs_error)}</b> (${r.routing.flagged.n} bài)</dd></div>
        <div><dt>Sai số tuyệt đối trung bình, bài máy tự kết luận</dt><dd><b>${fmt(r.routing.not_flagged.mean_abs_error)}</b> (${r.routing.not_flagged.n} bài)</dd></div>
      </dl>
      ${notes}`;
  }

  async function openReport(batchId) {
    const d = await call(`/api/v1/admin/ratings/batches/${encodeURIComponent(batchId)}/report`);
    if (!d) return;
    $("report-body").innerHTML = reportHtml(d);
    const dialog = $("report-dialog");
    if (!dialog.open) dialog.showModal();
  }

  $("report-body").addEventListener("click", (e) => {
    if (e.target.closest("#report-close")) $("report-dialog").close();
  });

  window.adminRatings = {
    load() {
      loadSetup().then(loadBatches);
    },
  };
  window.adminRatings.load();
})();
