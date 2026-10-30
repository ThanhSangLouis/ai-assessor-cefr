// A forgotten password replaced with the recovery code (D065).
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
  if (!pseudonymEl.value.trim()) return fail("Hãy nhập mã bút danh.", pseudonymEl);
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
        pseudonym: pseudonymEl.value.trim(),
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
    window.showRecoverySlip(d.pseudonym, d.recovery_code);
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
