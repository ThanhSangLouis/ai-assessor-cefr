// A forgotten password: a code sent by email (D079), or the recovery code (D065).
const form = document.getElementById("f");
const button = document.getElementById("b");
const box = document.getElementById("tb");
const pseudonymEl = document.getElementById("pseudonym");
const codeEl = document.getElementById("code");
const passwordEl = document.getElementById("password");
const againEl = document.getElementById("again");

document.getElementById("show").addEventListener("change", (e) => {
  [passwordEl, againEl].forEach((el) => (el.type = e.target.checked ? "text" : "password"));
});

function fail(message, el) {
  box.innerHTML = `<p class="error">${window.escapeHtml(message)}</p>`;
  if (el) el.focus();
}

form.onsubmit = async (e) => {
  e.preventDefault();
  box.innerHTML = "";
  if (!pseudonymEl.value.trim()) return fail("Hãy nhập email.", pseudonymEl);
  if (!codeEl.value.trim()) return fail("Hãy nhập mã khôi phục.", codeEl);
  const min = Number(passwordEl.getAttribute("minlength")) || 8;
  if (passwordEl.value.length < min) return fail(`Mật khẩu phải từ ${min} ký tự trở lên.`, passwordEl);
  if (passwordEl.value !== againEl.value) return fail("Hai lần nhập mật khẩu mới chưa khớp nhau.", againEl);
  button.disabled = true;
  button.textContent = "Đang đặt lại…";
  try {
    const r = await fetch("/api/v1/auth/recover", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: pseudonymEl.value.trim(),
        recovery_code: codeEl.value,
        new_password: passwordEl.value,
      }),
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      // 401: wrong pseudonym or code; 429: locked after too many tries (NFR-07).
      fail(typeof d.detail === "string" ? d.detail : "Không đặt lại được mật khẩu.");
      codeEl.select();
      return;
    }
    form.hidden = true;
    document.getElementById("done").hidden = false;
    window.showRecoverySlip(d.email || d.pseudonym, d.recovery_code);
    const go = document.getElementById("go");
    if (typeof d.home === "string" && d.home.startsWith("/") && !d.home.startsWith("//")) {
      go.href = d.home;
    }
    window.guardUntilKept(document.getElementById("kept"), go);
  } catch (err) {
    fail("Không kết nối được máy chủ. Mật khẩu chưa được đổi.");
  } finally {
    button.disabled = false;
    button.textContent = "Đặt mật khẩu mới";
  }
};

// ---------------------------------------------------------------- by email (D079)
const emailForm = document.getElementById("fe");
if (emailForm) {
  const codeForm = document.getElementById("fc");
  const emailEl = document.getElementById("reset-email");
  const sendButton = document.getElementById("be");
  const emailBox = document.getElementById("tbe");
  const codeBox = document.getElementById("tbc");
  const say = (el, message) => (el.innerHTML = `<p class="error">${window.escapeHtml(message)}</p>`);

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
