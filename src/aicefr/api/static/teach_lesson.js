// The transferred lesson builder stays read-only until its M10 producer contract is integrated.
const builder = document.getElementById("builder");
builder.setAttribute("aria-busy", "false");
const notice = document.createElement("section");
notice.className = "notice notice-info";
notice.setAttribute("role", "status");
notice.textContent = "Soạn bài đang chờ API M10 được tích hợp. Chưa có dữ liệu nào được gửi hoặc thay đổi.";
builder.prepend(notice);
builder.querySelectorAll("button, input, textarea, select").forEach((element) => { element.disabled = true; });
builder.querySelectorAll("[aria-busy=true]").forEach((element) => { element.setAttribute("aria-busy", "false"); });
