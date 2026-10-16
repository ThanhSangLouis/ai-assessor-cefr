// Một người học nhìn kết quả của chính mình theo thời gian. FR-27.
//
// Cái khó của màn hình này không phải vẽ biểu đồ mà là KHÔNG nói quá.
// `ridge_resp_v2` có RMSE 0,53 trên chính tập kiểm định của nó, nên chênh lệch
// 0,2 điểm giữa hai bài nằm gọn trong sai số của dụng cụ đo. Một mũi tên đi lên
// vẽ trên chênh lệch đó là đang nói với sinh viên rằng họ tiến bộ, trong khi thứ
// duy nhất thay đổi là hôm ghi âm. Vì vậy ngưỡng để gọi là xu hướng do máy chủ
// tính từ chính RMSE của mô hình, và màn hình chỉ hiển thị lại.
//
// Điểm đã được giảng viên xác nhận và điểm máy ước lượng được vẽ khác nhau:
// gộp chung sẽ khiến một con số chưa ai kiểm tra trông như một kết luận.
const panel = document.getElementById("progress-panel");

const TREND_LABEL = {
  tang: { text: "Có dấu hiệu đi lên", kind: "notice-ok" },
  giam: { text: "Có dấu hiệu đi xuống", kind: "notice-warn" },
  chua_ro: { text: "Chưa kết luận được", kind: "notice-info" },
  chua_du_du_lieu: { text: "Chưa đủ dữ liệu", kind: "notice-info" },
};

function shortDate(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso || "—";
  const two = (n) => String(n).padStart(2, "0");
  return `${two(d.getDate())}/${two(d.getMonth() + 1)} ${two(d.getHours())}:${two(d.getMinutes())}`;
}

// Task titles for the table: "P3" means nothing to a student. A failed call
// keeps the ids.
let titles = {};
const loadTitles = fetch("/api/student/tasks")
  .then((r) => (r.ok ? r.json() : []))
  .then((rows) => {
    (rows || []).forEach((t) => {
      titles[t.task_id] = t.title;
    });
  })
  .catch(() => {});

const loadReliableChange = fetch("/api/v1/me/reliable-change")
  .then((r) => (r.ok ? r.json() : null))
  .catch(() => null);

const progressDone = Promise.all([
  fetch("/api/student/progress").then((r) =>
    window.redirectToLoginIfExpired(r) ? null : r.ok ? r.json() : Promise.reject(r.status)
  ),
  loadTitles,
  loadReliableChange,
])
  .then(([d, , reliableChange]) => {
    if (d === null) return;
    window.clearBusy(panel);
    panel.innerHTML = build(d, reliableChange);
    window.wrapTables(panel);
  })
  .catch(() => {
    window.clearBusy(panel);
    panel.innerHTML =
      '<div class="empty-state"><div class="empty-mark" aria-hidden="true">⚠</div>' +
      "<h2>Không kết nối được máy chủ</h2><p>Hãy tải lại trang sau ít phút.</p></div>";
  });

const effortPanel = document.getElementById("effort-progress");
const effortBody = document.getElementById("effort-body");
function effortView(d) {
  const seconds = Math.round(Number(d.today_seconds) || 0);
  const goal = Math.max(1, Number(d.goal_seconds) || 1);
  const pct = Math.min(100, Math.round((seconds / goal) * 100));
  const rest = new Set(d.rest_days || []);
  const week = (d.week || []).map((item) => {
    const day = new Date(`${item.date}T00:00:00`);
    const label = Number.isNaN(day.getTime()) ? item.date : ["CN", "T2", "T3", "T4", "T5", "T6", "T7"][day.getDay()];
    const value = Math.round(Number(item.seconds) || 0);
    const state = value > 0 ? "on" : rest.has(item.date) ? "rest" : "";
    return `<li class="${state}" title="${window.escapeHtml(window.ui.dmy(item.date))}: ${value} giây"><span class="dot"></span>${label}</li>`;
  }).join("");
  return '<div class="stat-grid">' +
    `<div class="stat"><b>${seconds}/${goal}</b><span>giây luyện nói hôm nay</span></div>` +
    `<div class="stat"><b>${Number(d.streak_days) || 0}</b><span>ngày liên tiếp</span></div>` +
    `<div class="stat"><b>${Number(d.record_days) || 0}</b><span>ngày là kỷ lục</span></div></div>` +
    `<progress class="bar native-progress effort-progress" aria-label="Mục tiêu luyện nói hôm nay" max="${goal}" value="${Math.min(seconds, goal)}">${pct}%</progress>` +
    `<p>${d.goal_met ? "Đã đạt mục tiêu hôm nay." : `Còn ${Math.max(0, goal - seconds)} giây để đạt mục tiêu hôm nay.`}</p>` +
    `<ol class="week-dots" aria-label="Thời lượng nói bảy ngày gần nhất">${week}</ol>` +
    `<p class="muted">7 ngày qua: ${Math.round(Number(d.week_seconds) || 0)} giây · 7 ngày trước: ${Math.round(Number(d.previous_week_seconds) || 0)} giây</p>`;
}

