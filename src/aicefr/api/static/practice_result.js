const root = document.getElementById("practice-result");
const attemptId = root.dataset.responseId;
const escapeHtml = window.escapeHtml;
const STATUS = {
  PASS: "Đạt mục tiêu luyện tập",
  FAIL: "Chưa đạt mục tiêu luyện tập",
  UNSURE: "Chưa đủ căn cứ để kết luận",
  UNMEASURED: "Chưa đo được lượt này",
};
const REASONS = {
  NO_SPEECH: "Không phát hiện được lời nói.",
  LOW_ASR_CONFIDENCE: "Độ tin cậy nhận dạng còn thấp.",
  TRANSCRIPT_UNAVAILABLE: "Chưa có bản chép lời để đo.",
  REFERENCE_MISSING: "Thiếu nội dung đối chiếu.",
  INVALID_EVIDENCE: "Minh chứng đo chưa hợp lệ.",
  LANGUAGE_NOT_ENGLISH: "Lượt nói không dùng tiếng Anh.",
  LANGUAGE_UNCERTAIN: "Chưa xác định chắc ngôn ngữ.",
  LEMMA_EQUIVALENT: "Từ tương đương đã được tính.",
};

function measurementText(item, goal) {
  const unit = goal && goal.kind === "speak_seconds" ? " giây" : "";
  const measured = item.measured_value != null && Number.isFinite(Number(item.measured_value))
    ? `${Number(item.measured_value)}${unit}`
    : "chưa có số đo";
  const target = Number.isFinite(Number(item.target)) ? `${Number(item.target)}${unit}` : "";
  return `${measured}${target ? ` · mục tiêu ${target}` : ""}`;
}

function render(record) {
  window.clearBusy(root);
  const mission = record.mission || {};
  const result = record.result;
  if (!result) {
    const failed = ["NOT_EVALUATED", "LEGACY"].includes(record.state);
    root.innerHTML =
      '<div class="page-head"><h1>Kết quả luyện tập</h1></div>' +
      `<div class="notice ${failed ? "notice-danger" : "notice-info"}">` +
      `<b>${failed ? "Không thể xử lý bản ghi." : "Bản ghi đang được xử lý."}</b> ` +
      `${failed ? "Bạn có thể quay lại nhiệm vụ và thử lại." : "Trang sẽ tự cập nhật khi có kết quả."}</div>` +
      (mission.mission_id
        ? `<p class="button-row"><a class="button" href="/practice/${encodeURIComponent(mission.mission_id)}">Quay lại nhiệm vụ</a></p>`
        : '<p><a href="/practice">Về lộ trình luyện tập</a></p>');
    return;
  }

  const goals = new Map((mission.goals || []).map((goal) => [goal.goal_id, goal]));
  const measurements = (result.measurements || []).map((item) => {
    const goal = goals.get(item.goal_id);
    const status = STATUS[item.status] || "Trạng thái chưa xác định";
    const reason = item.reason ? REASONS[item.reason] || "" : "";
    return (
      `<li><b>${escapeHtml(goal ? goal.kind.replaceAll("_", " ") : "Mục tiêu")}</b>` +
      `<span>${escapeHtml(status)} · ${escapeHtml(measurementText(item, goal))}</span>` +
      (reason ? `<small class="muted">${escapeHtml(reason)}</small>` : "") +
      "</li>"
    );
  }).join("");
  const reasons = (result.reasons || []).map((code) => REASONS[code] || "").filter(Boolean);
  const status = STATUS[result.status] || "Lượt luyện đã được xử lý";
  root.innerHTML =
    '<div class="page-head">' +
    '<p class="crumb"><a href="/practice">← Lộ trình luyện tập</a></p>' +
    `<p class="task-tags"><span class="badge">${escapeHtml(window.ui.practiceName(mission.criterion))}</span>` +
    `<span class="badge">Mức ${escapeHtml(mission.target_band || "—")}</span></p>` +
    `<h1>${escapeHtml(mission.title || "Kết quả luyện tập")}</h1>` +
    `<p class="lede">${escapeHtml(status)}. Bài luyện tập không tạo điểm CEFR.</p></div>` +
    '<section class="card"><h2>Kết quả từng mục tiêu</h2>' +
    (measurements ? `<ul class="mission-list">${measurements}</ul>` : '<p class="muted">Không có số đo chi tiết.</p>') +
    (reasons.length ? `<p class="muted">${reasons.map(escapeHtml).join(" ")}</p>` : "") +
    `<p class="muted">Thời lượng nói được đo: ${Number(result.speaking_s || 0)} giây.</p>` +
    '</section><div class="button-row">' +
    (mission.mission_id
      ? `<a class="button" href="/practice/${encodeURIComponent(mission.mission_id)}">Thử lại nhiệm vụ</a>`
      : "") +
    '<a class="button secondary" href="/practice">Về lộ trình</a></div>';
}

let startedAt = Date.now();
function load() {
  fetch(`/api/v1/practice/attempts/${encodeURIComponent(attemptId)}`)
    .then((response) => {
      if (window.redirectToLoginIfExpired(response)) return null;
      if (!response.ok) throw new Error(String(response.status));
      return response.json();
    })
    .then((record) => {
      if (!record) return;
      if (!record.result && !["NOT_EVALUATED", "LEGACY"].includes(record.state)) {
        if (Date.now() - startedAt > 5 * 60 * 1000) {
          window.clearBusy(root);
          root.innerHTML = '<div class="notice notice-warn"><b>Xử lý lâu hơn bình thường.</b> Hãy tải lại trang sau ít phút.</div>';
          return;
        }
        root.innerHTML = '<div class="notice notice-info"><b>Đang xử lý bản ghi…</b> Trang tự cập nhật khi xong.</div>';
        setTimeout(load, 1500);
        return;
      }
      render(record);
    })
    .catch(() => {
      window.clearBusy(root);
      root.innerHTML =
        '<div class="empty-state"><div class="empty-mark" aria-hidden="true">◇</div>' +
        '<h2>Không tìm thấy lần luyện này</h2><p><a href="/practice">Quay lại lộ trình luyện tập</a>.</p></div>';
    });
}

load();
