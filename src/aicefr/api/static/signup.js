// Self sign-up (D065, D071): an email, a full name and a password in; a recovery code out.
const form = document.getElementById("f");
const button = document.getElementById("b");
const box = document.getElementById("tb");
const passwordEl = document.getElementById("password");
const againEl = document.getElementById("again");
const emailEl = document.getElementById("email");
const nameEl = document.getElementById("full-name");

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
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(emailEl.value.trim())) return fail("Hãy nhập một email hợp lệ.", emailEl);
  if (!nameEl.value.trim()) return fail("Hãy nhập họ và tên.", nameEl);
  const min = Number(passwordEl.getAttribute("minlength")) || 8;
  if (passwordEl.value.length < min) return fail(`Mật khẩu phải từ ${min} ký tự trở lên.`, passwordEl);
  if (passwordEl.value !== againEl.value) return fail("Hai lần nhập mật khẩu chưa khớp nhau.", againEl);
  button.disabled = true;
  button.textContent = "Đang tạo…";
  try {
    const r = await fetch("/api/v1/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: emailEl.value.trim(),
        full_name: nameEl.value.trim(),
        password: passwordEl.value,
      }),
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      fail(typeof d.detail === "string" ? d.detail : "Không tạo được tài khoản.");
      return;
    }
    form.hidden = true;
    document.getElementById("done").hidden = false;
    window.showRecoverySlip(d.email || d.pseudonym, d.recovery_code);
    // D079: a verification code went out with the account.
    document.getElementById("verify-note").hidden = d.email_verification !== "sent";
    const go = document.getElementById("go");
    if (typeof d.home === "string" && d.home.startsWith("/") && !d.home.startsWith("//")) {
      go.href = d.home;
    }
    window.guardUntilKept(document.getElementById("kept"), go);
  } catch (err) {
    fail("Không kết nối được máy chủ. Tài khoản chưa được tạo.");
  } finally {
    button.disabled = false;
    button.textContent = "Tạo tài khoản";
  }
};