fetch("/api/v1/me/learning/progress")
  .then((r) => (window.redirectToLoginIfExpired(r) ? null : r.ok ? r.json() : Promise.reject(r.status)))
  .then((d) => {
    if (!d) return;
    window.clearBusy(effortPanel);
    effortBody.innerHTML = effortView(d);
  })
  .catch(() => {
    window.clearBusy(effortPanel);
    effortBody.innerHTML = '<p class="error">Chưa tải được thời lượng luyện tập.</p>';
  });

// D042: "progress" only when the rise is larger than the measurement error.
const RELIABLE_TEXT = {
  tien_bo: ["ok", "Tiến bộ đáng tin"],
  giam: ["warn", "Giảm đáng tin"],
  chua_vuot_sai_so: ["", "Chưa vượt sai số đo"],
  chua_co_sai_so: ["", "Chưa đo được sai số"],
  chua_du_du_lieu: ["", "Chưa đủ bài để so"],
};
function reliableBlock(rc) {
  if (!rc) return "";
  const [kind, title] = RELIABLE_TEXT[rc.verdict] || RELIABLE_TEXT.chua_du_du_lieu;
  const n = (v) => Number(v).toFixed(2).replace(".", ",");
  let body;
  if (rc.verdict === "chua_du_du_lieu") {
    body = "Cần ít nhất hai bài có điểm.";
  } else if (rc.verdict === "chua_co_sai_so") {
    body =
      `Trung bình ${rc.k} bài gần nhất so với ${rc.k} bài đầu: ${rc.difference >= 0 ? "+" : ""}${n(rc.difference)} điểm. ` +
      "Hệ thống chưa đo được sai số giữa hai lần nói của cùng một người, nên chưa kết luận là tiến bộ.";
  } else {
    body =
      `Trung bình ${rc.k} bài gần nhất so với ${rc.k} bài đầu: ${rc.difference >= 0 ? "+" : ""}${n(rc.difference)} điểm; ` +
      `cần vượt ±${n(rc.threshold)} điểm (95%, sai số đo ${n(rc.sem)}) mới chắc không phải do khác ngày, khác đề.`;
  }
  return `<div class="notice ${kind}"><b>${title}.</b> ${window.escapeHtml(body)}</div>`;
}

