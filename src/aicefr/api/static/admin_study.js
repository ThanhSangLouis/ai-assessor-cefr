// D040: start the feedback study, move it on, read the comparison of the two arms.
"use strict";

const STATUS_NAMES = { running: "Đang chạy", survey: "Đang khảo sát", closed: "Đã đóng" };
const NEXT = { running: ["survey", "Chuyển sang khảo sát"], survey: ["closed", "Đóng thực nghiệm"] };

const listPanel = document.getElementById("study-list");
const listBody = document.getElementById("study-list-body");
const newPanel = document.getElementById("study-new");
const reportPanel = document.getElementById("study-report");
const reportBody = document.getElementById("study-report-body");

function num(v, digits = 2) {
  return v == null ? "—" : Number(v).toFixed(digits);
}

function studyRow(s) {
  const next = NEXT[s.status];
  return (
    `<tr><td>${window.escapeHtml(s.name)}</td>` +
    `<td>${window.escapeHtml(STATUS_NAMES[s.status] || s.status)}</td>` +
    `<td class="num">${Number(s.participants)}</td><td class="num">${Number(s.surveys)}</td>` +
    `<td>${window.escapeHtml((s.created_at || "").slice(0, 10))}</td><td class="button-row">` +
    `<button type="button" class="button secondary small" data-report="${encodeURIComponent(s.study_id)}">Xem kết quả</button>` +
    `<a class="button secondary small" href="/api/v1/admin/studies/${encodeURIComponent(s.study_id)}/export.csv">CSV</a>` +
    (next
      ? `<button type="button" class="button small" data-move="${encodeURIComponent(s.study_id)}" ` +
        `data-to="${encodeURIComponent(next[0])}">${window.escapeHtml(next[1])}</button>`
      : "") +
    "</td></tr>"
  );
}

async function loadList() {
  const d = await window.apiJson("/api/v1/admin/studies");
  window.clearBusy(listPanel);
  if (!d) {
    listBody.innerHTML = '<p class="error">Không tải được danh sách. Hãy tải lại trang.</p>';
    return;
  }
  newPanel.hidden = d.studies.some((s) => s.status !== "closed");
  listBody.innerHTML = d.studies.length
    ? '<div class="table-wrap"><table><thead><tr><th>Tên</th><th>Trạng thái</th><th class="num">Tham gia</th>' +
      '<th class="num">Khảo sát</th><th>Bắt đầu</th><th></th></tr></thead><tbody>' +
      d.studies.map(studyRow).join("") +
      "</tbody></table></div>"
    : '<p class="muted">Chưa có thực nghiệm nào.</p>';
}

function armColumn(a, items) {
  const survey = items
    .map((it) => `<li>${window.escapeHtml(it.text)} <b>${num(a.survey[it.key])}</b></li>`)
    .join("");
  return (
    `<div class="kpi-arm"><h3>${window.escapeHtml(a.name)}</h3><ul class="kpi-list">` +
    `<li>Tham gia: <b>${Number(a.enrolled)}</b>, có đủ bài đầu và cuối: <b>${Number(a.with_pre_post)}</b></li>` +
    `<li>Mức tăng điểm trung bình: <b>${num(a.mean_gain)}</b> (độ lệch chuẩn ${num(a.sd_gain)})</li>` +
    `<li>Số lần luyện trung bình: <b>${num(a.mean_practice_attempts)}</b></li>` +
    `<li>Số người trả lời khảo sát: <b>${Number(a.survey_responses)}</b></li></ul>` +
    `<details><summary>Điểm khảo sát trung bình (1–5)</summary><ul class="kpi-list">${survey}</ul></details></div>`
  );
}

async function loadReport(id) {
  const d = await window.apiJson(`/api/v1/admin/studies/${encodeURIComponent(id)}/report`);
  if (!d) return;
  const diff = d.difference;
  const ci = diff.ci95 ? `[${num(diff.ci95[0])}; ${num(diff.ci95[1])}]` : "chưa đủ dữ liệu";
  reportPanel.hidden = false;
  reportBody.innerHTML =
    `<p><b>${window.escapeHtml(d.study.name)}</b>, bài cuối cách bài đầu ít nhất ${Number(d.min_days)} ngày.</p>` +
    `<div class="kpi-arms">${armColumn(d.arms.feedback, d.survey_items)}${armColumn(d.arms.score_only, d.survey_items)}</div>` +
    `<p>${window.escapeHtml(diff.label)}: <b>${num(diff.value)}</b>, khoảng tin cậy 95 % ${window.escapeHtml(ci)}, ` +
    `Hedges g = <b>${num(diff.hedges_g)}</b>.</p>` +
    `<p class="muted">${window.escapeHtml(d.note)}</p>`;
  reportPanel.scrollIntoView({ block: "start" });
}

listBody.addEventListener("click", async (e) => {
  const report = e.target.closest("[data-report]");
  if (report) return loadReport(decodeURIComponent(report.dataset.report));
  const move = e.target.closest("[data-move]");
  if (!move) return;
  const to = decodeURIComponent(move.dataset.to);
  const ask =
    to === "closed"
      ? "Đóng thực nghiệm? Mọi học viên sẽ thấy lại phản hồi đầy đủ và không khảo sát thêm được."
      : "Chuyển sang khảo sát? Học viên sẽ thấy năm câu hỏi ở trang Tiến độ; nhóm “Chỉ điểm” vẫn chưa thấy nhận xét cho đến khi đóng, và điểm từ lúc này không tính vào kết quả.";
  if (!window.confirm(ask)) return;
  const r = await window.apiJson(`/api/v1/admin/studies/${move.dataset.move}/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: to }),
  });
  if (r) {
    window.toast("Đã cập nhật trạng thái thực nghiệm.");
    loadList();
  }
});

document.getElementById("study-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  if (!window.confirm("Chia nhóm ngẫu nhiên và bắt đầu? Nhóm “Chỉ điểm” sẽ không thấy nhận xét cho đến khi đóng.")) return;
  const r = await window.apiJson("/api/v1/admin/studies", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: f.get("name"), min_days: Number(f.get("min_days")) }),
  });
  if (r) {
    window.toast(`Đã chia ${r.participants} học viên vào hai nhóm.`);
    loadList();
  }
});

loadList();
