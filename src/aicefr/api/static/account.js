// The account page (D028, D029): profile, security, history and data.
//
// Tabs switch without reloading and keep their place in the URL (#security),
// as on the admin page. An account still on a temporary password gets the
// password form alone: everything else would be refused by the server.
//
// The rules shown under the new-password field tick themselves as the person
// types, so a refusal from the server is the exception, not the way to learn
// the rules. The server checks them again; this is only the courtesy layer.
const escapeHtml = window.escapeHtml;
const homeEl = document.getElementById("account-home");
const home = homeEl.dataset.home || "/";
const firstTime = !!homeEl.dataset.first;

let me = null;

// ---------------------------------------------------------------- tabs
const TABS = ["profile", "security", "data"]
  .map((key) => ({ key, button: document.getElementById(`tab-${key}`), panel: document.getElementById(`panel-${key}`) }))
  .filter((t) => t.button && t.panel);
const loaded = new Set();
const LOADERS = {
  security: () => {
    loadSessions();
    loadActivity();
  },
};

function showTab(tab) {
  TABS.forEach((t) => {
    const chosen = t === tab;
    t.button.classList.toggle("chosen", chosen);
    t.button.setAttribute("aria-selected", chosen ? "true" : "false");
    t.panel.hidden = !chosen;
  });
  // Security is read fresh each time it opens: it shows what just happened
  // (a session ended, a sign-in), and "#activity" lands on it (D068).
  if (LOADERS[tab.key] && (!loaded.has(tab.key) || tab.key === "security")) {
    loaded.add(tab.key);
    LOADERS[tab.key]();
  }
}

TABS.forEach((t, i) => {
  t.button.addEventListener("click", () => {
    history.replaceState(null, "", `#${t.key}`);
    showTab(t);
  });
  t.button.addEventListener("keydown", (e) => {
    const step = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    e.preventDefault();
    const next = TABS[(i + step + TABS.length) % TABS.length];
    next.button.focus();
    next.button.click();
  });
});

// "#activity" is the old address of the history, now part of security (D068).
const tabFromHash = () =>
  TABS.find((t) => `#${t.key}` === (location.hash === "#activity" ? "#security" : location.hash)) ||
  TABS[0];
if (TABS.length) {
  window.addEventListener("hashchange", () => showTab(tabFromHash()));
  showTab(tabFromHash());
}

// ---------------------------------------------------------------- facts
function setFact(name, value) {
  const el = document.querySelector(`[data-fact="${name}"]`);
  if (el) el.textContent = value;
}

function loadMe() {
  return fetch("/api/v1/me/account")
    .then((r) => (window.redirectToLoginIfExpired(r) ? null : r.json()))
    .then((data) => {
      if (!data) return null;
      me = data;
      const facts = document.getElementById("me-facts");
      if (facts) window.clearBusy(facts);
      const when = (iso) => (iso ? window.ui.localTime(iso) : "Chưa có");
      setFact("created_at", when(data.created_at));
      setFact("last_login_at", when(data.last_login_at));
      setFact("password_changed_at", when(data.password_changed_at));
      document.getElementById("first-time").hidden = !data.must_change_password;
      paintGoogle();
      paintRecovery();
      checkRules();
      return data;
    })
    .catch(() => null);
}

// ---------------------------------------------------------------- profile
const avatarPreview = document.getElementById("avatar-preview");
const avatarSave = document.getElementById("avatar-save");

function chosen(name) {
  const input = document.querySelector(`input[name="${name}"]:checked`);
  return input ? input.value : null;
}

// The big avatar in the page head follows the choice before it is saved, so
// the person sees what they are about to keep.
function paintAvatar() {
  const iconName = chosen("avatar-icon") || "user";
  const color = chosen("avatar-color");
  avatarPreview.className = `avatar-lg avatar-${color || "none"}`;
  avatarPreview.innerHTML = window.ui.icon(iconName);
}

document.querySelectorAll('input[name="avatar-icon"], input[name="avatar-color"]').forEach((input) =>
  input.addEventListener("change", paintAvatar)
);

async function patchProfile(body) {
  const r = await fetch("/api/v1/me/profile", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (window.redirectToLoginIfExpired(r)) return null;
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    window.toast(typeof d.detail === "string" ? d.detail : "Không lưu được.", "error");
    return null;
  }
  return d;
}

if (avatarSave) {
  avatarSave.addEventListener("click", async () => {
    avatarSave.disabled = true;
    const body = { avatar_icon: chosen("avatar-icon") || "user" };
    const color = chosen("avatar-color");
    if (color) body.avatar_color = color;
    const d = await patchProfile(body);
    avatarSave.disabled = false;
    if (!d) return;
    // The sidebar's own avatar changes at once, not at the next page load.
    const small = document.querySelector(".account-button .avatar");
    if (small) {
      small.className = `avatar avatar-${d.avatar_color || "none"}`;
      small.innerHTML = window.ui.icon(d.avatar_icon || "user");
    }
    window.toast("Đã lưu ảnh đại diện.", "ok");
  });
}