function build(d, reliableChange) {
  const submissions = d.items || [];
  const rows = submissions
    .filter((row) => typeof row.overall_score === "number")
    .map((row) => ({ ...row, overall_0_6: row.overall_score }));
  if (!submissions.length) {
    return (
      '<div class="empty-state"><div class="empty-mark" aria-hidden="true">◎</div>' +
      "<h2>Chưa có bài đánh giá nào</h2>" +
      "<p>Lịch sử điểm sẽ xuất hiện sau khi bạn nộp bài đánh giá và hệ thống có kết quả.</p>" +
      '<div class="button-row"><a class="button" href="/student/tasks">Chọn đề đánh giá</a></div></div>'
    );
  }

  const direction = {
    tien_bo: "tang",
    giam: "giam",
    chua_vuot_sai_so: "chua_ro",
    chua_co_sai_so: "chua_ro",
    chua_du_du_lieu: "chua_du_du_lieu",
  }[reliableChange?.verdict];
  const label = TREND_LABEL[direction] || TREND_LABEL.chua_du_du_lieu;

  let h = '<div class="card-head"><h2>Kết quả theo thời gian</h2>';
  h += `<span class="badge">${rows.length} bài có điểm</span></div>`;

  h += '<div class="stat-grid">';
  h += `<div class="stat"><b>${rows.length}</b><span>bài đã có điểm</span></div>`;
  h += `<div class="stat"><b>${d.teacher_verified_count || 0}</b><span>bài giảng viên đã xác nhận</span></div>`;
  const last = rows[rows.length - 1];
  h += `<div class="stat"><b>${last ? last.overall_0_6.toFixed(2) : "—"}</b><span>bài có điểm gần nhất · ${window.escapeHtml(
    last ? last.overall_band || "—" : "chưa có"
  )}</span></div>`;
  h += "</div>";

  if (rows.length) {
    const note = reliableChange?.reason_code === "insufficient_scores"
      ? "Cần ít nhất hai bài có điểm để so sánh."
      : "Kết luận thay đổi chỉ dùng khi dữ liệu vượt sai số đo.";
    h += `<div class="notice ${label.kind}"><b>${label.text}.</b> ${note}</div>`;
    h += reliableBlock(reliableChange);
    h += chart(rows);
    h +=
      '<p class="trend-legend"><span><i class="verified"></i>Giảng viên đã xác nhận</span>' +
      "<span><i></i>Máy ước lượng, chưa ai xác nhận</span></p>";
  } else {
    h += `<div class="notice notice-info"><b>Chưa có bài nào được chấm.</b> ${submissions.length} bài đã nộp chưa có điểm để hiển thị.</div>`;
  }

  h += '<h2 class="progress-results-title">Từng bài</h2>';
  h += "<table><thead><tr><th>Nộp lúc</th><th>Đề</th><th>Ước lượng</th>" +
    "<th>Trạng thái</th><th>Xác nhận</th><th>Báo cáo</th></tr></thead><tbody>";
  for (const r of [...submissions].reverse()) {
    const estimate = typeof r.overall_score === "number"
      ? `${r.overall_score.toFixed(2)} · ${window.escapeHtml(r.overall_band || "—")}`
      : "Chưa có ước lượng";
    h +=
      `<tr><td>${window.escapeHtml(shortDate(r.created_at))}</td>` +
      `<td>${window.escapeHtml(titles[r.task_id] || r.task_id)}</td>` +
      `<td>${estimate}</td>` +
      `<td>${window.escapeHtml(window.ui.statusName(r.status))}</td>` +
      `<td>${r.teacher_verified ? "Đã xác nhận" : '<span class="muted">Chưa</span>'}</td>` +
      `<td><a href="/student/responses/${encodeURIComponent(r.response_id)}/report">Xem báo cáo</a></td></tr>`;
  }
  h += "</tbody></table>";

  h +=
    `<p class="muted">${window.escapeHtml(d.note || "")} Mọi điểm ở đây là ước lượng` +
    " phục vụ luyện tập, không phải chứng chỉ CEFR.</p>";
  return h;
}

// Một biểu đồ SVG viết tay, không kéo thư viện: cả trang chỉ cần đúng một
// đường gấp khúc, và một thư viện vẽ biểu đồ sẽ nặng hơn toàn bộ phần còn lại
// của giao diện. Trục y luôn phủ hết thang 0-6 thay vì co theo dữ liệu — co
// trục là cách dễ nhất để biến dao động 0,2 điểm thành một ngọn núi.
const Y_MIN = 0;
const Y_MAX = 6;

