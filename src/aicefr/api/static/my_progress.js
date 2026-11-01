// Một người học nhìn kết quả của chính mình theo thời gian. FR-27.
//
// Cái khó của màn hình này không phải vẽ biểu đồ mà là KHÔNG nói quá.
// `ridge_resp_v2` có sai số cỡ nửa điểm trên chính tập kiểm định của nó, nên chênh lệch
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
const loadTitles = fetch("/api/v1/tasks")
  .then((r) => (r.ok ? r.json() : []))
  .then((rows) => {
    (rows || []).forEach((t) => {
      titles[t.task_id] = t.title;
    });
  })
  .catch(() => {});

const progressDone = Promise.all([
  fetch("/api/v1/me/progress").then((r) => (window.redirectToLoginIfExpired(r) ? null : r.json())),
  loadTitles,
])
  .then(([d]) => {
    if (d === null) return;
    window.clearBusy(panel);
    panel.innerHTML = build(d);
    window.wrapTables(panel);
    paintHabits(d.habits || []);
  })
  .catch(() => {
    window.clearBusy(panel);
    panel.innerHTML =
      '<div class="empty-state"><div class="empty-mark" aria-hidden="true">⚠</div>' +
      "<h2>Không kết nối được máy chủ</h2><p>Hãy tải lại trang sau ít phút.</p></div>";
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

const PLACE = { low: "đầu", mid: "giữa", high: "cuối" };
// "3,62 · B1 cuối": the score, the band and the third of it the result sits in (D078).
function bandLabel(r) {
  const p = r.band_position;
  const score = r.overall_0_6 == null ? "" : `${r.overall_0_6.toFixed(2)} · `;
  return `${score}${r.overall_band || "—"}${p ? ` ${PLACE[p.part]}` : ""}`;
}

function build(d) {
  const rows = d.results || [];
  if (!rows.length) {
    return (
      '<div class="empty-state"><div class="empty-mark" aria-hidden="true">◎</div>' +
      "<h2>Chưa có bài nào được chấm</h2>" +
      "<p>Sau khi bạn nộp vài bài, màn hình này sẽ vẽ lại kết quả theo thời gian " +
      "để bạn tự thấy mình đang ở đâu.</p>" +
      '<div class="button-row"><a class="button" href="/">Nộp bài đầu tiên</a></div></div>'
    );
  }

  const t = d.trend || {};
  const label = TREND_LABEL[t.direction] || TREND_LABEL.chua_du_du_lieu;

  let h = '<div class="card-head"><h2>Kết quả theo thời gian</h2>';
  h += `<span class="badge">${rows.length} bài có điểm</span></div>`;

  h += '<div class="stat-grid">';
  h += `<div class="stat"><b>${rows.length}</b><span>bài đã có điểm</span></div>`;
  h += `<div class="stat"><b>${d.verified_count || 0}</b><span>bài giảng viên đã xác nhận</span></div>`;
  const last = rows[rows.length - 1];
  h += `<div class="stat"><b>${last.overall_0_6.toFixed(2)}</b><span>bài gần nhất · ${window.escapeHtml(
    last.overall_band || "—"
  )}${last.band_position ? ` ${PLACE[last.band_position.part]} band` : ""}</span></div>`;
  h += "</div>";

  h += `<div class="notice ${label.kind}"><b>${label.text}.</b> ${window.escapeHtml(t.note || "")}</div>`;
  h += reliableBlock(d.reliable_change);

  h += chart(rows, d.band_thresholds || {});
  h +=
    '<p class="trend-legend"><span><i class="verified"></i>Giảng viên đã xác nhận</span>' +
    "<span><i></i>Máy ước lượng, chưa ai xác nhận</span></p>";

  h += '<h2 style="margin-top:var(--sp-6)">Từng bài</h2>';
  h += "<table><thead><tr><th>Nộp lúc</th><th>Đề</th><th>Điểm · band</th>" +
    "<th>Trạng thái</th><th>Xác nhận</th><th>Báo cáo</th></tr></thead><tbody>";
  for (const r of [...rows].reverse()) {
    h +=
      `<tr><td>${window.escapeHtml(shortDate(r.created_at))}</td>` +
      `<td>${window.escapeHtml(titles[r.task_id] || r.task_id)}</td>` +
      `<td>${window.escapeHtml(bandLabel(r))}</td>` +
      `<td>${window.escapeHtml(window.ui.statusName(r.status))}</td>` +
      `<td>${r.teacher_verified ? "Đã xác nhận" : '<span class="muted">Chưa</span>'}</td>` +
      `<td><a href="/report/${encodeURIComponent(r.response_id)}">Xem báo cáo</a></td></tr>`;
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
// trục là cách dễ nhất để biến dao động 0,2 điểm thành một ngọn núi. D078: bên
// phải ghi band, vạch đứt là ranh giới giữa hai band.
const Y_MIN = 0;
const Y_MAX = 6;
const BANDS = ["A1", "A2", "B1", "B2", "C1", "C2"];
const EDGES = ["A1_A2", "A2_B1", "B1_B2", "B2_C1", "C1_C2"];

function chart(rows, limits) {
  const W = 720;
  const H = 240;
  const PAD_L = 34;
  const PAD_R = 30;
  const PAD_T = 14;
  const PAD_B = 28;
  const innerW = W - PAD_L - PAD_R;
  const innerH = H - PAD_T - PAD_B;

  const x = (i) => PAD_L + (rows.length === 1 ? innerW / 2 : (i / (rows.length - 1)) * innerW);
  const y = (v) => PAD_T + innerH - ((v - Y_MIN) / (Y_MAX - Y_MIN)) * innerH;

  const edges = [Y_MIN, ...EDGES.map((k, i) => Number(limits[k] ?? i + 1.75)), Y_MAX];
  let g = "";
  for (let v = Y_MIN; v <= Y_MAX; v += 1) {
    g += `<line class="grid" x1="${PAD_L}" y1="${y(v)}" x2="${W - PAD_R}" y2="${y(v)}"></line>`;
    g += `<text class="axis-label" x="4" y="${y(v) + 4}">${v}</text>`;
  }
  BANDS.forEach((b, i) => {
    if (i) g += `<line class="grid band-edge" x1="${PAD_L}" y1="${y(edges[i]).toFixed(1)}" x2="${W - PAD_R}" y2="${y(edges[i]).toFixed(1)}"></line>`;
    g += `<text class="axis-label" x="${W - 4}" text-anchor="end" y="${(y((edges[i] + edges[i + 1]) / 2) + 4).toFixed(1)}">${b}</text>`;
  });

  const path = rows.map((r, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(r.overall_0_6).toFixed(1)}`).join(" ");
  let dots = "";
  rows.forEach((r, i) => {
    dots +=
      `<circle class="dot${r.teacher_verified ? " verified" : ""}" cx="${x(i).toFixed(1)}"` +
      ` cy="${y(r.overall_0_6).toFixed(1)}" r="4.5"><title>` +
      `${window.escapeHtml(shortDate(r.created_at))} · ${window.escapeHtml(bandLabel(r))}</title></circle>`;
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
    ` aria-label="Biểu đồ điểm ${rows.length} bài nói theo thời gian, thang 0 đến 6, band A1 đến C2.` +
    ` Bài gần nhất ${window.escapeHtml(bandLabel(rows[rows.length - 1]))}.">` +
    `${g}<path class="line" d="${path}"></path>${dots}${ends}</svg>`
  );
}

// ---------------------------------------------------------------- habits (D070)
// One small chart per habit, its own scale, the better direction named. The
// movement (first third against last third of the assessments) is the
// server's; from three assessments on, and called a direction, not progress.
function habitChart(h) {
  const W = 320;
  const H = 120;
  const PAD_L = 8;
  const PAD_R = 8;
  const PAD_T = 18;
  const PAD_B = 18;
  const pts = h.points;
  const values = pts.map((p) => p.value);
  let lo = Math.min(...values);
  let hi = Math.max(...values);
  if (hi - lo < 1e-9) {
    lo -= 1;
    hi += 1;
  }
  const innerW = W - PAD_L - PAD_R;
  const innerH = H - PAD_T - PAD_B;
  const x = (i) => PAD_L + (pts.length === 1 ? innerW / 2 : (i / (pts.length - 1)) * innerW);
  const y = (v) => PAD_T + innerH - ((v - lo) / (hi - lo)) * innerH;
  const path = pts.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");
  const dots = pts
    .map(
      (p, i) =>
        `<circle class="dot" cx="${x(i).toFixed(1)}" cy="${y(p.value).toFixed(1)}" r="3.5">` +
        `<title>${window.escapeHtml(shortDate(p.at))} · ${p.value} ${window.escapeHtml(h.unit)}</title></circle>`
    )
    .join("");
  const first = pts[0];
  const last = pts[pts.length - 1];
  const ends =
    `<text class="axis-label" x="${x(0).toFixed(1)}" y="${(y(first.value) - 7).toFixed(1)}"` +
    `${pts.length === 1 ? ' text-anchor="middle"' : ""}>${first.value}</text>` +
    (pts.length > 1
      ? `<text class="axis-label end" x="${x(pts.length - 1).toFixed(1)}" y="${(y(last.value) - 7).toFixed(1)}" text-anchor="end">${last.value}</text>`
      : "");
  return (
    `<svg class="trend-chart habit-chart" viewBox="0 0 ${W} ${H}" role="img"` +
    ` aria-label="${window.escapeHtml(h.label)} qua ${pts.length} bài, bài gần nhất ${last.value} ${window.escapeHtml(h.unit)}.">` +
    `<line class="grid" x1="${PAD_L}" y1="${H - PAD_B}" x2="${W - PAD_R}" y2="${H - PAD_B}"></line>` +
    `<path class="line" d="${path}"></path>${dots}${ends}</svg>`
  );
}

function habitMovement(h) {
  const m = h.movement;
  if (!m) return '<p class="muted small-note">Cần ít nhất 3 bài đánh giá để thấy hướng đi.</p>';
  const n = (v) => String(v).replace(".", ",");
  const went = m.delta > 0 ? "tăng" : m.delta < 0 ? "giảm" : "giữ nguyên";
  const chip = m.toward_better
    ? '<span class="badge ok">đúng hướng</span>'
    : m.delta === 0
      ? '<span class="badge">chưa đổi</span>'
      : '<span class="badge warn">ngược hướng</span>';
  return (
    `<p class="habit-move">${chip} ${went} từ ${n(m.first)} đến ${n(m.last)} ${window.escapeHtml(h.unit)}` +
    ` <span class="muted">(TB ${m.n} bài đầu so với ${m.n} bài gần nhất)</span></p>`
  );
}

function paintHabits(habits) {
  const card = document.getElementById("habits");
  const shown = habits.filter((h) => h.points.length);
  if (!card || !shown.length) return;
  document.getElementById("habits-body").innerHTML = shown
    .map(
      (h) =>
        '<figure class="habit">' +
        `<figcaption><b>${window.escapeHtml(h.label)}</b>` +
        ` <span class="muted">${h.better === "up" ? "cao hơn là tốt" : "thấp hơn là tốt"}</span></figcaption>` +
        habitChart(h) +
        habitMovement(h) +
        "</figure>"
    )
    .join("");
  card.hidden = false;
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
      `<span style="width:${Math.round((value / target) * 100)}%"></span></div>` +
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

const achievementsDone = fetch("/api/v1/me/achievements")
  .then((r) => {
    if (window.redirectToLoginIfExpired(r)) return null;
    if (!r.ok) throw new Error(String(r.status));
    return r.json();
  })
  .then((d) => {
    if (!d) return;
    window.clearBusy(achPanel);
    achPanel.innerHTML = achievementList(d);
    const fresh = d.items.filter((i) => i.new).map((i) => i.code);
    if (fresh.length) {
      fetch("/api/v1/me/achievements/seen", {
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
fetch("/api/v1/me/pronunciation")
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

// Arriving at #achievements from the practice page: the browser jumped to the
// section before the panel above it had grown, so jump again once both are drawn.
Promise.allSettled([progressDone, achievementsDone]).then(() => {
  if (location.hash === "#achievements") achPanel.scrollIntoView({ block: "start" });
});

// D056: what I said when listening back, newest last, linked to the report.
(async function replayNotes() {
  const r = await fetch("/api/v1/me/replay-labels");
  if (!r.ok) return;
  const notes = await r.json();
  if (!notes.length) return;
  const mmss = window.ui.mmss;
  document.getElementById("replay-notes-body").innerHTML = `<ul class="plain-list">${notes
    .map(
      (n) => `<li><a href="/report/${encodeURIComponent(n.response_id)}">${new Date(n.created_at).toLocaleDateString("vi-VN")} · đoạn ${mmss(n.start_s)}–${mmss(n.end_s)}</a>
        — ${window.escapeHtml(n.answer)}${n.intended ? `<div class="small">Bạn định nói: “${window.escapeHtml(n.intended)}”</div>` : ""}</li>`,
    )
    .join("")}</ul>`;
  document.getElementById("replay-notes").hidden = false;
})();
