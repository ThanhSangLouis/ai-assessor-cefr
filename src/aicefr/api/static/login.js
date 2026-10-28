// Login screen. See docs/web/SPEC_WEB.md section M1.
const form = document.getElementById("f");
const submitButton = document.getElementById("b");
const messageBox = document.getElementById("tb");
const passwordEl = document.getElementById("password");
const showButton = document.getElementById("show-password");
const capsHint = document.getElementById("caps-hint");

// D029: see what is being typed, and know when Caps Lock turns "matkhau" into
// "MATKHAU" -- the commonest wrong password there is.
showButton.addEventListener("click", () => {
  const show = passwordEl.type === "password";
  passwordEl.type = show ? "text" : "password";
  showButton.textContent = show ? "Ẩn" : "Hiện";
  showButton.setAttribute("aria-pressed", String(show));
});
["keydown", "keyup"].forEach((type) =>
  passwordEl.addEventListener(type, (e) => {
    if (e.getModifierState) capsHint.hidden = !e.getModifierState("CapsLock");
  })
);

// Google comes back to the page the person was heading for.
const googleLink = document.getElementById("google-login");
if (googleLink) {
  const asked = new URLSearchParams(location.search).get("next");
  if (asked && asked.startsWith("/") && !asked.startsWith("//")) {
    googleLink.href += `&next=${encodeURIComponent(asked)}`;
  }
}

form.onsubmit = async (e) => {
  e.preventDefault();
  submitButton.disabled = true;
  submitButton.textContent = "Đang đăng nhập…";
  messageBox.innerHTML = "";
  try {
    const r = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pseudonym: document.getElementById("pseudonym").value,
        password: document.getElementById("password").value,
      }),
    });
    if (r.ok) {
      // Go back to the page the user was heading for; otherwise to the start
      // page of their role (practice, queue or admin), which the server names.
      // Only same-site paths. Without this check, a link like
      // /login?next=https://evil.example sends the user to a copy of the login
      // page right after a real login, and `javascript:` would run in this
      // origin. A leading "//" is a protocol-relative URL, so it is rejected too.
      const d = await r.json().catch(() => ({}));
      const safe = (p) => typeof p === "string" && p.startsWith("/") && !p.startsWith("//");
      const asked = new URLSearchParams(location.search).get("next");
      // A temporary password goes to the account page whatever was asked for:
      // nothing else works until a new password is chosen (D028).
      if (d.must_change_password && safe(d.home)) {
        location.href = d.home;
        return;
      }
      location.href = safe(asked) ? asked : safe(d.home) ? d.home : "/";
      return;
    }
    const d = await r.json();
    // A 429 means the account is temporarily locked under NFR-07.
    const detail = d.detail || "Đăng nhập không thành công.";
    messageBox.innerHTML = `<p class="error">${window.escapeHtml(detail)}</p>`;
    document.getElementById("password").select();
  } catch (err) {
    messageBox.innerHTML = '<p class="error">Không kết nối được máy chủ.</p>';
  }
  submitButton.disabled = false;
  submitButton.textContent = "Đăng nhập";
};