function chart(rows) {
  const W = 720;
  const H = 240;
  const PAD_L = 34;
  const PAD_R = 14;
  const PAD_T = 14;
  const PAD_B = 28;
  const innerW = W - PAD_L - PAD_R;
  const innerH = H - PAD_T - PAD_B;

  const x = (i) => PAD_L + (rows.length === 1 ? innerW / 2 : (i / (rows.length - 1)) * innerW);
  const y = (v) => PAD_T + innerH - ((v - Y_MIN) / (Y_MAX - Y_MIN)) * innerH;

  let g = "";
  for (let v = Y_MIN; v <= Y_MAX; v += 1) {
    g += `<line class="grid" x1="${PAD_L}" y1="${y(v)}" x2="${W - PAD_R}" y2="${y(v)}"></line>`;
    g += `<text class="axis-label" x="4" y="${y(v) + 4}">${v}</text>`;
  }

  const path = rows.map((r, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(r.overall_0_6).toFixed(1)}`).join(" ");
  let dots = "";
  rows.forEach((r, i) => {
    dots +=
      `<circle class="dot${r.teacher_verified ? " verified" : ""}" cx="${x(i).toFixed(1)}"` +
      ` cy="${y(r.overall_0_6).toFixed(1)}" r="4.5"><title>` +
      `${window.escapeHtml(shortDate(r.created_at))} · ${r.overall_0_6.toFixed(2)} · ` +
      `${window.escapeHtml(r.overall_band || "—")}</title></circle>`;
  });

  // Nhãn hai đầu trục hoành. Vẽ đủ mọi mốc thời gian sẽ chồng chữ lên nhau khi
  // có hai chục bài; hai đầu là đủ để đọc được chiều của biểu đồ.
  const ends =
    `<text class="axis-label" x="${PAD_L}" y="${H - 8}">${window.escapeHtml(
      shortDate(rows[0].created_at)
    )}</text>` +
    `<text class="axis-label" x="${W - PAD_R}" y="${H - 8}" text-anchor="end">${window.escapeHtml(
      shortDate(rows[rows.length - 1].created_at)
    )}</text>`;

  return (
    `<svg class="trend-chart" viewBox="0 0 ${W} ${H}" role="img"` +
    ` aria-label="Biểu đồ điểm ${rows.length} bài nói theo thời gian, thang 0 đến 6.` +
    ` Bài gần nhất ${rows[rows.length - 1].overall_0_6.toFixed(2)} điểm.">` +
    `${g}<path class="line" d="${path}"></path>${dots}${ends}</svg>`
  );
}

const printButton = document.getElementById("print-progress");
if (printButton) printButton.addEventListener("click", () => window.print());

// Achievements (D032): effort, not scores. Each tile says what was done and
// how far the next step is; a tile reached since the last visit is marked
// "Mới" once, then marked seen. Nobody else can read this list.
const achPanel = document.getElementById("achievements");

function dayOf(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso || "—";
  const two = (n) => String(n).padStart(2, "0");
  return `${two(d.getDate())}/${two(d.getMonth() + 1)}/${d.getFullYear()}`;
}

function achievementTile(a) {
  const cls = ["ach", a.unlocked ? "is-unlocked" : "is-locked", a.new ? "is-new" : ""]
    .filter(Boolean)
    .join(" ");
  const value = Number(a.value) || 0;
  const target = Math.max(1, Number(a.target) || 1);
  const state = a.unlocked
    ? `<span class="ach-state">Đạt ngày ${window.escapeHtml(dayOf(a.unlocked_at))}</span>`
    : `<div class="bar" role="progressbar" aria-label="Tiến độ: ${window.escapeHtml(a.title)}"` +
      ` aria-valuemin="0" aria-valuemax="${target}" aria-valuenow="${value}">` +
      `<progress class="bar native-progress ach-progress" aria-label="Tiến độ: ${window.escapeHtml(a.title)}" max="${target}" value="${Math.min(target, Math.max(0, value))}">${value}/${target}</progress>` +
      `<span class="ach-state">${value}/${target} ${window.escapeHtml(a.unit)} · chưa đạt</span>`;
  return (
    `<li class="${cls}">` +
    `<span class="ach-medal" aria-hidden="true">${window.ui.icon(a.icon)}</span>` +
    '<div class="ach-body">' +
    `<b class="ach-title">${window.escapeHtml(a.title)}` +
    (a.new ? ' <span class="ach-fresh">Mới</span>' : "") +
    "</b>" +
    `<span class="ach-desc">${window.escapeHtml(a.description)}</span>` +
    state +
    "</div></li>"
  );
}

function achievementList(d) {
  const byGroup = {};
  for (const item of d.items) (byGroup[item.group] = byGroup[item.group] || []).push(item);
  let h =
    '<div class="card-head"><h2 id="ach-title">Thành tựu</h2>' +
    `<span class="badge">${Number(d.unlocked)}/${Number(d.total)} đã đạt</span></div>` +
    '<p class="muted ach-lede">Ghi lại công sức luyện tập: thời gian nói, số ngày, bài đã xong, ' +
    "những lần thử lại. Không dựa vào điểm, không so với ai và chỉ bạn thấy; đã đạt thì giữ mãi.</p>";
  for (const g of d.groups) {
    const items = byGroup[g.key] || [];
    if (!items.length) continue;
    h += `<h3 class="ach-group">${window.escapeHtml(g.name)}</h3>`;
    h += `<ul class="ach-grid">${items.map(achievementTile).join("")}</ul>`;
  }
  return h;
}

