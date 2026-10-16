const root = document.getElementById("insights");
const escapeHtml = window.escapeHtml;
function metric(label, value, hint, attention) {
  return '<div class="stat' + (attention ? ' attention' : '') + '"><b>' + Number(value || 0) +
    '</b><span>' + escapeHtml(label) + '</span><small class="muted">' + escapeHtml(hint) + '</small></div>';
}
async function json(url) {
  const response = await fetch(url);
  if (window.redirectToLoginIfExpired(response)) throw new Error("expired");
  const value = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof value.detail === "string" ? value.detail : "Không tải được thống kê.");
  return value;
}
async function load() {
  try {
    const current = await json("/api/v1/me");
    const ownerId = current.profile && current.profile.actor_id;
    if (!ownerId) throw new Error("Không xác định được tài khoản hiện tại.");
    const data = await json("/api/v1/teacher/learn/insights/" + encodeURIComponent(ownerId));
    root.setAttribute("aria-busy", "false");
    root.innerHTML =
      '<section class="stat-grid" aria-label="Tổng hợp hoạt động gần đây">' +
      metric("Lượt luyện hoàn tất", data.practice_completed, "Tối đa 100 lượt practice gần nhất", false) +
      metric("Lượt practice chưa đánh giá", data.practice_not_evaluated, "Không được tính thành điểm", data.practice_not_evaluated > 0) +
      metric("Bước bài học hoàn tất", data.step_completed, "Tối đa 100 lượt step gần nhất", false) +
      metric("Bước chưa đánh giá", data.step_not_evaluated, "Bằng chứng chưa đủ để kết luận", data.step_not_evaluated > 0) +
      metric("Tệp audio được lưu", data.audio_artifacts, "Số artifact gắn với tài khoản", false) +
      metric("Ôn tập đến hạn", data.due_reviews, "Tổng hợp các mục ôn đến hạn", data.due_reviews > 0) +
      '</section><section class="card"><h2>Phạm vi dữ liệu</h2>' +
      '<p>Đây là tổng hợp theo tài khoản giáo viên đang đăng nhập, không phải báo cáo theo lớp hoặc lộ trình. API M10 hiện chưa cung cấp aggregate theo cohort, danh sách học viên hay bảng xếp hạng.</p>' +
      '<p class="muted">Cập nhật theo dữ liệu đến ' + escapeHtml(data.as_of || "thời điểm hiện tại") + '.</p>' +
      '<a class="button secondary" href="/teach">Quay lại lộ trình luyện</a></section>';
  } catch (error) {
    root.setAttribute("aria-busy", "false");
    if (error.message === "expired") return;
    root.innerHTML = '<section class="card"><p class="error">' + escapeHtml(error.message || "Không tải được thống kê.") + '</p></section>';
  }
}
load();
