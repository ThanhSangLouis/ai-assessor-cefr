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
  )}</span></div>`;
  h += "</div>";

  h += `<div class="notice ${label.kind}"><b>${label.text}.</b> ${window.escapeHtml(t.note || "")}</div>`;
  h += reliableBlock(d.reliable_change);

  h += chart(rows);
  h +=
    '<p class="trend-legend"><span><i class="verified"></i>Giảng viên đã xác nhận</span>' +
    "<span><i></i>Máy ước lượng, chưa ai xác nhận</span></p>";

  h += '<h2 style="margin-top:var(--sp-6)">Từng bài</h2>';
  h += "<table><thead><tr><th>Nộp lúc</th><th>Đề</th><th>Ước lượng</th>" +
    "<th>Trạng thái</th><th>Xác nhận</th><th>Báo cáo</th></tr></thead><tbody>";
  for (const r of [...rows].reverse()) {
    h +=
      `<tr><td>${window.escapeHtml(shortDate(r.created_at))}</td>` +
      `<td>${window.escapeHtml(titles[r.task_id] || r.task_id)}</td>` +
      `<td>${r.overall_0_6.toFixed(2)} · ${window.escapeHtml(r.overall_band || "—")}</td>` +
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

// D040: the learner's place in the feedback study, the survey and the way out.
const studyPanel = document.getElementById("study");
const studyBody = document.getElementById("study-body");
const AGREE = ["Hoàn toàn không đồng ý", "Không đồng ý", "Phân vân", "Đồng ý", "Hoàn toàn đồng ý"];

function studyView(s) {
  if (s.withdrawn) {
    return '<p class="muted">Bạn đã rời thực nghiệm. Báo cáo của bạn hiện đầy đủ như bình thường.</p>';
  }
  let h =
    `<p>Bạn đang tham gia <b>${window.escapeHtml(s.name)}</b>, nhóm <b>${window.escapeHtml(s.arm_name)}</b>. ` +
    "Hai nhóm được chia ngẫu nhiên để xem nhận xét chi tiết có giúp luyện nói tốt hơn chỉ xem điểm hay không.</p>";
  if (s.status === "survey") {
    if (s.survey_done) {
      h += '<p class="muted">Cảm ơn bạn, câu trả lời khảo sát đã được ghi lại.</p>';
    } else {
      h += '<form id="study-survey" class="survey"><p><b>Năm câu hỏi ngắn</b> (1 = hoàn toàn không đồng ý, 5 = hoàn toàn đồng ý):</p>';
      for (const item of s.survey_items) {
        h += `<fieldset><legend>${window.escapeHtml(item.text)}</legend><div class="survey-scale">`;
        for (let v = 1; v <= 5; v++) {
          h +=
            `<label title="${window.escapeHtml(AGREE[v - 1])}"><input type="radio" required ` +
            `name="${encodeURIComponent(item.key)}" value="${v}"> ${v}</label>`;
        }
        h += "</div></fieldset>";
      }
      h += '<div class="button-row"><button type="submit" class="button">Gửi khảo sát</button></div></form>';
    }
  }
  h +=
    '<div class="button-row"><button type="button" class="button secondary small" id="study-leave">' +
    "Rời thực nghiệm</button></div>";
  return h;
}

function drawStudy(s) {
  if (!s || !s.enrolled) return;
  studyPanel.hidden = false;
  studyBody.innerHTML = studyView(s);
  const form = document.getElementById("study-survey");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const answers = {};
      for (const item of s.survey_items) answers[item.key] = Number(new FormData(form).get(item.key));
      const r = await window.apiJson("/api/v1/me/study/survey", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers }),
      });
      if (r) drawStudy({ ...s, survey_done: true });
    });
  }
  const leave = document.getElementById("study-leave");
  if (leave) {
    leave.addEventListener("click", async () => {
      if (!window.confirm("Rời thực nghiệm? Từ giờ báo cáo của bạn sẽ hiện đầy đủ nhận xét.")) return;
      const r = await window.apiJson("/api/v1/me/study/withdraw", { method: "POST" });
      if (r) drawStudy({ ...s, withdrawn: true });
    });
  }
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