const ACHIEVEMENT_GROUPS = [
  { key: "habit", name: "Đều đặn" },
  { key: "voice", name: "Thời gian nói" },
  { key: "path", name: "Lộ trình" },
  { key: "persistence", name: "Kiên trì" },
  { key: "assessment", name: "Đánh giá" },
];

const achievementsDone = fetch("/api/v1/me/learning/achievements")
  .then((r) => {
    if (window.redirectToLoginIfExpired(r)) return null;
    if (!r.ok) throw new Error(String(r.status));
    return r.json();
  })
  .then((d) => {
    if (!d) return;
    d.groups = ACHIEVEMENT_GROUPS.filter((group) => d.items.some((item) => item.group === group.key));
    d.items = d.items.map((item) => ({ ...item, unlocked: Boolean(item.unlocked_at), new: item.is_new }));
    if (d.next) {
      const item = d.items.find((row) => row.code === d.next.code);
      if (item) d.next = { ...item, ...d.next };
    }
    window.clearBusy(achPanel);
    achPanel.innerHTML = achievementList(d);
    const fresh = d.items.filter((i) => i.new).map((i) => i.code);
    if (fresh.length) {
      fetch("/api/v1/me/learning/achievements/seen", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ codes: fresh }),
      }).catch(() => {});
    }
  })
  .catch(() => {
    window.clearBusy(achPanel);
    achPanel.innerHTML =
      '<h2 id="ach-title">Thành tựu</h2><p class="error">Không tải được thành tựu. Hãy tải lại trang.</p>';
  });

// D039: pronunciation patterns from the learner's own lesson steps.
const pronPanel = document.getElementById("pronunciation");
const pronBody = document.getElementById("pronunciation-body");
fetch("/api/v1/me/learning/pronunciation")
  .then((r) => (window.redirectToLoginIfExpired(r) ? null : r.ok ? r.json() : Promise.reject(r.status)))
  .then((d) => {
    if (!d) return;
    window.clearBusy(pronPanel);
    pronBody.innerHTML = window.ui.pronunciationList(d, { lessonLinks: true });
  })
  .catch(() => {
    window.clearBusy(pronPanel);
    pronBody.innerHTML = '<p class="error">Không tải được phần phát âm. Hãy tải lại trang.</p>';
  });

// D040: the learner's place in the feedback study, the survey and the way out.
const studyPanel = document.getElementById("study");
const studyBody = document.getElementById("study-body");
const AGREE = ["Hoàn toàn không đồng ý", "Không đồng ý", "Phân vân", "Đồng ý", "Hoàn toàn đồng ý"];

function drawStudy(payload) {
  const s = payload?.study;
  if (!s) return;
  studyPanel.hidden = false;
  const state = s.state === "SURVEY" ? "Đang ở giai đoạn khảo sát" : "Đang tham gia";
  const arm = s.arm === "score_only" ? "Chỉ xem điểm" : "Có nhận xét chi tiết";
  studyBody.innerHTML =
    `<p>${state} trong nghiên cứu phản hồi, nhóm <b>${window.escapeHtml(arm)}</b>.</p>` +
    '<p class="muted">Bạn có thể xem hoặc thay đổi lựa chọn dữ liệu nghiên cứu trong phần đồng ý dữ liệu.</p>' +
    '<p><a class="button secondary small" href="/student/consent">Quản lý lựa chọn đồng ý dữ liệu</a></p>';
}

fetch("/api/v1/me/study")
  .then((r) => (window.redirectToLoginIfExpired(r) ? null : r.ok ? r.json() : null))
  .then(drawStudy)
  .catch(() => {});

// Arriving at #achievements from the practice page: the browser jumped to the
// section before the panel above it had grown, so jump again once both are drawn.
Promise.allSettled([progressDone, achievementsDone]).then(() => {
  if (location.hash === "#achievements") achPanel.scrollIntoView({ block: "start" });
});
