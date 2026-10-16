// Cohort learning insights stay unavailable until M10/M13 producer contracts are integrated.
const insights = document.getElementById("insights");
window.clearBusy(insights);
insights.innerHTML = '<section class="card"><div class="empty-state"><h2>Chưa có dữ liệu insights</h2><p>Thống kê luyện tập và chỉnh nhận định sẽ hoạt động sau khi API aggregate M10/M13 được tích hợp theo contract đã duyệt.</p><a class="button secondary" href="/teacher/stats">Mở thống kê giảng viên hiện có</a></div></section>';
document.querySelectorAll("#attempt-dialog button, #words-dialog button, #words-dialog input, #words-dialog select, #words-dialog textarea").forEach((element) => { element.disabled = true; });
