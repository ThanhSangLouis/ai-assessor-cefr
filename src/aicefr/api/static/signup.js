// Self sign-up (D065, D071): an email, a full name and a password in; signed in.
const form = document.getElementById("f");
const submitButton = document.getElementById("b");
const messageBox = document.getElementById("tb");
const alertBox = document.getElementById("auth-alert");
const emailEl = document.getElementById("email");
const nameEl = document.getElementById("full-name");
const passwordEl = document.getElementById("password");
const againEl = document.getElementById("again");

const EYE_SLASH_ICON = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/><line x1="2" y1="2" x2="22" y2="22"/></svg>`;
const EYE_OPEN_ICON = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>`;

const TOAST_ICONS = {
  error: `<svg class="toast-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  success: `<svg class="toast-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
  warning: `<svg class="toast-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  info: `<svg class="toast-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
};

function bindPasswordToggle(btn, inputEl, labelPrefix) {
  if (!btn || !inputEl) return;
  btn.addEventListener("click", () => {
    const show = inputEl.type === "password";
    inputEl.type = show ? "text" : "password";
    btn.setAttribute("aria-pressed", String(show));
    btn.setAttribute("aria-label", show ? `Ẩn ${labelPrefix}` : `Hiện ${labelPrefix}`);
    btn.title = show ? `Ẩn ${labelPrefix}` : `Hiện ${labelPrefix}`;
    btn.innerHTML = show ? EYE_OPEN_ICON : EYE_SLASH_ICON;
  });
}
bindPasswordToggle(document.getElementById("show-password"), passwordEl, "mật khẩu");
bindPasswordToggle(document.getElementById("show-again"), againEl, "mật khẩu nhập lại");

const legacyShow = document.getElementById("show");
if (legacyShow) {
  legacyShow.addEventListener("change", (e) => {
    [passwordEl, againEl].forEach((el) => {
      if (el) el.type = e.target.checked ? "text" : "password";
    });
  });
}

// Google comes back to the page the person was heading for.
const googleLink = document.getElementById("google-login");
if (googleLink) {
  const asked = new URLSearchParams(location.search).get("next");
  if (window.samePath(asked)) {
    googleLink.href += `&next=${encodeURIComponent(asked)}`;
  }
}

// Show toast when Google OAuth credentials are not configured on the machine.
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

// Form-level alert helper
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

function validateFullName(val) {
  const trimmed = (val || "").trim();
  if (!trimmed) return "Hãy nhập họ và tên.";
  if (trimmed.length > 80) return "Họ và tên tối đa 80 ký tự.";
  return null;
}

function validatePassword(val) {
  if (!val) return "Hãy nhập mật khẩu.";
  const min = (passwordEl && Number(passwordEl.getAttribute("minlength"))) || 8;
  if (val.length < min) return `Mật khẩu cần ít nhất ${min} ký tự.`;
  return null;
}

function validateConfirmPassword(val, pwdVal) {
  if (!val) return "Hãy nhập lại mật khẩu.";
  if (val !== pwdVal) return "Hai lần nhập mật khẩu chưa khớp nhau.";
  return null;
}

// Event listeners for blur and active error clearance
if (emailEl) {
  emailEl.addEventListener("blur", () => {
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

if (nameEl) {
  nameEl.addEventListener("blur", () => {
    const err = validateFullName(nameEl.value);
    if (err) setFieldError(nameEl, err);
    else clearFieldError(nameEl);
  });
  nameEl.addEventListener("input", () => {
    hideFormAlert();
    if (nameEl.closest(".figma-field.has-error")) {
      const err = validateFullName(nameEl.value);
      if (!err) clearFieldError(nameEl);
      else setFieldError(nameEl, err);
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
    // If confirm password already has a value, re-validate confirm password
    if (againEl && againEl.value) {
      const againErr = validateConfirmPassword(againEl.value, passwordEl.value);
      if (!againErr) clearFieldError(againEl);
      else if (againEl.closest(".figma-field.has-error")) setFieldError(againEl, againErr);
    }
  });
}

if (againEl) {
  againEl.addEventListener("blur", () => {
    const err = validateConfirmPassword(againEl.value, passwordEl ? passwordEl.value : "");
    if (err) setFieldError(againEl, err);
    else clearFieldError(againEl);
  });
  againEl.addEventListener("input", () => {
    hideFormAlert();
    if (againEl.closest(".figma-field.has-error")) {
      const err = validateConfirmPassword(againEl.value, passwordEl ? passwordEl.value : "");
      if (!err) clearFieldError(againEl);
      else setFieldError(againEl, err);
    }
  });
}

// Form submission handler
if (form) {
  form.onsubmit = async (e) => {
    e.preventDefault();
    hideFormAlert();

    const emailErr = validateEmail(emailEl.value);
    const nameErr = validateFullName(nameEl.value);
    const passErr = validatePassword(passwordEl.value);
    const againErr = validateConfirmPassword(againEl.value, passwordEl.value);

    let firstInvalid = null;

    if (emailErr) {
      setFieldError(emailEl, emailErr);
      firstInvalid = firstInvalid || emailEl;
    } else {
      clearFieldError(emailEl);
    }

    if (nameErr) {
      setFieldError(nameEl, nameErr);
      firstInvalid = firstInvalid || nameEl;
    } else {
      clearFieldError(nameEl);
    }

    if (passErr) {
      setFieldError(passwordEl, passErr);
      firstInvalid = firstInvalid || passwordEl;
    } else {
      clearFieldError(passwordEl);
    }

    if (againErr) {
      setFieldError(againEl, againErr);
      firstInvalid = firstInvalid || againEl;
    } else {
      clearFieldError(againEl);
    }

    if (firstInvalid) {
      firstInvalid.focus();
      return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "Đang tạo…";

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

      if (r.ok) {
        form.hidden = true;
        const doneBox = document.getElementById("done");
        if (doneBox) doneBox.hidden = false;

        // D079: a verification code went out with the account.
        const verifyNote = document.getElementById("verify-note");
        if (verifyNote) verifyNote.hidden = d.email_verification !== "sent";

        const go = document.getElementById("go");
        if (go && window.samePath(d.home)) {
          go.href = d.home;
        }
        return;
      }

      if (r.status === 409) {
        setFieldError(emailEl, "Email này đã có tài khoản. Hãy đăng nhập.");
        emailEl.focus();
        return;
      }

      if (r.status === 429) {
        showToast("Thử quá nhiều lần. Hãy thử lại sau.", "warning");
        return;
      }

      const detail = typeof d.detail === "string" ? d.detail : "Không tạo được tài khoản. Hãy kiểm tra lại thông tin.";
      if (r.status === 422 && (detail.includes("mật khẩu") || detail.includes("password"))) {
        setFieldError(passwordEl, detail);
        passwordEl.focus();
      } else {
        showFormAlert(detail);
      }
    } catch (err) {
      if (!navigator.onLine) {
        showToast("Không có kết nối mạng. Hãy thử lại.", "error");
      } else {
        showToast("Không kết nối được máy chủ. Tài khoản chưa được tạo.", "error");
      }
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "Tạo tài khoản";
    }
  };
}
