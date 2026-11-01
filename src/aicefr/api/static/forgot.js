// A forgotten password: a code sent by email (D079). With email off the page
// only says whom to ask, and there is no form.
const emailForm = document.getElementById("fe");
if (emailForm) {
  const codeForm = document.getElementById("fc");
  const emailEl = document.getElementById("reset-email");
  const sendButton = document.getElementById("be");
  const emailBox = document.getElementById("tbe");
  const codeBox = document.getElementById("tbc");
  const say = (el, message) => (el.innerHTML = `<p class="error">${window.escapeHtml(message)}</p>`);

  document.getElementById("show").addEventListener("change", (e) => {
    ["reset-password", "reset-again"].forEach(
      (id) => (document.getElementById(id).type = e.target.checked ? "text" : "password"),
    );
  });

  async function askForCode() {
    const r = await fetch("/api/v1/auth/forgot/email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: emailEl.value.trim() }),
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(typeof d.detail === "string" ? d.detail : "Chưa gửi được mã.");
    return d;
  }

  emailForm.onsubmit = async (e) => {
    e.preventDefault();
    emailBox.innerHTML = "";
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(emailEl.value.trim())) {
      say(emailBox, "Hãy nhập email của tài khoản.");
      emailEl.focus();
      return;
    }
    sendButton.disabled = true;
    try {
      const d = await askForCode();
      emailForm.hidden = true;
      codeForm.hidden = false;
      document.getElementById("sent-note").textContent = d.message;
      document.getElementById("reset-code").focus();
    } catch (err) {
      say(emailBox, err.message);
    } finally {
      sendButton.disabled = false;
    }
  };

  document.getElementById("resend").addEventListener("click", async () => {
    codeBox.innerHTML = "";
    try {
      const d = await askForCode();
      window.toast(d.message, "ok");
    } catch (err) {
      say(codeBox, err.message);
    }
  });

  codeForm.onsubmit = async (e) => {
    e.preventDefault();
    codeBox.innerHTML = "";
    const code = document.getElementById("reset-code");
    const pw = document.getElementById("reset-password");
    const again = document.getElementById("reset-again");
    if (!/^\d{6}$/.test(code.value.trim())) return say(codeBox, "Mã gồm 6 chữ số.");
    const min = Number(pw.getAttribute("minlength")) || 8;
    if (pw.value.length < min) return say(codeBox, `Mật khẩu phải từ ${min} ký tự trở lên.`);
    if (pw.value !== again.value) return say(codeBox, "Hai lần nhập mật khẩu mới chưa khớp nhau.");
    const button = document.getElementById("bc");
    button.disabled = true;
    try {
      const r = await fetch("/api/v1/auth/forgot/email/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: emailEl.value.trim(), code: code.value.trim(), new_password: pw.value }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) {
        say(codeBox, typeof d.detail === "string" ? d.detail : "Không đặt lại được mật khẩu.");
        return;
      }
      const home = typeof d.home === "string" && d.home.startsWith("/") && !d.home.startsWith("//") ? d.home : "/";
      window.location.href = home;
    } catch (err) {
      say(codeBox, "Không kết nối được máy chủ. Mật khẩu chưa được đổi.");
    } finally {
      button.disabled = false;
    }
  };
}
