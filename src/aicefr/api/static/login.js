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

// Where to go after login: a path of this site, or null. Only same-site paths.
// Without this check, a link like /login?next=https://evil.example sends the
// user to a copy of the login page right after a real login, and `javascript:`
// would run in this origin. A leading "//" is a protocol-relative URL, so it
// is rejected too. SEC-04: startsWith alone missed "/\evil.example" and
// "/<tab>/evil.example": the browser reads a backslash as "/" and drops tab
// and newline, so both leave the site. Such characters are refused, written
// plainly or percent-encoded, and what is left must resolve to this origin.
// The same rule is safe_next in aicefr/auth/google.py.
function safeNext(value, origin) {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//")) {
    return null;
  }
  if (/[\\\s\u0000-\u001f\u007f-\u009f]/.test(value)) return null;
  let decoded;
  try {
    decoded = decodeURIComponent(value);
  } catch (err) {
    return null;
  }
  if (decoded.startsWith("//") || /[\\\u0000-\u001f\u007f-\u009f]/.test(decoded)) return null;
  let url;
  try {
    url = new URL(value, origin);
  } catch (err) {
    return null;
  }
  if (url.origin !== origin || (url.protocol !== "http:" && url.protocol !== "https:")) {
    return null;
  }
  return url.pathname + url.search + url.hash;
}

// Google comes back to the page the person was heading for.
const googleLink = document.getElementById("google-login");
if (googleLink) {
  const asked = safeNext(new URLSearchParams(location.search).get("next"), location.origin);
  if (asked) {
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
        email: document.getElementById("pseudonym").value.trim(),
        password: document.getElementById("password").value,
      }),
    });
    if (r.ok) {
      // Go back to the page the user was heading for; otherwise to the start
      // page of their role (practice, queue or admin), which the server names.
      // Both go through safeNext above.
      const d = await r.json().catch(() => ({}));
      const asked = safeNext(new URLSearchParams(location.search).get("next"), location.origin);
      const home = safeNext(d.home, location.origin);
      // A temporary password goes to the account page whatever was asked for:
      // nothing else works until a new password is chosen (D028).
      if (d.must_change_password && home) {
        location.href = home;
        return;
      }
      location.href = asked || home || "/";
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
