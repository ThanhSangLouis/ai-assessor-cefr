// Thống kê cấp lớp cho giảng viên. FR-29.
//
// Con số quan trọng nhất trên màn hình này không nói về sinh viên mà nói về
// chính cái máy: tỷ lệ giảng viên GIỮ NGUYÊN band mà mô hình đề xuất. Không màn
// hình chấm từng bài nào cho thấy được điều đó, vì nó chỉ lộ ra khi cộng dồn
// hàng chục quyết định. Một lớp mà giảng viên sửa một phần ba số band là một
// lớp đang nói cho bạn biết mô hình chưa dùng được — và đó là thứ phải đọc được
// trước khi ai đó trích điểm của máy vào bảng điểm học phần.
//
// Chỉ tính những lần duyệt mà máy CÓ đề xuất band. Bài máy từ chối chấm rồi
// giảng viên tự chấm không phải là "đồng ý" hay "không đồng ý" với ai cả; đếm
// vào sẽ làm đẹp cho mô hình bằng chính những ca nó không trả lời.
const panel = document.getElementById("stats-panel");

const BAND_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"];

fetch("/api/v1/review/stats")
  .then((r) => (window.redirectToLoginIfExpired(r) ? null : r.json()))
  .then((d) => {
    if (d === null) return;
    window.clearBusy(panel);
    if (d.detail) {
      panel.innerHTML =
        '<div class="empty-state"><div class="empty-mark" aria-hidden="true">∅</div>' +
        "<h2>Không xem được thống kê</h2><p>" +
        window.escapeHtml(d.detail) +
        "</p></div>";
      return;
    }
    panel.innerHTML = build(d);
    window.wrapTables(panel);
  })
  .catch(() => {
    window.clearBusy(panel);
    panel.innerHTML =
      '<div class="empty-state"><div class="empty-mark" aria-hidden="true">⚠</div>' +
      "<h2>Không kết nối được máy chủ</h2><p>Hãy tải lại trang sau ít phút.</p></div>";
  });

// D023. Practice across the class, per criterion. Totals only: this tells a
// teacher which criterion the class is stumbling on, not who to rank.
const PRACTICE_SKILLS = [
  ["fluency", "Độ trôi chảy"],
  ["coherence", "Mạch lạc"],
  ["range", "Vốn từ"],
  ["accuracy", "Ngữ pháp"],
  ["phonology", "Phát âm dễ nghe"],
];

function practiceSection(p) {
  let h = '<h2 style="margin-top:var(--sp-6)">Luyện tập của lớp</h2>';
  if (!p || !p.attempts) {
    return (
      h +
      '<div class="notice notice-info">Chưa có lần luyện tập nào được xử lý xong.</div>'
    );
  }
  h += '<div class="stat-grid">';
  h += `<div class="stat"><b>${Number(p.attempts)}</b><span>lần luyện đã xử lý</span></div>`;
  h += `<div class="stat"><b>${Number(p.learners)}</b><span>người có luyện</span></div>`;
  h += `<div class="stat"><b>${Math.round((p.completed / p.attempts) * 100)}%</b>` +
    "<span>lần luyện hoàn thành mọi mục tiêu</span></div>";
  h += "</div>";
  h += "<table><thead><tr><th>Tiêu chí</th><th>Lần luyện</th><th>Hoàn thành</th>" +
    "<th>Tỷ lệ</th></tr></thead><tbody>";
  for (const [code, name] of PRACTICE_SKILLS) {
    const c = (p.by_criterion || {})[code] || { attempts: 0, completed: 0 };
    const rate = c.attempts ? `${Math.round((c.completed / c.attempts) * 100)}%` : "—";
    h += `<tr><td><b>${name}</b></td><td>${Number(c.attempts)}</td>` +
      `<td>${Number(c.completed)}</td><td>${rate}</td></tr>`;
  }
  h += "</tbody></table>";
  h +=
    '<p class="muted">Không có số liệu theo từng sinh viên. Tỷ lệ hoàn thành thấp ở một ' +
    "tiêu chí là gợi ý để chọn bài cho cả lớp, không phải điểm của ai.</p>";
  return h;
}

