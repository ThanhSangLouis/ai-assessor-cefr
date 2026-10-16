// The transferred authoring view stays read-only until its M10 producer contract is integrated.
const root = document.getElementById("teach-paths");
const note = document.getElementById("plan-note");
window.clearBusy(root);
note.hidden = false;
note.textContent = "Soạn lộ trình đang chờ API M10 được tích hợp. Chưa có dữ liệu nào được gửi hoặc thay đổi.";
document.getElementById("new-path").disabled = true;
document.getElementById("import-path").disabled = true;
document.getElementById("import-file").disabled = true;
root.innerHTML = '<section class="card"><div class="empty-state"><h2>Chưa thể tải lộ trình</h2><p>Trang sẽ hoạt động sau khi API authoring M10 được tích hợp và ánh xạ theo contract của repo.</p></div></section>';