// Display preferences live in this browser only (window.ui.prefs, common.js).
const themeSelect = document.getElementById("pref-theme");
const fontSelect = document.getElementById("pref-font");
if (themeSelect && window.ui.prefs) {
  themeSelect.value = window.ui.prefs.theme();
  fontSelect.value = window.ui.prefs.font();
  themeSelect.addEventListener("change", () => window.ui.prefs.setTheme(themeSelect.value));
  fontSelect.addEventListener("change", () => window.ui.prefs.setFont(fontSelect.value));
}

// ---------------------------------------------------------------- password
const form = document.getElementById("pw-form");
const currentEl = document.getElementById("pw-current");
const newEl = document.getElementById("pw-new");
const againEl = document.getElementById("pw-again");
const showEl = document.getElementById("pw-show");
const saveEl = document.getElementById("pw-save");
const messageEl = document.getElementById("pw-message");

// Each rule line ticks when it holds; the minimum comes from the server.
function checkRules() {
  const value = newEl.value;
  const min = (me && me.min_password_length) || Number(newEl.getAttribute("minlength")) || 8;
  const pseudonym = me ? me.pseudonym : "";
  const rules = {
    length: value.length >= min,
    pseudonym: !!value && value.trim().toLowerCase() !== pseudonym.trim().toLowerCase(),
    different: !!value && value !== currentEl.value,
  };
  document.querySelectorAll("#pw-rules [data-rule]").forEach((li) => {
    li.classList.toggle("met", !!rules[li.dataset.rule]);
  });
  return Object.values(rules).every(Boolean);
}

[newEl, currentEl].forEach((el) => el.addEventListener("input", checkRules));

showEl.addEventListener("change", () => {
  const type = showEl.checked ? "text" : "password";
  [currentEl, newEl, againEl].forEach((el) => {
    el.type = type;
  });
});

function say(html, kind) {
  messageEl.innerHTML = `<p class="${kind}">${html}</p>`;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  messageEl.innerHTML = "";
  if (!currentEl.value) {
    say("Hãy nhập mật khẩu hiện tại.", "error");
    currentEl.focus();
    return;
  }
  if (!checkRules()) {
    say("Mật khẩu mới chưa đạt các điều kiện ở trên.", "error");
    newEl.focus();
    return;
  }
  if (newEl.value !== againEl.value) {
    say("Hai lần nhập mật khẩu mới chưa khớp nhau.", "error");
    againEl.focus();
    return;
  }
  saveEl.disabled = true;
  try {
    const r = await fetch("/api/v1/me/password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: currentEl.value, new_password: newEl.value }),
    });
    if (window.redirectToLoginIfExpired(r)) return;
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      const detail = typeof d.detail === "string" ? d.detail : "Không đổi được mật khẩu.";
      say(escapeHtml(detail), "error");
      return;
    }
    form.reset();
    checkRules();
    const ended = Number(d.sessions_ended) || 0;
    window.toast(
      ended ? `Đã đổi mật khẩu và đăng xuất ${ended} thiết bị khác.` : "Đã đổi mật khẩu.",
      "ok"
    );
    if (firstTime) {
      // The rest of the system opens now; go where this role starts its work.
      location.href = d.home || home;
      return;
    }
    loadMe();
    if (loaded.has("security")) loadSessions();
  } catch (err) {
    say("Không kết nối được máy chủ. Mật khẩu chưa được đổi.", "error");
  } finally {
    saveEl.disabled = false;
  }
});

// ---------------------------------------------------------------- Google
const googleState = document.getElementById("google-state");
const googleLink = document.getElementById("google-link");
const googleUnlink = document.getElementById("google-unlink");

function paintGoogle() {
  if (!googleState || !me) return;
  const g = me.google || {};
  const domain = g.domain ? ` Chỉ tài khoản thuộc tên miền ${escapeHtml(g.domain)}.` : "";
  googleState.innerHTML = g.linked
    ? `<span class="success">Đã liên kết</span> từ ${escapeHtml(window.ui.localTime(g.linked_at))}. ` +
      "Bạn đăng nhập được bằng Google hoặc bằng mật khẩu."
    : `Chưa liên kết. Liên kết để đăng nhập bằng Google thay cho mật khẩu.${domain}`;
  googleLink.hidden = !!g.linked;
  googleUnlink.hidden = !g.linked;
}

