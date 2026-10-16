"use strict";
const list = document.getElementById("study-list");
const listBody = document.getElementById("study-list-body");
const form = document.getElementById("study-form");
const reportPanel = document.getElementById("study-report");
const reportBody = document.getElementById("study-report-body");
const STORAGE_KEY = "aicefr-admin-study-ids";
const STATUS = { DRAFT: "Bản nháp", RUNNING: "Đang chạy", SURVEY: "Đang khảo sát", CLOSED: "Đã đóng" };
function esc(value) { return window.escapeHtml(value == null ? "" : value); }
function loadSaved() {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(value) ? value.filter((item) => item && typeof item.id === "string") : [];
  } catch (_) { return []; }
}
function saveStudy(id, title) {
  const items = loadSaved().filter((item) => item.id !== id);
  items.unshift({ id, title: title || id });
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, 50)));
}
function fmt(value) { return value == null || Number.isNaN(Number(value)) ? "—" : Number(value).toFixed(3); }
async function whileDisabled(button, action) {
  if (button.disabled) return null;
  button.disabled = true;
  try {
    return await action();
  } finally {
    button.disabled = false;
  }
}
function nextState(state) {
  if (state === "DRAFT") return ["start", "Bắt đầu"];
  if (state === "RUNNING") return ["survey", "Chuyển sang khảo sát"];
  if (state === "SURVEY") return ["close", "Đóng study"];
  return null;
}
function renderRow(item, report) {
  const state = String(report.status || "UNKNOWN").toUpperCase();
  const arms = report.arms || {};
  const surveyCount = Object.values(arms).reduce((sum, arm) => sum + Number(arm.survey_responses || 0), 0);
  const move = nextState(state);
  return '<tr><td><strong>' + esc(item.title || item.id) + '</strong><div class="muted">' + esc(item.id) + '</div></td>' +
    '<td>' + esc(STATUS[state] || state) + '</td><td class="num">' + Number(report.n || 0) + '</td>' +
    '<td class="num">' + surveyCount + '</td><td class="button-row">' +
    '<button type="button" class="button secondary small" data-report="' + esc(item.id) + '">Xem kết quả</button>' +
    '<a class="button secondary small" href="/api/v1/admin/studies/' + encodeURIComponent(item.id) + '/export.csv">CSV</a>' +
    (move ? '<button type="button" class="button small" data-move="' + esc(item.id) + '" data-to="' + move[0] + '">' + esc(move[1]) + '</button>' : '') +
    '<button type="button" class="button secondary small" data-forget="' + esc(item.id) + '">Ẩn</button></td></tr>';
}
async function readReport(id) {
  return await window.apiJson("/api/v1/admin/studies/" + encodeURIComponent(id) + "/report");
}
async function loadList() {
  const saved = loadSaved();
  window.clearBusy(list);
  if (!saved.length) {
    listBody.innerHTML = '<p class="muted">Chưa có study ID trong trình duyệt này. Tạo study hoặc mở bằng ID.</p>';
    return;
  }
  const rows = await Promise.all(saved.map(async (item) => {
    try {
      const report = await readReport(item.id);
      return report ? renderRow(item, report) : '<tr><td>' + esc(item.title || item.id) + '</td><td colspan="4">Không tải được study.</td></tr>';
    } catch (_) {
      return '<tr><td>' + esc(item.title || item.id) + '<div class="muted">' + esc(item.id) + '</div></td><td colspan="4">Không tải được trạng thái.</td></tr>';
    }
  }));
  listBody.innerHTML = '<div class="table-wrap"><table><thead><tr><th>Tên / ID</th><th>Trạng thái</th><th>Học viên</th><th>Khảo sát</th><th>Thao tác</th></tr></thead><tbody>' +
    rows.join("") + '</tbody></table></div>';
}
function armColumn(name, arm, items) {
  const surveys = items.map((item) => '<li>' + esc(item.text) + ' <b>' + fmt(arm.survey && arm.survey[item.key]) + '</b></li>').join("");
  return '<div class="kpi-arm"><h3>' + esc(name) + '</h3><ul class="kpi-list">' +
    '<li>Tham gia: <b>' + Number(arm.enrolled || 0) + '</b>, có đủ bài đầu và cuối: <b>' + Number(arm.with_pre_post || 0) + '</b></li>' +
    '<li>Mức tăng điểm trung bình: <b>' + fmt(arm.mean_gain) + '</b> (độ lệch chuẩn ' + fmt(arm.sd_gain) + ')</li>' +
    '<li>Số lần luyện trung bình: <b>' + fmt(arm.mean_practice_attempts) + '</b></li>' +
    '<li>Số người trả lời khảo sát: <b>' + Number(arm.survey_responses || 0) + '</b></li></ul>' +
    '<details><summary>Điểm khảo sát trung bình (1–5)</summary><ul class="kpi-list">' + surveys + '</ul></details></div>';
}
async function showReport(id) {
  const data = await readReport(id);
  if (!data) return;
  const diff = data.difference || {};
  const interval = diff.ci95 ? '[' + fmt(diff.ci95[0]) + '; ' + fmt(diff.ci95[1]) + ']' : 'chưa đủ dữ liệu';
  const arms = data.arms || {};
  const items = data.survey_items || [];
  reportPanel.hidden = false;
  reportBody.innerHTML = '<p><b>Study ' + esc(id) + '</b> · ' + esc(STATUS[String(data.status).toUpperCase()] || data.status) +
    ' · bài cuối cách bài đầu tối thiểu ' + Number(data.min_days || 0) + ' ngày.</p>' +
    '<div class="kpi-arms">' + armColumn('Phản hồi đầy đủ', arms.feedback || {}, items) +
    armColumn('Chỉ điểm', arms.score_only || {}, items) + '</div>' +
    '<p>' + esc(diff.label || '') + ': <b>' + fmt(diff.value) + '</b>, khoảng tin cậy 95% ' + esc(interval) +
    ', Hedges g = <b>' + fmt(diff.hedges_g) + '</b>.</p>' +
    '<p class="muted">' + esc(data.note || '') + '</p>';
  reportPanel.scrollIntoView({ block: "start" });
}
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (form.dataset.submitting === "true") return;
  form.dataset.submitting = "true";
  const submitButton = event.submitter || form.querySelector('button[type="submit"]');
  const values = new FormData(form);
  const title = String(values.get("title") || "").trim();
  const minDays = Number(values.get("min_days"));
  try {
    const result = await whileDisabled(submitButton, () => window.apiJson("/api/v1/admin/studies", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, min_days: minDays }),
    }));
    if (!result) return;
    saveStudy(result.study_id, title);
    window.toast("Đã tạo study dạng nháp. Bắt đầu sau khi đã kiểm tra điều kiện tham gia.");
    form.reset();
    await loadList();
    await showReport(result.study_id);
  } finally {
    form.dataset.submitting = "false";
  }
});
document.getElementById("study-open-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const id = String(new FormData(event.target).get("study_id") || "").trim();
  if (!id) return;
  const report = await readReport(id);
  if (!report) return;
  saveStudy(id, id);
  event.target.reset();
  await loadList();
  await showReport(id);
});
listBody.addEventListener("click", async (event) => {
  const reportButton = event.target.closest("[data-report]");
  if (reportButton) return showReport(reportButton.dataset.report);
  const forgetButton = event.target.closest("[data-forget]");
  if (forgetButton) {
    saveStudyList(loadSaved().filter((item) => item.id !== forgetButton.dataset.forget));
    await loadList();
    return;
  }
  const move = event.target.closest("[data-move]");
  if (!move) return;
  const id = move.dataset.move, state = move.dataset.to;
  const question = state === "start"
    ? "Bắt đầu và chia ngẫu nhiên các học viên đang đồng ý tham gia?"
    : (state === "survey"
      ? "Chuyển sang khảo sát sau khi đã đủ dữ liệu cần thiết?"
      : "Đóng study? Sau khi đóng, survey không còn nhận câu trả lời.");
  if (!window.confirm(question)) return;
  await whileDisabled(move, async () => {
    const result = await window.apiJson("/api/v1/admin/studies/" + encodeURIComponent(id) + "/" + state, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
    });
    if (result) {
      window.toast("Đã cập nhật trạng thái study.");
      await loadList();
      await showReport(id);
    }
  });
});
function saveStudyList(items) { localStorage.setItem(STORAGE_KEY, JSON.stringify(items)); }
loadList();
