// Login screen. See docs/web/SPEC_WEB.md section M1.
const form = document.getElementById("f");
const submitButton = document.getElementById("b");
const messageBox = document.getElementById("tb");
const alertBox = document.getElementById("auth-alert");
const emailEl = document.getElementById("email");
const passwordEl = document.getElementById("password");
const showButton = document.getElementById("show-password");
const capsHint = document.getElementById("caps-hint");

const EYE_SLASH_ICON = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/><line x1="2" y1="2" x2="22" y2="22"/></svg>`;
const EYE_OPEN_ICON = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>`;

const TOAST_ICONS = {
  error: `<svg class="toast-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  success: `<svg class="toast-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
  warning: `<svg class="toast-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  info: `<svg class="toast-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
};

// Password Show/Hide toggle
if (showButton && passwordEl) {
  showButton.addEventListener("click", () => {
    const show = passwordEl.type === "password";
    passwordEl.type = show ? "text" : "password";
    showButton.setAttribute("aria-pressed", String(show));
    showButton.setAttribute("aria-label", show ? "Ẩn mật khẩu" : "Hiện mật khẩu");
    showButton.title = show ? "Ẩn mật khẩu" : "Hiện mật khẩu";
    showButton.innerHTML = show ? EYE_OPEN_ICON : EYE_SLASH_ICON;
  });
}

// Caps Lock hint
if (passwordEl && capsHint) {
  ["keydown", "keyup"].forEach((type) =>
    passwordEl.addEventListener(type, (e) => {
      if (e.getModifierState) capsHint.hidden = !e.getModifierState("CapsLock");
    })
  );
}

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

// Google OAuth next path preserved
const googleLink = document.getElementById("google-login");
if (googleLink) {
  const next = window.sitePath(safeNext(new URLSearchParams(location.search).get("next"), location.origin));
  if (next) {
    const start = new URL(googleLink.href, location.origin);
    start.searchParams.set("next", next);
    googleLink.href = start.pathname + start.search;
  }
}

// Google disabled button feedback
const googleDisabledBtn = document.getElementById("google-disabled-btn");
if (googleDisabledBtn) {
  googleDisabledBtn.addEventListener("click", (e) => {
    e.preventDefault();
    showToast("Đăng nhập bằng Google chưa bật trên máy này (thiếu khoá Google trong .env).", "info");
  });
}

// Toast notification manager
let toastTimer = null;
function showToast(message, type = "error") {
  if (!messageBox) return;
  clearTimeout(toastTimer);
  const icon = TOAST_ICONS[type] || TOAST_ICONS.error;
  const escaped = window.escapeHtml ? window.escapeHtml(message) : message;
  messageBox.innerHTML = `
    <div class="toast-item is-${type} error" role="alert">
      ${icon}
      <span class="toast-text">${escaped}</span>
      <button type="button" class="toast-close" aria-label="Đóng thông báo">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>`;

  const closeBtn = messageBox.querySelector(".toast-close");
  if (closeBtn) {
    closeBtn.onclick = (e) => {
      e.stopPropagation();
      clearTimeout(toastTimer);
      const item = messageBox.querySelector(".toast-item, .error");
      if (item) {
        item.classList.add("toast-out");
        setTimeout(() => { messageBox.innerHTML = ""; }, 200);
      } else {
        messageBox.innerHTML = "";
      }
    };
  }
  toastTimer = setTimeout(() => {
    const item = messageBox.querySelector(".toast-item, .error");
    if (item) {
      item.classList.add("toast-out");
      setTimeout(() => { messageBox.innerHTML = ""; }, 200);
    }
  }, 4500);
}

// Form-level alert banner helper
function showFormAlert(message) {
  if (!alertBox) return;
  const escaped = window.escapeHtml ? window.escapeHtml(message) : message;
  alertBox.innerHTML = `
    <svg class="alert-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>
    <span class="alert-text">${escaped}</span>
  `;
  alertBox.style.display = "flex";
}

function hideFormAlert() {
  if (!alertBox) return;
  alertBox.innerHTML = "";
  alertBox.style.display = "none";
}

// Field-level error helpers
function setFieldError(inputEl, message) {
  if (!inputEl) return;
  const field = inputEl.closest(".figma-field");
  if (!field) return;
  field.classList.add("has-error");
  inputEl.setAttribute("aria-invalid", "true");
  let errBox = field.querySelector(".auth-field-error");
  if (!errBox) {
    errBox = document.createElement("div");
    errBox.className = "auth-field-error";
    errBox.setAttribute("role", "alert");
    field.appendChild(errBox);
  }
  const escaped = window.escapeHtml ? window.escapeHtml(message) : message;
  errBox.innerHTML = `
    <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="8" cy="8" r="7"/><line x1="8" y1="5" x2="8" y2="8"/><circle cx="8" cy="11" r="0.5" fill="currentColor"/></svg>
    <span>${escaped}</span>
  `;
  errBox.style.display = "flex";
}