function build(d) {
  if (!d.responses) {
    return (
      '<div class="empty-state"><div class="empty-mark" aria-hidden="true">◎</div>' +
      "<h2>Chưa có bài nào được chấm</h2>" +
      "<p>Thống kê xuất hiện khi lớp bắt đầu nộp bài.</p></div>" +
      practiceSection(d.practice)
    );
  }

  const ag = d.agreement || {};
  let h = '<div class="card-head"><h2>Toàn lớp</h2></div>';

  h += '<div class="stat-grid">';
  h += `<div class="stat"><b>${d.responses}</b><span>bài đã nộp</span></div>`;
  h += `<div class="stat"><b>${d.scored}</b><span>bài máy chấm được</span></div>`;
  h += `<div class="stat"><b>${d.speakers}</b><span>người nộp bài</span></div>`;
  h += `<div class="stat${d.waiting_for_review ? " attention" : ""}"><b>${d.waiting_for_review}</b>` +
    "<span>bài đang chờ duyệt</span></div>";
  h += `<div class="stat"><b>${d.teacher_verified}</b><span>bài đã xác nhận</span></div>`;
  h += "</div>";

  // How often teachers keep the machine's band: a measurement of the model
  // for the study, read by administrators only (D068).
  if (!document.body.classList.contains("role-admin")) {
    // nothing: a teacher reads the class, not the model
  } else if (!ag.decisions) {
    h += '<h2 style="margin-top:var(--sp-6)">Giảng viên và máy có đồng ý với nhau không</h2>';
    h +=
      '<div class="notice notice-info">Chưa có lượt duyệt nào để so sánh. ' +
      "Con số này chỉ có nghĩa sau vài chục quyết định.</div>";
  } else {
    h += '<h2 style="margin-top:var(--sp-6)">Giảng viên và máy có đồng ý với nhau không</h2>';
    const rate = ag.rate == null ? null : Math.round(ag.rate * 100);
    const weak = rate != null && rate < 70;
    h += '<div class="stat-grid">';
    h += `<div class="stat"><b>${ag.decisions}</b><span>lượt duyệt có band của máy</span></div>`;
    h += `<div class="stat"><b>${ag.band_kept}</b><span>lần giữ nguyên band</span></div>`;
    h += `<div class="stat${weak ? " attention" : ""}"><b>${ag.band_changed}</b>` +
      "<span>lần giảng viên đổi band</span></div>";
    h += `<div class="stat${weak ? " attention" : ""}"><b>${rate}%</b><span>tỷ lệ đồng ý</span></div>`;
    h += "</div>";
    h +=
      `<div class="notice ${weak ? "notice-warn" : "notice-info"}">` +
      (weak
        ? "<b>Giảng viên đang sửa nhiều.</b> Dưới 70% đồng ý nghĩa là band của máy chưa đủ " +
          "ổn định để dùng như một kết quả; hãy tiếp tục coi nó là gợi ý và duyệt từng bài."
        : "<b>Đây là số đo về mô hình, không phải về giảng viên.</b> Tỷ lệ đồng ý cao không " +
          "có nghĩa mô hình đúng — có thể giảng viên đang tin máy quá mức. Chỉ khảo sát " +
          "chấm mù đôi (kế hoạch tuần 10–11) mới trả lời được câu đó.") +
      "</div>";
  }

  h += '<h2 style="margin-top:var(--sp-6)">Phân bố band</h2>';
  const bands = d.by_band || {};
  const total = Object.values(bands).reduce((a, b) => a + b, 0) || 1;
  // D031: the same counts as blocks whose height follows each band's share.
  h += window.ui.cubes(
    BAND_ORDER.map((b) => ({
      label: b,
      sub: bands[b] || 0,
      h: 58 + ((bands[b] || 0) / total) * 100,
      cls: bands[b] ? "" : "is-dim",
    })),
    "band-columns"
  );
  h += "<table><thead><tr><th>Band</th><th>Số bài</th><th>Tỷ lệ</th></tr></thead><tbody>";
  for (const b of BAND_ORDER) {
    const n = bands[b] || 0;
    h += `<tr><td><b>${b}</b></td><td>${n}</td><td>${Math.round((n / total) * 100)}%</td></tr>`;
  }
  h += "</tbody></table>";
  h +=
    '<p class="muted">Band <b>máy ước lượng</b>, chưa phải trình độ thật của lớp.</p>';

  h += '<h2 style="margin-top:var(--sp-6)">Theo đề bài</h2>';
  h += "<table><thead><tr><th>Đề</th><th>Số bài</th><th>Điểm trung bình</th>" +
    "<th>Đang chờ duyệt</th></tr></thead><tbody>";
  for (const t of d.by_task || []) {
    h +=
      `<tr><td><b>${window.escapeHtml(t.task_id)}</b></td><td>${t.n}</td>` +
      `<td>${t.avg_score == null ? "—" : t.avg_score.toFixed(2)}</td>` +
      `<td>${t.waiting}</td></tr>`;
  }
  h += "</tbody></table>";
  h +=
    '<p class="muted">Điểm trung bình giữa các đề không so sánh trực tiếp được.</p>';
  return h + practiceSection(d.practice);
}