if (googleUnlink) {
  googleUnlink.addEventListener("click", async () => {
    if (!window.confirm("Gỡ liên kết Google? Sau đó chỉ đăng nhập được bằng bút danh và mật khẩu.")) return;
    googleUnlink.disabled = true;
    const r = await fetch("/api/v1/me/google/unlink", { method: "POST" });
    googleUnlink.disabled = false;
    if (window.redirectToLoginIfExpired(r)) return;
    await r.json().catch(() => ({}));
    if (!r.ok) {
      window.toast("Không gỡ được liên kết Google.", "error");
      return;
    }
    window.toast("Đã gỡ liên kết Google.", "ok");
    loadMe();
  });
}

// ---------------------------------------------------------------- recovery code
// D065: whether a code is in force; a new one is shown once on the slip.
const recoveryState = document.getElementById("recovery-state");
const recoveryNew = document.getElementById("recovery-new");

function paintRecovery() {
  if (!recoveryState || !me) return;
  const at = me.recovery && me.recovery.issued_at;
  recoveryState.innerHTML = at
    ? `<span class="success">Đang có mã</span>, tạo lúc ${escapeHtml(window.ui.localTime(at))}.`
    : "Chưa có mã khôi phục. Tạo một mã và cất ở nơi an toàn để tự đặt lại mật khẩu khi quên.";
}

if (recoveryNew) {
  recoveryNew.addEventListener("click", async () => {
    if (me && me.recovery && me.recovery.issued_at &&
        !window.confirm("Tạo mã mới? Mã khôi phục cũ sẽ hết hiệu lực.")) return;
    recoveryNew.disabled = true;
    try {
      const r = await fetch("/api/v1/me/recovery-code", { method: "POST" });
      if (window.redirectToLoginIfExpired(r)) return;
      const d = await r.json().catch(() => ({}));
      if (!r.ok) {
        window.toast(typeof d.detail === "string" ? d.detail : "Không tạo được mã.", "error");
        return;
      }
      window.showRecoverySlip(me.pseudonym, d.recovery_code);
      window.toast("Đã tạo mã khôi phục mới. Hãy lưu lại: mã chỉ hiện lần này.", "ok");
      loadMe();
    } finally {
      recoveryNew.disabled = false;
    }
  });
}

// ---------------------------------------------------------------- sessions
const sessionList = document.getElementById("session-list");
const METHOD_NAMES = { password: "mật khẩu", google: "Google", recovery: "mã khôi phục" };

function sessionItem(s) {
  const device = s.device || "Thiết bị không rõ";
  const label = `Đăng xuất phiên trên ${device}`;
  return `<li class="session${s.current ? " current" : ""}">
    <span class="session-icon" aria-hidden="true">${window.ui.icon(s.current ? "check-circle" : "user")}</span>
    <span class="session-main">
      <b>${escapeHtml(device)}</b>${s.current ? ' <span class="badge COMPLETED">Máy này</span>' : ""}
      <span class="cell-sub">Đăng nhập bằng ${escapeHtml(METHOD_NAMES[s.method] || s.method)} lúc
        ${escapeHtml(window.ui.localTime(s.created_at))} · hết hạn ${escapeHtml(window.ui.localTime(s.expires_at))}</span>
    </span>
    <button type="button" class="link-button" data-session="${escapeHtml(s.session_id)}"
      aria-label="${escapeHtml(label)}">Đăng xuất</button>
  </li>`;
}

function loadSessions() {
  if (!sessionList) return;
  fetch("/api/v1/me/sessions")
    .then((r) => (window.redirectToLoginIfExpired(r) ? null : r.json()))
    .then((rows) => {
      if (!rows) return;
      window.clearBusy(sessionList);
      sessionList.innerHTML = rows.length
        ? rows.map(sessionItem).join("")
        : '<li class="muted">Không có phiên nào đang mở.</li>';
    })
    .catch(() => {
      window.clearBusy(sessionList);
      sessionList.innerHTML = '<li class="error">Không tải được danh sách phiên.</li>';
    });
}

if (sessionList) {
  sessionList.addEventListener("click", async (e) => {
    const button = e.target.closest("[data-session]");
    if (!button) return;
    button.disabled = true;
    const r = await fetch(`/api/v1/me/sessions/${encodeURIComponent(button.dataset.session)}`, {
      method: "DELETE",
    });
    if (window.redirectToLoginIfExpired(r)) return;
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      button.disabled = false;
      window.toast("Không đăng xuất được phiên này.", "error");
      return;
    }
    if (d.current) {
      // Ending the session in use is signing out.
      location.href = "/login";
      return;
    }
    window.toast("Đã đăng xuất phiên đó.", "ok");
    loadSessions();
  });
}