function clearFieldError(inputEl) {
  if (!inputEl) return;
  const field = inputEl.closest(".figma-field");
  if (!field) return;
  field.classList.remove("has-error");
  inputEl.removeAttribute("aria-invalid");
  const errBox = field.querySelector(".auth-field-error");
  if (errBox) {
    errBox.innerHTML = "";
    errBox.style.display = "none";
  }
}

// Validation rules
function validateEmail(val) {
  const trimmed = (val || "").trim();
  if (!trimmed) return "Hãy nhập email.";
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(trimmed)) {
    return "Hãy nhập một email hợp lệ.";
  }
  return null;
}

function validatePassword(val) {
  if (!val) return "Hãy nhập mật khẩu.";
  return null;
}

// Input event listeners (validate on blur, update on typing if already in error)
if (emailEl) {
  emailEl.addEventListener("blur", () => {
    emailEl.value = emailEl.value.trim();
    const err = validateEmail(emailEl.value);
    if (err) setFieldError(emailEl, err);
    else clearFieldError(emailEl);
  });
  emailEl.addEventListener("input", () => {
    hideFormAlert();
    if (emailEl.closest(".figma-field.has-error")) {
      const err = validateEmail(emailEl.value);
      if (!err) clearFieldError(emailEl);
      else setFieldError(emailEl, err);
    }
  });
}

if (passwordEl) {
  passwordEl.addEventListener("blur", () => {
    const err = validatePassword(passwordEl.value);
    if (err) setFieldError(passwordEl, err);
    else clearFieldError(passwordEl);
  });
  passwordEl.addEventListener("input", () => {
    hideFormAlert();
    if (passwordEl.closest(".figma-field.has-error")) {
      const err = validatePassword(passwordEl.value);
      if (!err) clearFieldError(passwordEl);
      else setFieldError(passwordEl, err);
    }
  });
}

// Handle Google server error if present
const googleServerErr = document.getElementById("google-error-msg");
if (googleServerErr && googleServerErr.dataset.error) {
  const err = googleServerErr.dataset.error;
  // If user deliberately cancelled, do not show a red error toast
  if (!err.includes("huỷ") && !err.includes("cancel")) {
    showToast(err, "error");
  }
}

// Check session expired from query params
if (new URLSearchParams(location.search).get("expired") === "1") {
  showToast("Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại.", "warning");
}

// Submit handler
if (form) {
  form.onsubmit = async (e) => {
    e.preventDefault();
    hideFormAlert();

    const emailErr = validateEmail(emailEl.value);
    const passErr = validatePassword(passwordEl.value);

    let firstInvalid = null;
    if (emailErr) {
      setFieldError(emailEl, emailErr);
      firstInvalid = firstInvalid || emailEl;
    } else {
      clearFieldError(emailEl);
    }

    if (passErr) {
      setFieldError(passwordEl, passErr);
      firstInvalid = firstInvalid || passwordEl;
    } else {
      clearFieldError(passwordEl);
    }

    if (firstInvalid) {
      firstInvalid.focus();
      return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "Đang đăng nhập…";
    try {
      const r = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: emailEl.value.trim(),
          password: passwordEl.value,
        }),
      });

      const d = await r.json().catch(() => ({}));
      if (r.ok) {
        // Back to the page the person was heading for, else the start page of
        // their role; only pages on this site (common.js, sitePath). A
        // temporary password goes to the account page whatever was asked (D028).
        const home = window.sitePath(safeNext(d.home, location.origin));
        const next = window.sitePath(safeNext(new URLSearchParams(location.search).get("next"), location.origin));
        const path = d.must_change_password && home ? home : next || home || "/";
        location.assign(location.origin + path);
        return;
      }

      if (r.status === 401) {
        showFormAlert(d.detail || "Email hoặc mật khẩu không đúng.");
        passwordEl.select();
        return;
      }

      if (r.status === 429) {
        // NFR-07: the account is locked for a while; the server says how long.
        showToast(d.detail || "Đăng nhập sai quá nhiều lần. Hãy thử lại sau.", "warning");
        return;
      }

      const detail = d.detail || "Đăng nhập không thành công. Hãy thử lại sau.";
      showToast(detail, "error");
      passwordEl.select();
    } catch (err) {
      if (!navigator.onLine) {
        showToast("Không có kết nối mạng. Hãy thử lại.", "error");
      } else {
        showToast("Không kết nối được máy chủ.", "error");
      }
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "Đăng nhập";
    }
  };
}