const printButton = document.getElementById("print-stats");
if (printButton) printButton.addEventListener("click", () => window.print());

// D039: the class's pronunciation patterns, counts only.
const classPron = document.getElementById("class-pronunciation");
const classPronBody = document.getElementById("class-pronunciation-body");
if (classPron) {
  fetch("/api/v1/teach/pronunciation")
    .then((r) => (window.redirectToLoginIfExpired(r) ? null : r.ok ? r.json() : Promise.reject(r.status)))
    .then((d) => {
      if (!d) return;
      window.clearBusy(classPron);
      const who = d.learners ? `<p class="muted">${d.learners} sinh viên, ${d.steps} bước đã đo.</p>` : "";
      classPronBody.innerHTML = who + window.ui.pronunciationList(d);
    })
    .catch(() => {
      window.clearBusy(classPron);
      classPronBody.innerHTML = '<p class="error">Không tải được phần phát âm.</p>';
    });
}

// D041: teacher time with and without the machine, measured, each figure with its count.
const teacherTime = document.getElementById("teacher-time");
const teacherTimeBody = document.getElementById("teacher-time-body");
function pct(v) {
  return v == null ? "—" : `${Math.round(v * 100)}%`;
}
function ci(c) {
  return c ? ` (95%: ${pct(c[0])}–${pct(c[1])})` : "";
}
function teacherTimeView(k) {
  const mins = (s) =>
    s.median_minutes == null
      ? `<span class="muted">chưa đủ ${k.min_samples} lần (có ${s.n})</span>`
      : `<b>${s.median_minutes.toFixed(1).replace(".", ",")}</b> phút <span class="muted">· trung vị ${s.n} lần</span>`;
  let h = '<div class="stat-grid">';
  h += `<div class="stat"><span>Duyệt một bài, có máy</span>${mins(k.review_with_machine)}</div>`;
  h += `<div class="stat"><span>Chấm mù một bài, không có máy</span>${mins(k.rating_without_machine)}</div>`;
  h += `<div class="stat"><span>Thời gian tiết kiệm</span><b>${k.time_saved == null ? "—" : pct(k.time_saved)}</b></div>`;
  h += "</div><ul class=\"kpi-list\">";
  const a = k.settled_alone;
  h += `<li>Máy tự xử lý: <b>${pct(a.rate)}</b>${window.escapeHtml(ci(a.ci95))} · ${a.k}/${a.n} bài có kết quả</li>`;
  const b = k.band_kept;
  h += `<li>Giảng viên giữ nguyên band máy đề xuất: <b>${pct(b.rate)}</b>${window.escapeHtml(ci(b.ci95))} · ${b.k}/${b.n} quyết định</li>`;
  if (k.review_with_machine.idle_left_out) {
    h += `<li class="muted">${k.review_with_machine.idle_left_out} lần mở bài quá ${k.idle_cap_minutes} phút không tính (người duyệt bỏ dở).</li>`;
  }
  if (k.rating_without_machine.idle_left_out) {
    h += `<li class="muted">${k.rating_without_machine.idle_left_out} phiếu chấm mù mở quá ${k.idle_cap_minutes} phút không tính.</li>`;
  }
  h += "</ul>";
  return h;
}
if (teacherTime) {
  fetch("/api/v1/review/kpi")
    .then((r) => (window.redirectToLoginIfExpired(r) ? null : r.ok ? r.json() : Promise.reject(r.status)))
    .then((d) => {
      if (!d) return;
      window.clearBusy(teacherTime);
      teacherTimeBody.innerHTML = teacherTimeView(d);
    })
    .catch(() => {
      window.clearBusy(teacherTime);
      teacherTimeBody.innerHTML = '<p class="error">Không tải được số đo thời gian.</p>';
    });
}