const revokeEl = document.getElementById("revoke-others");
if (revokeEl) {
  revokeEl.addEventListener("click", async () => {
    revokeEl.disabled = true;
    try {
      const r = await fetch("/api/v1/me/sessions/revoke-others", { method: "POST" });
      if (window.redirectToLoginIfExpired(r)) return;
      const d = await r.json().catch(() => ({}));
      if (!r.ok) {
        window.toast(d.detail || "Không đăng xuất được các thiết bị khác.", "error");
        return;
      }
      const n = Number(d.revoked) || 0;
      window.toast(n ? `Đã đăng xuất ${n} thiết bị khác.` : "Không có thiết bị nào khác đang đăng nhập.", "ok");
      loadSessions();
    } finally {
      revokeEl.disabled = false;
    }
  });
}

// ---------------------------------------------------------------- activity
const activityList = document.getElementById("activity-list");
// What happened, said from the person's side. An action missing here still
// shows, under its code, rather than disappearing from the history.
const ACTIVITY = {
  "auth.login": ["logout", "Đăng nhập"],
  "auth.login_failed": ["alert", "Đăng nhập không thành công"],
  "account.create": ["user-plus", "Tài khoản được tạo"],
  "account.password_change": ["lock", "Đổi mật khẩu"],
  "account.reset_password": ["key", "Được cấp mật khẩu tạm mới"],
  "account.sessions_revoked": ["logout", "Đăng xuất các thiết bị khác"],
  "account.session_revoked": ["logout", "Đăng xuất một phiên"],
  "account.disable": ["power", "Tài khoản bị tắt"],
  "account.enable": ["check", "Tài khoản được bật lại"],
  "account.unlock": ["unlock", "Được gỡ khoá đăng nhập"],
  "account.role_change": ["shield", "Đổi vai trò"],
  "account.google_link": ["plus", "Liên kết Google"],
  "account.google_unlink": ["x", "Gỡ liên kết Google"],
  "account.profile": ["sparkle", "Sửa hồ sơ"],
  "account.signup": ["user-plus", "Tự đăng ký tài khoản"],
  "account.google_signup": ["user-plus", "Đăng ký bằng Google"],
  "account.recovery_code": ["key", "Tạo mã khôi phục mới"],
  "account.recover": ["unlock", "Đặt lại mật khẩu bằng mã khôi phục"],
  "auth.recover_failed": ["alert", "Thử mã khôi phục không thành công"],
};
const DETAIL = {
  "method=password": "bằng mật khẩu",
  "method=google": "bằng Google",
  wrong_password: "sai mật khẩu",
  wrong_code: "sai mã khôi phục",
  locked: "tài khoản đang tạm khoá",
};

function activityItem(a) {
  const [iconName, text] = ACTIVITY[a.action] || ["info", a.action];
  const detail = DETAIL[a.detail] ? " " + DETAIL[a.detail] : "";
  // A failed attempt carries the pseudonym it was made against, not who made
  // it: calling it "you" would hide exactly the attempt worth noticing.
  const who =
    a.action === "auth.login_failed" ? "Không rõ ai thử" : a.by_self ? "Bạn" : "Quản trị viên";
  const warn = a.action === "auth.login_failed" ? " warn" : "";
  return `<li class="activity${warn}">
    <span class="activity-icon" aria-hidden="true">${window.ui.icon(iconName)}</span>
    <span class="activity-main"><b>${escapeHtml(text)}${escapeHtml(detail)}</b>
      <span class="cell-sub">${escapeHtml(who)} · ${escapeHtml(window.ui.localTime(a.created_at))}</span></span>
  </li>`;
}

function loadActivity() {
  if (!activityList) return;
  fetch("/api/v1/me/activity")
    .then((r) => (window.redirectToLoginIfExpired(r) ? null : r.json()))
    .then((rows) => {
      if (!rows) return;
      window.clearBusy(activityList);
      activityList.innerHTML = rows.length
        ? rows.map(activityItem).join("")
        : '<li class="muted">Chưa có hoạt động nào được ghi.</li>';
    })
    .catch(() => window.clearBusy(activityList));
}

// FR-34. Through fetch first, so an expired session goes to the login page
// instead of downloading an error page.
const exportAll = document.getElementById("export-all");
if (exportAll) {
  exportAll.addEventListener("click", async () => {
    exportAll.disabled = true;
    try {
      const r = await fetch("/api/v1/me/export.json");
      if (window.redirectToLoginIfExpired(r)) return;
      if (!r.ok) throw new Error("export failed");
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "du-lieu-cua-toi.json";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      window.toast("Đã tải dữ liệu của bạn.", "ok");
    } catch (err) {
      window.toast("Không tải được dữ liệu. Hãy thử lại sau.", "error");
    } finally {
      exportAll.disabled = false;
    }
  });
}

loadMe();
