// Administration screen: eight tabs behind one page. FR-08, FR-32 (accounts,
// D028), FR-34, FR-35, FR-36, NFR-11.
//
// Tabs switch without reloading, and each tab fetches its data the first time
// it is opened. Reason: three of the four tabs hit admin-only endpoints, and
// loading all of them up front would fire four requests for a page where the
// reader usually only wants one of them.

const TABS = [
  { button: "tab-accounts", panel: "panel-accounts", load: loadAccounts },
  { button: "tab-models", panel: "panel-models", load: loadModels },
  // D078. The prices of the runs live in admin_prices.js, loaded first.
  {
    button: "tab-config",
    panel: "panel-config",
    load: () => {
      loadConfig();
      window.adminPrices.load();
    },
  },
  { button: "tab-erase", panel: "panel-erase", load: null },
  // D072. The language model's use lives in admin_coach.js, loaded first.
  { button: "tab-coach", panel: "panel-coach", load: () => window.adminCoach.load() },
  { button: "tab-ops", panel: "panel-ops", load: loadOps },
];

const loaded = new Set();
const escapeHtml = window.escapeHtml;
// How a person is named to the administrator: the full name, else the email,
// else the account code of an account that has neither yet (D071).
const nameOf = (a) => a.full_name || a.email || a.pseudonym;

// Every admin endpoint is behind require_role(ADMIN). A 401 means the session
// expired; a 403 means the account is logged in but is a student or a teacher.
// Both have to say so plainly instead of leaving an empty panel behind.
function permissionMessage(status) {
  if (status === 403) {
    return `<p class="error">Tài khoản của bạn <b>không có quyền quản trị</b>.
      Màn hình này chỉ dành cho vai trò <code>admin</code>. Hãy đăng nhập bằng
      tài khoản quản trị hoặc liên hệ người phụ trách hệ thống.</p>`;
  }
  if (status === 404) {
    return `<p class="error">Máy chủ chưa có API cho phần này
      (HTTP 404). Vui lòng cập nhật phiên bản máy chủ.</p>`;
  }
  return `<p class="error">Không tải được dữ liệu (HTTP ${escapeHtml(status)}).</p>`;
}

// Returns the parsed body, or null when the caller should stop. A 401 has
// already navigated away by the time null comes back.
async function getJson(url, targetEl) {
  let r;
  try {
    r = await fetch(url);
  } catch (e) {
    if (targetEl) { window.clearBusy(targetEl); targetEl.innerHTML = '<p class="error">Không kết nối được máy chủ.</p>'; }
    return null;
  }
  if (window.redirectToLoginIfExpired(r)) return null;
  if (!r.ok) {
    if (targetEl) { window.clearBusy(targetEl); targetEl.innerHTML = permissionMessage(r.status); }
    return null;
  }
  return r.json();
}

function showTab(chosen) {
  TABS.forEach((t) => {
    const isChosen = t.button === chosen.button;
    const button = document.getElementById(t.button);
    button.classList.toggle("chosen", isChosen);
    // The class alone is invisible to a screen reader; aria-selected is what a
    // tab announces as its state.
    button.setAttribute("aria-selected", isChosen ? "true" : "false");
    document.getElementById(t.panel).hidden = !isChosen;
  });
  if (chosen.load && !loaded.has(chosen.button)) {
    loaded.add(chosen.button);
    chosen.load();
  }
}

// The open tab lives in the URL (#config), so a reload or a shared link lands
// on the same tab. Arrow keys move between tabs, as the ARIA tabs pattern
// expects of a role="tablist".
const tabKey = (t) => t.panel.replace("panel-", "");

TABS.forEach((t, i) => {
  const button = document.getElementById(t.button);
  button.addEventListener("click", () => {
    history.replaceState(null, "", `#${tabKey(t)}`);
    showTab(t);
  });
  button.addEventListener("keydown", (e) => {
    const step = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    e.preventDefault();
    const next = TABS[(i + step + TABS.length) % TABS.length];
    document.getElementById(next.button).focus();
    document.getElementById(next.button).click();
  });
});

// ---------- Tab: accounts (FR-32, D028) ----------
//
// Pseudonyms only. A one-time password comes back from the server once, is
// shown on printable slips and in a CSV, and is gone once the slips are hidden:
// the server keeps only its hash.

const ROLE_NAMES = { student: "Sinh viên", teacher: "Giảng viên", admin: "Quản trị" };
const DEFAULT_PREFIX = { student: "SV", teacher: "GV", admin: "QT" };
const accountsEl = document.getElementById("accounts-body");
const accForm = document.getElementById("acc-form");
const accRole = document.getElementById("acc-role");
const accMode = document.getElementById("acc-mode");
const accCount = document.getElementById("acc-count");
const accPrefix = document.getElementById("acc-prefix");
const accPseudonym = document.getElementById("acc-pseudonym");
const accPreview = document.getElementById("acc-preview");
const accSearch = document.getElementById("acc-search");
const accFilter = document.getElementById("acc-filter");
const slipsEl = document.getElementById("slips");
const slipGrid = document.getElementById("slip-grid");

let accounts = [];
let slips = [];

function nextNumbers(prefix, count) {
  const re = new RegExp(`^${prefix}-(\\d+)$`, "i");
  const used = accounts
    .map((a) => (re.exec(a.pseudonym) || [])[1])
    .filter(Boolean)
    .map(Number);
  const start = (used.length ? Math.max(...used) : 0) + 1;
  const width = Math.max(3, String(start + count - 1).length);
  const name = (n) => `${prefix}-${String(n).padStart(width, "0")}`;
  return count > 1 ? `${name(start)} → ${name(start + count - 1)}` : name(start);
}

// "Sẽ tạo SV-011 → SV-020": the same continuation rule as the server, so the
// administrator sees which pseudonyms are about to exist before pressing.
function paintPreview() {
  const series = accMode.value === "series";
  accForm.querySelectorAll("[data-mode]").forEach((el) => {
    el.hidden = el.dataset.mode !== accMode.value;
  });
  accPrefix.placeholder = DEFAULT_PREFIX[accRole.value];
  if (!series) {
    accPreview.textContent = "";
    return;
  }
  const prefix = (accPrefix.value.trim() || DEFAULT_PREFIX[accRole.value]).toUpperCase();
  const count = Math.min(200, Math.max(1, Number(accCount.value) || 1));
  accPreview.textContent = /^[A-Z]{1,6}$/.test(prefix)
    ? `Sẽ tạo ${nextNumbers(prefix, count)}`
    : "Tiền tố chỉ gồm 1 đến 6 chữ cái không dấu.";
}
[accRole, accMode, accCount, accPrefix].forEach((el) => el.addEventListener("input", paintPreview));

function avatarHtml(a) {
  return `<span class="avatar avatar-${escapeHtml(a.avatar_color || "none")}" aria-hidden="true">` +
    `${window.ui.icon(a.avatar_icon || "user")}</span>`;
}

function accountState(a) {
  const chips = [];
  if (a.disabled) chips.push('<span class="badge FAILED">Đã tắt</span>');
  else chips.push('<span class="badge COMPLETED">Đang dùng</span>');
  if (a.locked_until) chips.push('<span class="badge REJECTED">Tạm khoá</span>');
  if (a.must_change_password) chips.push('<span class="badge REVIEW_REQUIRED">Chờ đổi mật khẩu tạm</span>');
  if (a.google_linked) chips.push('<span class="badge QUEUED">Có Google</span>');
  return chips.join(" ");
}

function iconButton(action, a, icon, label, extra = "") {
  return (
    `<button type="button" class="icon-only ${extra}" data-account-action="${action}"` +
    ` data-account="${escapeHtml(a.account_id)}" aria-label="${escapeHtml(label)}" title="${escapeHtml(label)}">` +
    `${window.ui.icon(icon)}</button>`
  );
}

function accountActions(a) {
  const who = nameOf(a);
  if (a.account_id === myAccountId) {
    return '<span class="muted small-note">Tài khoản của bạn</span>';
  }
  let h = iconButton("reset", a, "key", `Cấp mật khẩu tạm mới cho ${who}`);
  if (a.locked_until) h += iconButton("unlock", a, "unlock", `Gỡ khoá đăng nhập của ${who}`);
  h += a.disabled
    ? iconButton("enable", a, "check", `Bật lại tài khoản ${who}`)
    : iconButton("disable", a, "power", `Tắt tài khoản ${who}`, "danger");
  return `<div class="row-actions">${h}</div>`;
}

function renderAccounts() {
  const q = accSearch.value.trim().toLowerCase();
  const role = accFilter.value;
  const rows = accounts.filter(
    (a) =>
      (!role || a.role === role) &&
      (!q || [a.pseudonym, a.email, a.full_name].some((v) => (v || "").toLowerCase().includes(q)))
  );
  const counts = Object.keys(ROLE_NAMES)
    .map((r) => `${ROLE_NAMES[r]} ${accounts.filter((a) => a.role === r).length}`)
    .join(" · ");
  if (!rows.length) {
    accountsEl.innerHTML = `<p class="muted">${accounts.length ? "Không có tài khoản nào khớp." : "Chưa có tài khoản nào."}</p>`;
    return;
  }
  let h = `<p class="muted">${escapeHtml(counts)}</p>
    <table class="accounts-table">
      <thead><tr><th>Người dùng</th><th>Đăng nhập gần nhất</th><th>Trạng thái</th><th>Thao tác</th></tr></thead>
      <tbody>`;
  rows.forEach((a) => {
    const last = a.last_login_at ? window.ui.localTime(a.last_login_at) : "Chưa đăng nhập";
    const sessions = a.active_sessions ? ` · ${a.active_sessions} phiên đang mở` : "";
    h += `<tr class="${a.disabled ? "row-muted" : ""}">
      <td><span class="account-cell">${avatarHtml(a)}<span>
        <button type="button" class="link-button account-open" data-account-open="${escapeHtml(a.account_id)}"
          aria-label="${escapeHtml("Xem chi tiết " + (a.full_name || a.pseudonym))}">${escapeHtml(a.full_name || a.pseudonym)}</button>
        <span class="cell-sub">${escapeHtml(a.email || "chưa có email")} · ${escapeHtml(ROLE_NAMES[a.role] || a.role)} · <code>${escapeHtml(a.pseudonym)}</code></span></span></span></td>
      <td>${escapeHtml(last)}<span class="cell-sub">${escapeHtml(sessions)}</span></td>
      <td>${accountState(a)}</td>
      <td class="action-cell">${accountActions(a)}</td>
    </tr>`;
  });
  accountsEl.innerHTML = h + "</tbody></table>";
}
[accSearch, accFilter].forEach((el) => el.addEventListener("input", renderAccounts));

// The administrator's own account: actions on it are refused by the server
// (no self-reset, no self-disable, no self-demotion), so they are not offered.
let myAccountId = null;

async function loadAccounts() {
  if (myAccountId === null) {
    const me = await fetch("/api/v1/me").then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
    myAccountId = me.account_id || "";
  }
  const data = await getJson("/api/v1/admin/accounts", accountsEl);
  if (!data) return;
  accounts = data;
  window.clearBusy(accountsEl);
  renderAccounts();
  paintPreview();
}

async function postJson(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (window.redirectToLoginIfExpired(r)) return null;
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    window.toast(typeof d.detail === "string" ? d.detail : "Thao tác không thành công.", "error", { sticky: true });
    return null;
  }
  return d;
}

// ---- slips

function slipHtml(x) {
  const origin = `${location.origin}/login`;
  return `<article class="slip">
    <p class="slip-brand">SpeakUp · Phiếu tài khoản · ${escapeHtml(ROLE_NAMES[x.role] || x.role)}</p>
    <div class="slip-codes">
      <div><span class="slip-label">Mã đăng nhập</span><span class="slip-code">${escapeHtml(x.pseudonym)}</span></div>
      <div><span class="slip-label">Mật khẩu tạm</span><span class="slip-code">${escapeHtml(x.temporary_password)}</span></div>
    </div>
    <p class="slip-note">Đăng nhập tại <b>${escapeHtml(origin)}</b>. Lần đầu, hệ thống yêu cầu đặt
      mật khẩu của riêng bạn; từ đó mật khẩu tạm hết hiệu lực.</p>
    <p class="slip-name">Sau đó thêm email và họ tên ở trang Tài khoản để đăng nhập bằng email.</p>
  </article>`;
}

function paintSlips() {
  slipsEl.hidden = !slips.length;
  slipGrid.innerHTML = slips.map(slipHtml).join("");
}

function addSlips(rows, role) {
  rows.forEach((x) => slips.push({ ...x, role: x.role || role }));
  paintSlips();
  slipsEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

document.getElementById("slips-print").addEventListener("click", () => {
  document.body.classList.add("printing-slips");
  window.print();
});
window.addEventListener("afterprint", () => document.body.classList.remove("printing-slips"));

// A CSV for a mail merge or a spreadsheet. The byte-order mark makes Excel read
// it as UTF-8, so Vietnamese headers survive.
document.getElementById("slips-csv").addEventListener("click", () => {
  const cell = (v) => `"${String(v).replace(/"/g, '""')}"`;
  const lines = [["but_danh", "vai_tro", "mat_khau_tam", "dia_chi_dang_nhap"].join(",")];
  slips.forEach((x) =>
    lines.push([x.pseudonym, x.role, x.temporary_password, `${location.origin}/login`].map(cell).join(","))
  );
  const blob = new Blob(["\ufeff" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "phieu-tai-khoan.csv";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
});

document.getElementById("slips-close").addEventListener("click", () => {
  if (!window.confirm("Ẩn phiếu? Mật khẩu tạm sẽ không xem lại được nữa.")) return;
  slips = [];
  paintSlips();
});

// Leaving the page with slips on screen loses the passwords for good.
window.addEventListener("beforeunload", (e) => {
  if (!slips.length) return;
  e.preventDefault();
  e.returnValue = "";
});

accForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const role = accRole.value;
  const body = { role };
  if (accMode.value === "one") {
    body.pseudonym = accPseudonym.value.trim();
    if (!body.pseudonym) {
      window.toast("Hãy nhập mã tài khoản.", "error");
      accPseudonym.focus();
      return;
    }
  } else {
    body.count = Math.min(200, Math.max(1, Number(accCount.value) || 1));
    body.prefix = (accPrefix.value.trim() || DEFAULT_PREFIX[role]).toUpperCase();
  }
  const button = document.getElementById("acc-create");
  button.disabled = true;
  try {
    const d = await postJson("/api/v1/admin/accounts", body);
    if (!d) return;
    window.toast(`Đã tạo ${d.created.length} tài khoản. Hãy in hoặc tải phiếu trước khi rời trang.`, "ok");
    addSlips(d.created, d.role);
    accPseudonym.value = "";
    loadAccounts();
  } finally {
    button.disabled = false;
  }
});

const ACCOUNT_ACTIONS = {
  revoke: {
    ask: (a) => "Đăng xuất " + nameOf(a) + " khỏi mọi thiết bị? Mật khẩu giữ nguyên.",
    url: (a) => `/api/v1/admin/accounts/${encodeURIComponent(a.account_id)}/revoke-sessions`,
    done: (a, d) => window.toast("Đã đăng xuất " + nameOf(a) + " khỏi " + d.revoked + " phiên.", "ok"),
  },
  unlinkGoogle: {
    ask: (a) => "Gỡ liên kết Google của " + nameOf(a) + "? Họ vẫn đăng nhập được bằng mật khẩu.",
    url: (a) => `/api/v1/admin/accounts/${encodeURIComponent(a.account_id)}/unlink-google`,
    done: (a) => window.toast("Đã gỡ liên kết Google của " + nameOf(a) + ".", "ok"),
  },
  reset: {
    // Plain strings for confirm() and toast(), which never parse HTML; joined
    // rather than templated so the escaping check sees no unescaped markup.
    ask: (a) => "Cấp mật khẩu tạm mới cho " + nameOf(a) + "? Mọi phiên đăng nhập của tài khoản này sẽ kết thúc.",
    url: (a) => `/api/v1/admin/accounts/${encodeURIComponent(a.account_id)}/reset-password`,
    done: (a, d) => {
      addSlips([d], a.role);
      window.toast("Đã cấp mật khẩu tạm mới cho " + nameOf(a) + ".", "ok");
    },
  },
  disable: {
    ask: (a) => "Tắt tài khoản " + nameOf(a) + "? Người dùng bị đăng xuất ngay; dữ liệu vẫn giữ nguyên.",
    url: (a) => `/api/v1/admin/accounts/${encodeURIComponent(a.account_id)}/disable`,
    done: (a) => window.toast("Đã tắt " + nameOf(a) + ".", "ok"),
  },
  enable: {
    ask: null,
    url: (a) => `/api/v1/admin/accounts/${encodeURIComponent(a.account_id)}/enable`,
    done: (a) => window.toast("Đã bật lại " + nameOf(a) + ".", "ok"),
  },
  unlock: {
    ask: null,
    url: (a) => `/api/v1/admin/accounts/${encodeURIComponent(a.account_id)}/unlock`,
    done: (a) => window.toast("Đã gỡ khoá " + nameOf(a) + ".", "ok"),
  },
};

async function runAccountAction(button) {
  const a = accounts.find((x) => x.account_id === button.dataset.account);
  const action = ACCOUNT_ACTIONS[button.dataset.accountAction];
  if (!a || !action) return;
  if (action.ask && !window.confirm(action.ask(a))) return;
  button.disabled = true;
  const d = await postJson(action.url(a));
  button.disabled = false;
  if (!d) return;
  action.done(a, d);
  await loadAccounts();
  if (!accountDialog.open) return;
  // A new one-time password lands on a slip under the dialog: close it so the
  // slip is in view. Anything else refreshes the dialog in place.
  if (button.dataset.accountAction === "reset") accountDialog.close();
  else openAccount(a.account_id);
}

accountsEl.addEventListener("click", (e) => {
  const open = e.target.closest("[data-account-open]");
  if (open) {
    openAccount(open.dataset.accountOpen);
    return;
  }
  const button = e.target.closest("[data-account-action]");
  if (button) runAccountAction(button);
});

// ---- one account in detail (D029)

const accountDialog = document.getElementById("account-dialog");
const accountDialogBody = document.getElementById("account-dialog-body");
const ACTIVITY_NAMES = {
  "auth.login": "Đăng nhập",
  "auth.login_failed": "Đăng nhập sai",
  "account.create": "Tạo tài khoản",
  "account.password_change": "Đổi mật khẩu",
  "account.reset_password": "Cấp mật khẩu tạm",
  "account.sessions_revoked": "Đăng xuất mọi thiết bị",
  "account.session_revoked": "Đăng xuất một phiên",
  "account.disable": "Tắt tài khoản",
  "account.enable": "Bật tài khoản",
  "account.unlock": "Gỡ khoá",
  "account.role_change": "Đổi vai trò",
  "account.google_link": "Liên kết Google",
  "account.google_unlink": "Gỡ liên kết Google",
  "account.signup": "Tự đăng ký",
  "account.google_signup": "Đăng ký bằng Google",
  // The recovery code (D065) is gone since D081; its past entries stay in the log.
  "account.recovery_code": "Tạo mã khôi phục",
  "account.recover": "Đặt lại mật khẩu bằng mã khôi phục",
  "account.contact": "Đổi họ tên hoặc email",
  "account.google_adopt": "Nối đăng nhập Google theo email",
  "auth.recover_failed": "Thử mã khôi phục sai",
  "account.profile": "Sửa hồ sơ",
};

function detailHtml(d) {
  const self = d.account_id === myAccountId;
  const when = (iso) => (iso ? window.ui.localTime(iso) : "—");
  const fact = (k, v) => `<div><dt>${k}</dt><dd>${escapeHtml(v)}</dd></div>`;
  const roleOptions = Object.keys(ROLE_NAMES)
    .map((r) => `<option value="${r}"${r === d.role ? " selected" : ""}>${ROLE_NAMES[r]}</option>`)
    .join("");
  const actions = self
    ? '<p class="muted">Đây là tài khoản của bạn: đổi mật khẩu, phiên và Google ở trang Tài khoản.</p>'
    : `<div class="button-row">
        ${actionButton("reset", d, "key", "Cấp mật khẩu tạm")}
        ${actionButton("revoke", d, "logout", "Đăng xuất mọi thiết bị")}
        ${d.google_linked ? actionButton("unlinkGoogle", d, "x", "Gỡ liên kết Google") : ""}
        ${d.locked_until ? actionButton("unlock", d, "unlock", "Gỡ khoá") : ""}
        ${d.disabled ? actionButton("enable", d, "check", "Bật lại") : actionButton("disable", d, "power", "Tắt tài khoản", "danger")}
        <a class="button secondary" href="#erase" data-erase="${escapeHtml(d.pseudonym)}">Xoá dữ liệu…</a>
      </div>
      <div class="inline-form role-form">
        <div class="field"><label for="role-select">Vai trò</label><select id="role-select">${roleOptions}</select></div>
        <div class="button-row"><button type="button" class="secondary" id="role-save">Đổi vai trò</button></div>
      </div>
      <div class="inline-form role-form">
        <div class="field"><label for="contact-name">Họ và tên</label><input id="contact-name" maxlength="80" value="${escapeHtml(d.full_name || "")}"></div>
        <div class="field"><label for="contact-email">Email đăng nhập</label><input id="contact-email" type="email" maxlength="254" value="${escapeHtml(d.email || "")}"></div>
        <div class="button-row"><button type="button" class="secondary" id="contact-save">Lưu họ tên và email</button></div>
      </div>`;
  const sessions = d.sessions.length
    ? `<table><thead><tr><th>Thiết bị</th><th>Cách đăng nhập</th><th>Bắt đầu</th><th>Hết hạn</th></tr></thead><tbody>${d.sessions
        .map(
          (x) =>
            `<tr><td>${escapeHtml(x.device || "Không rõ")}</td><td>${escapeHtml(x.method === "google" ? "Google" : "Mật khẩu")}</td>` +
            `<td>${escapeHtml(when(x.created_at))}</td><td>${escapeHtml(when(x.expires_at))}</td></tr>`
        )
        .join("")}</tbody></table>`
    : '<p class="muted">Không có phiên nào đang mở.</p>';
  const activity = d.activity.length
    ? `<ol class="activity-list">${d.activity
        .map(
          (x) =>
            `<li class="activity"><span class="activity-main"><b>${escapeHtml(ACTIVITY_NAMES[x.action] || x.action)}</b>` +
            `<span class="cell-sub">${escapeHtml(x.actor_id)} · ${escapeHtml(when(x.created_at))}` +
            `${x.detail ? " · " + escapeHtml(x.detail) : ""}</span></span></li>`
        )
        .join("")}</ol>`
    : '<p class="muted">Chưa có hoạt động nào.</p>';
  return `<div class="sheet-head">
      <div class="profile-head">${avatarHtml(d)}
        <div><h2 id="account-dialog-h">${escapeHtml(d.full_name || d.pseudonym)}</h2>
        <p class="muted">${escapeHtml(ROLE_NAMES[d.role] || d.role)} · ${accountState(d)} · mã <code>${escapeHtml(d.pseudonym)}</code></p></div></div>
      <button type="button" class="secondary icon-only" id="account-dialog-close" aria-label="Đóng">${window.ui.icon("x")}</button>
    </div>
    <dl class="facts">
      ${fact("Email", d.email ? d.email + (d.email_verified ? " (Google đã xác minh)" : "") : "Chưa có")}
      ${fact("Tạo lúc", when(d.created_at))}
      ${fact("Đăng nhập gần nhất", when(d.last_login_at))}
      ${fact("Đổi mật khẩu gần nhất", when(d.password_changed_at))}
      ${fact("Liên kết Google", d.google_linked ? "từ " + when(d.google_linked_at) : "Chưa")}
      ${fact("Lần đăng nhập sai liên tiếp", String(d.failed_attempts))}
    </dl>
    ${actions}
    <h3>Phiên đang mở</h3>${sessions}
    <h3>Hoạt động gần đây</h3>${activity}`;
}

function actionButton(action, a, icon, label, extra = "") {
  return (
    `<button type="button" class="secondary ${extra}" data-account-action="${action}"` +
    ` data-account="${escapeHtml(a.account_id)}">${window.ui.icon(icon)} ${escapeHtml(label)}</button>`
  );
}

async function openAccount(accountId) {
  const r = await fetch(`/api/v1/admin/accounts/${encodeURIComponent(accountId)}`);
  if (window.redirectToLoginIfExpired(r)) return;
  if (!r.ok) {
    window.toast("Không mở được tài khoản này.", "error");
    return;
  }
  const d = await r.json();
  accountDialogBody.innerHTML = detailHtml(d);
  if (!accountDialog.open) accountDialog.showModal();
}

accountDialogBody.addEventListener("click", async (e) => {
  if (e.target.closest("#account-dialog-close")) {
    accountDialog.close();
    return;
  }
  const erase = e.target.closest("[data-erase]");
  if (erase) {
    // Erasing data is the Data tab's job, with its own preview and double entry.
    accountDialog.close();
    document.getElementById("speaker-id").value = erase.dataset.erase;
    return;
  }
  const button = e.target.closest("[data-account-action]");
  if (button) {
    runAccountAction(button);
    return;
  }
  if (e.target.closest("#contact-save")) {
    const id = accountDialogBody.querySelector("[data-account]").dataset.account;
    const body = {};
    const name = document.getElementById("contact-name").value.trim();
    const email = document.getElementById("contact-email").value.trim();
    if (name) body.full_name = name;
    if (email) body.email = email;
    if (!Object.keys(body).length) return;
    const r = await fetch(`/api/v1/admin/accounts/${encodeURIComponent(id)}/contact`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (window.redirectToLoginIfExpired(r)) return;
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      window.toast(typeof d.detail === "string" ? d.detail : "Chưa lưu được.", "error");
      return;
    }
    window.toast("Đã lưu họ tên và email.", "ok");
    await loadAccounts();
    openAccount(id);
    return;
  }
  if (e.target.closest("#role-save")) {
    const id = accountDialogBody.querySelector("[data-account]").dataset.account;
    const a = accounts.find((x) => x.account_id === id);
    const role = document.getElementById("role-select").value;
    if (!a || role === a.role) return;
    if (!window.confirm("Đổi vai trò của " + nameOf(a) + " thành " + ROLE_NAMES[role] + "?")) return;
    const d = await postJson(`/api/v1/admin/accounts/${encodeURIComponent(id)}/role`, { role });
    if (!d) return;
    window.toast("Đã đổi vai trò của " + nameOf(a) + ".", "ok");
    await loadAccounts();
    openAccount(id);
  }
});

// The list as a spreadsheet: who exists and in what state. No password, no
// hash, nothing that opens an account.
document.getElementById("acc-csv").addEventListener("click", () => {
  const cell = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const head = ["ma_tai_khoan", "email", "ho_ten", "vai_tro", "tao_luc", "dang_nhap_gan_nhat", "da_tat", "cho_doi_mat_khau", "co_google"];
  const lines = [head.join(",")];
  accounts.forEach((a) =>
    lines.push(
      [a.pseudonym, a.email || "", a.full_name || "", a.role, a.created_at, a.last_login_at || "", a.disabled ? 1 : 0, a.must_change_password ? 1 : 0, a.google_linked ? 1 : 0]
        .map(cell)
        .join(",")
    )
  );
  const blob = new Blob(["\ufeff" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "danh-sach-tai-khoan.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
});

// ---------- Tab: models (FR-36) ----------

function numberOrDash(v, digits) {
  return v == null ? "—" : Number(v).toFixed(digits);
}

async function loadModels() {
  const el = document.getElementById("models-body");
  const data = await getJson("/api/v1/admin/models", el);
  if (!data) return;
  const models = Array.isArray(data) ? data : data.models || [];
  if (!models.length) {
    window.clearBusy(el);
    el.innerHTML = '<p class="muted">Chưa có hiện vật mô hình nào.</p>';
    return;
  }

  // Four columns instead of ten, so the action is on screen: what the
  // artifact is, how it was evaluated, its state, and what can be done with it.
  let h = `<h2>Hiện vật mô hình</h2>
    <table class="models-table">
      <thead><tr><th>Mô hình</th><th>Kiểm định chéo</th><th>Trạng thái</th><th>Thao tác</th></tr></thead>
      <tbody>`;

  let hasUnusable = false;
  let hasUncalibrated = false;

  models.forEach((m) => {
    const usable = m.usable !== false;
    if (!usable) hasUnusable = true;
    const calibration = m.calibration_version;
    if (calibration === "chua-hieu-chuan") hasUncalibrated = true;
    const compatible = usable && m.compatible !== false;

    let state = "";
    if (m.active) state += '<span class="badge COMPLETED">Đang chấm</span> ';
    if (!usable) {
      // A broken artifact comes back with only name/usable/error, so the error
      // text is the only thing that says what is actually wrong with it.
      state += '<span class="badge FAILED">Không nạp được</span>';
      if (m.error) state += `<span class="cell-sub">${escapeHtml(m.error)}</span>`;
    } else if (!compatible) {
      state += '<span class="badge REVIEW_REQUIRED">Không tương thích</span>';
      if (m.incompatible_reason) {
        state += `<span class="cell-sub">${escapeHtml(m.incompatible_reason)}</span>`;
      }
    } else if (!m.active) {
      state += '<span class="badge QUEUED">Sẵn sàng</span>';
    }

    // FR-36: an artifact that does not load, or does not fit this system,
    // cannot be activated; the server refuses it too.
    let action = '<span class="muted">—</span>';
    if (m.active) action = '<span class="muted">Đang dùng</span>';
    else if (compatible) {
      action = `<button type="button" class="small" data-activate="${escapeHtml(m.name)}">Kích hoạt</button>`;
    }

    h += `<tr class="${m.active ? "row-active" : usable ? "" : "row-broken"}">
      <td><b>${escapeHtml(m.name ?? m.model_version ?? "—")}</b>
        <span class="cell-sub">Mô hình <code>${escapeHtml(m.model_version ?? "—")}</code> ·
          đặc trưng <code>${escapeHtml(m.feature_version ?? "—")}</code></span>
        <span class="cell-sub">Hiệu chuẩn <code>${escapeHtml(calibration ?? "—")}</code></span></td>
      <td>PCC <b>${numberOrDash(m.cv_pcc, 3)}</b> · RMSE ${numberOrDash(m.cv_rmse, 3)}
        <span class="cell-sub">Đơn vị: ${escapeHtml(m.unit_of_inference ?? "—")} ·
          ${m.train_n == null ? "—" : escapeHtml(m.train_n)} mẫu</span></td>
      <td>${state}</td>
      <td class="action-cell">${action}</td>
    </tr>`;
  });
  h += "</tbody></table>";

  if (hasUncalibrated) {
    h += `<div class="notice">
      <b>Về hiệu chuẩn.</b> Giá trị <code>chua-hieu-chuan</code>
      <b>không phải là tên một phiên bản hiệu chuẩn</b>. Nó có nghĩa là mô hình
      <b>chưa qua hiệu chuẩn xác suất</b>: điểm mô hình trả về chưa được chỉnh
      để phản ánh đúng mức độ chắc chắn, nên không được đọc như một xác suất.
    </div>`;
  }
  if (hasUnusable) {
    h += `<div class="notice notice-danger">
      <b>Có hiện vật không nạp được</b>, thường là do thiếu tệp trọng số hoặc tệp
      hỏng. Những phiên bản này <b>không thể kích hoạt</b>. Cần bổ sung đủ tệp
      hiện vật rồi kiểm tra lại trước khi dùng.
    </div>`;
  }
  // The artifacts on disk are not all trained at the same unit: a whole-exam
  // model reports a much higher PCC than a single-response one simply because a
  // five-minute exam carries more signal. Putting them in one table without
  // this warning invites exactly the comparison the SDD says not to make.
  h += `<div class="notice">
    <b>Đừng so trực tiếp PCC và RMSE giữa các dòng.</b> Hai chỉ số này chỉ so được
    với nhau khi <b>cùng đơn vị suy luận</b>. Mô hình chấm cả bài thi luôn có PCC
    cao hơn mô hình chấm từng bài nói, chỉ vì bài thi dài hơn nên mang nhiều
    thông tin hơn, chứ không phải vì nó tốt hơn cho bài toán này.
  </div>`;
  h += `<p class="muted">Kích hoạt chỉ đổi mô hình chấm các bài nộp từ lúc đó. Báo cáo
    đã lưu giữ nguyên phiên bản mô hình đã chấm chúng, và mỗi lần đổi được ghi
    vào nhật ký kiểm toán.</p>`;
  window.clearBusy(el);
  el.innerHTML = h;
  el.querySelectorAll("[data-activate]").forEach((b) =>
    b.addEventListener("click", () => activate(b.dataset.activate, b))
  );
}

async function activate(name, button) {
  const sure = window.confirm(
    `Kích hoạt mô hình ${name}? Mọi bài nộp từ bây giờ sẽ được chấm bằng mô hình này.`
  );
  if (!sure) return;
  button.disabled = true;
  try {
    const r = await fetch(`/api/v1/admin/models/${encodeURIComponent(name)}/activate`, {
      method: "POST",
    });
    if (window.redirectToLoginIfExpired(r)) return;
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      window.toast(d.detail || "Không kích hoạt được mô hình.", "error", { sticky: true });
      button.disabled = false;
      return;
    }
    // toast() sets textContent, so the server's sentence is shown as text.
    window.toast(["Đã kích hoạt", d.active_model + ".", d.note || ""].join(" "), "ok");
    loadModels();
  } catch (e) {
    window.toast("Không kết nối được máy chủ.", "error");
    button.disabled = false;
  }
}

// ---------- Tab 2: QC configuration (FR-08) ----------

// Vietnamese labels for the keys the API returns. Any key not listed here is
// still shown, under its raw name, rather than dropped: a threshold the
// interface does not recognise is still a threshold in force.
const CONFIG_LABELS = {
  qc_config_version: "Phiên bản bộ ngưỡng",
  changed_by: "Người sửa gần nhất",
  changed_at: "Lúc sửa gần nhất",
  config_version: "Phiên bản cấu hình",
  candidate_thresholds: "Ngưỡng mặc định ban đầu",
  max_bytes: "Kích thước tệp tối đa (byte)",
  target_sr: "Tần số lấy mẫu chuẩn hoá (Hz)",
  reject_below: "Dưới mức này thì từ chối bài",
  review_below: "Dưới mức này thì chuyển giảng viên duyệt",
  review_at: "Từ mức này thì chuyển giảng viên duyệt",
  reject_above: "Trên mức này thì từ chối bài",
};

function formatConfigValue(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "có" : "không";
  return escapeHtml(v);
}

function configRow(key, value, groupLabel) {
  const what = groupLabel ? `${groupLabel} · ${CONFIG_LABELS[key] || key}` : CONFIG_LABELS[key] || key;
  return `<tr><td>${escapeHtml(what)}</td>
    <td><b>${formatConfigValue(value)}</b></td>
    <td><code>${escapeHtml(key)}</code></td></tr>`;
}

// Each editable threshold, where its current value sits in the GET payload,
// and how to say it in Vietnamese. The server is the judge of ranges and of
// ordering; this table only lays the form out.
const EDITABLE = [
  ["min_duration_s", "duration_s", "reject_below", "Thời lượng: từ chối nếu ngắn hơn (giây)"],
  ["review_duration_s", "duration_s", "review_below", "Thời lượng: chuyển duyệt nếu ngắn hơn (giây)"],
  ["max_duration_s", "duration_s", "reject_above", "Thời lượng: từ chối nếu dài hơn (giây)"],
  ["review_clipping_ratio", "clipping_ratio", "review_at", "Méo tiếng: chuyển duyệt từ tỷ lệ"],
  ["max_clipping_ratio", "clipping_ratio", "reject_above", "Méo tiếng: từ chối trên tỷ lệ"],
  ["review_silence_ratio", "silence_ratio", "review_at", "Im lặng: chuyển duyệt từ tỷ lệ"],
  ["max_silence_ratio", "silence_ratio", "reject_above", "Im lặng: từ chối trên tỷ lệ"],
  ["min_snr_db", "snr_db", "reject_below", "Nhiễu nền: từ chối nếu SNR dưới (dB)"],
  ["review_snr_db", "snr_db", "review_below", "Nhiễu nền: chuyển duyệt nếu SNR dưới (dB)"],
];

async function loadConfig() {
  const el = document.getElementById("config-body");
  const data = await getJson("/api/v1/admin/config", el);
  if (!data) return;

  // Versions and other scalars, read-only.
  let h = '<h2>Ngưỡng đang áp dụng</h2><table class="kv"><tbody>';
  Object.entries(data).forEach(([k, v]) => {
    if (["editable_here", "editable_fields"].includes(k)) return;
    if (v && typeof v === "object" && !Array.isArray(v)) return;
    if (k === "changed_at" && v) v = window.ui.localTime(v);
    h += configRow(k, v, null);
  });
  h += "</tbody></table>";

  const fields = data.editable_fields || {};
  const rows = EDITABLE.filter(([key]) => fields[key]);
  if (data.editable_here && rows.length) {
    h += '<h2 class="block-title">Sửa ngưỡng</h2>';
    h +=
      '<p class="muted">Mỗi lần lưu tạo một phiên bản ngưỡng mới; báo cáo chấm sau đó ghi ' +
      "phiên bản này. Máy chủ kiểm tra khoảng cho phép và thứ tự giữa các ngưỡng.</p>";
    h += '<form id="config-form" class="config-grid">';
    rows.forEach(([key, group, sub, label]) => {
      const now = (data[group] || {})[sub];
      const range = fields[key];
      const step = range.max <= 1 ? "0.01" : "0.5";
      h +=
        `<label for="cfg-${key}">${escapeHtml(label)}` +
        `<span class="cell-sub">Cho phép ${escapeHtml(range.min)} – ${escapeHtml(range.max)} · <code>${escapeHtml(key)}</code></span></label>` +
        `<input id="cfg-${key}" name="${key}" type="number" step="${step}"` +
        ` min="${escapeHtml(range.min)}" max="${escapeHtml(range.max)}" value="${escapeHtml(now ?? "")}"` +
        ` data-current="${escapeHtml(now ?? "")}">`;
    });
    h +=
      '<div class="button-row config-actions"><button type="submit">Lưu ngưỡng mới</button>' +
      '<button type="reset" class="secondary">Hoàn tác thay đổi</button></div>';
    h += '<div id="config-message" aria-live="polite"></div></form>';
  }
  window.clearBusy(el);
  el.innerHTML = h;
  const form = document.getElementById("config-form");
  if (form) form.addEventListener("submit", saveConfig);
  loadGoogleSetup();
}

// D036. Sign-in with Google: on or off, the redirect address to register with
// Google, and what is still missing. The client secret is never sent here.
let googleSetupWired = false;
async function loadGoogleSetup() {
  const box = document.getElementById("google-setup");
  const g = await getJson("/api/v1/admin/google", null);
  if (!box || !g) return;
  const state = g.enabled
    ? '<span class="badge COMPLETED">Đang bật</span>'
    : '<span class="badge QUEUED">Chưa bật</span>';
  const problems = g.problems.length
    ? `<div class="notice notice-warn"><b>Cần xem lại</b><ul class="bill-problems">${g.problems
        .map((p) => `<li>${escapeHtml(p)}</li>`)
        .join("")}</ul></div>`
    : "";
  const row = (label, value) => `<tr><th scope="row">${label}</th><td>${value}</td></tr>`;
  box.innerHTML =
    `<div class="card-head"><h2 id="google-setup-h">Đăng nhập bằng Google</h2>${state}</div>` +
    '<p class="muted">OAuth 2.0, luồng mã uỷ quyền với PKCE (S256), state và nonce. Hệ thống chỉ giữ mã băm một chiều của tài khoản Google, không giữ email hay tên.</p>' +
    problems +
    '<table class="kv google-kv"><tbody>' +
    row(
      "Địa chỉ chuyển hướng cần đăng ký",
      `<code>${escapeHtml(g.redirect_uri)}</code> <button type="button" class="secondary small" data-copy="${escapeHtml(g.redirect_uri)}">Sao chép</button>` +
        (g.redirect_from_public_url ? "" : '<span class="cell-sub">Lấy theo địa chỉ đang mở trang này; đặt AICEFR_PUBLIC_URL để cố định.</span>')
    ) +
    row("Client ID", g.client_id ? `<code>${escapeHtml(g.client_id)}</code>` : "Chưa đặt") +
    row("Client secret", g.secret_set ? "Đã đặt (không bao giờ hiển thị)" : "Chưa đặt") +
    row("Phạm vi xin", `<code>${escapeHtml(g.scopes)}</code>`) +
    row("Chỉ nhận tài khoản thuộc", g.allowed_domain ? escapeHtml(g.allowed_domain) : "Mọi tài khoản Google") +
    row("Cookie của luồng", `<code>${escapeHtml(g.flow_cookie)}</code>, có chữ ký`) +
    row("Tài khoản đã liên kết", String(Number(g.linked_accounts))) +
    "</tbody></table>" +
    '<p class="muted">Cách tạo OAuth client trong Google Cloud Console và nơi đặt khoá: <code>docs/plan/CAU_HINH_KHOA_BEN_NGOAI.md</code>.</p>';
  box.hidden = false;
  if (!googleSetupWired) {
    googleSetupWired = true;
    box.addEventListener("click", copyText);
  }
}

// A button marked data-copy puts that text on the clipboard. The clipboard
// needs https or localhost; elsewhere the person is told to copy it by hand.
async function copyText(e) {
  const button = e.target.closest("[data-copy]");
  if (!button) return;
  try {
    await navigator.clipboard.writeText(button.dataset.copy);
    window.toast("Đã sao chép.", "ok");
  } catch {
    window.toast("Không sao chép tự động được; hãy chọn dòng chữ và sao chép tay.", "error");
  }
}

async function saveConfig(e) {
  e.preventDefault();
  const form = e.target;
  const message = document.getElementById("config-message");
  // Only what changed goes to the server, so the audit line names exactly the
  // thresholds this administrator moved.
  const changes = {};
  form.querySelectorAll("input[name]").forEach((input) => {
    if (input.value !== "" && input.value !== input.dataset.current) {
      changes[input.name] = Number(input.value);
    }
  });
  if (!Object.keys(changes).length) {
    message.innerHTML = '<p class="muted">Chưa có ngưỡng nào thay đổi.</p>';
    return;
  }
  const list = Object.entries(changes)
    .map(([k, v]) => `${k} = ${v}`)
    .join(", ");
  if (!window.confirm(`Lưu ngưỡng mới (${list})? Bài nộp từ bây giờ sẽ được kiểm tra theo ngưỡng này.`)) {
    return;
  }
  const r = await fetch("/api/v1/admin/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(changes),
  });
  if (window.redirectToLoginIfExpired(r)) return;
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    const detail = typeof d.detail === "string" ? d.detail : "Không lưu được ngưỡng.";
    message.innerHTML = `<p class="error">${escapeHtml(detail)}</p>`;
    return;
  }
  window.toast(`Đã lưu ngưỡng, phiên bản ${d.qc_config_version}.`, "ok");
  loadConfig();
}

// ---------- Tab 3: personal data erasure (FR-34, FR-35) ----------

const speakerInput = document.getElementById("speaker-id");
const speakerInputAgain = document.getElementById("speaker-id-again");
const previewBody = document.getElementById("preview-body");
const confirmBody = document.getElementById("confirm-body");
const eraseButton = document.getElementById("erase-button");
const eraseMessage = document.getElementById("erase-message");

// The pseudonym the preview was run for. The delete call uses this, not the
// live input, so editing the first field after a preview cannot delete someone
// else's data.
let previewedSpeakerId = null;

function resetErasePanel() {
  previewedSpeakerId = null;
  previewBody.innerHTML = "";
  confirmBody.hidden = true;
  speakerInputAgain.value = "";
  eraseButton.disabled = true;
  eraseMessage.innerHTML = "";
}

document.getElementById("preview-button").addEventListener("click", async () => {
  const speakerId = speakerInput.value.trim();
  resetErasePanel();
  if (!speakerId) {
    previewBody.innerHTML = '<p class="error">Hãy nhập mã tài khoản.</p>';
    return;
  }
  const data = await getJson(
    `/api/v1/admin/erase/${encodeURIComponent(speakerId)}`,
    previewBody
  );
  if (!data) return;

  const ids = data.response_ids || [];
  let h = `<h2>Sẽ xoá những gì</h2>
    <table>
      <tr><th>Mục</th><th>Số lượng</th></tr>
      <tr><td>Bài nói</td><td><b>${escapeHtml(data.responses ?? 0)}</b></td></tr>
      <tr><td>Tệp ghi âm trên ổ đĩa</td><td><b>${escapeHtml(data.audio_files ?? 0)}</b></td></tr>
      <tr><td>Lần duyệt của giảng viên</td><td><b>${escapeHtml(
        data.review_actions ?? 0
      )}</b></td></tr>
    </table>`;
  h += ids.length
    ? `<p>Mã các bài sẽ bị xoá:</p><p><code>${ids.map(escapeHtml).join("</code> <code>")}</code></p>`
    : '<p class="muted">Không có bài nào thuộc mã tài khoản này.</p>';
  h += `<div class="notice notice-danger">Bấm xác nhận là xoá ngay và
    <b>không hoàn tác được</b>.</div>`;
  previewBody.innerHTML = h;

  previewedSpeakerId = data.speaker_id ?? speakerId;
  confirmBody.hidden = false;
});

// The confirm button only wakes up when the second field matches the pseudonym
// the preview was actually run for.
speakerInputAgain.addEventListener("input", () => {
  eraseButton.disabled =
    previewedSpeakerId === null || speakerInputAgain.value.trim() !== previewedSpeakerId;
});

eraseButton.addEventListener("click", async () => {
  if (previewedSpeakerId === null) return;
  eraseButton.disabled = true;
  eraseMessage.innerHTML = '<p class="muted">Đang xoá…</p>';

  let r;
  try {
    r = await fetch("/api/v1/admin/erase", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        speaker_id: previewedSpeakerId,
        confirm_speaker_id: speakerInputAgain.value.trim(),
      }),
    });
  } catch (e) {
    eraseMessage.innerHTML = '<p class="error">Không kết nối được máy chủ. Chưa xoá gì cả.</p>';
    window.toast("Không kết nối được máy chủ. Chưa xoá gì cả.", "error");
    eraseButton.disabled = false;
    return;
  }
  if (window.redirectToLoginIfExpired(r)) return;
  if (!r.ok) {
    eraseMessage.innerHTML = permissionMessage(r.status);
    eraseButton.disabled = false;
    return;
  }
  const data = await r.json();

  // AC-35.4: erasure removes the stored data, but it cannot pull that data back
  // out of models that were already trained and released. Saying so is part of
  // the requirement, not an optional footnote.
  const cutoffNote =
    data.cutoff_note ||
    "Dữ liệu đã dùng huấn luyện các mô hình phát hành trước đó không bị gỡ khỏi mô hình.";
  window.toast("Đã xoá dữ liệu cá nhân của người học.", "ok", { sticky: true });
  eraseMessage.innerHTML = `
    <p class="success">Đã xoá dữ liệu của <code>${escapeHtml(previewedSpeakerId)}</code>:
      ${escapeHtml(data.responses ?? 0)} bài nói,
      ${escapeHtml(data.audio_files ?? 0)} tệp ghi âm,
      ${escapeHtml(data.review_actions ?? 0)} lần duyệt.</p>
    <div class="notice notice-danger"><b>Lưu ý về phạm vi xoá.</b>
      ${escapeHtml(cutoffNote)}</div>`;
  previewedSpeakerId = null;
  previewBody.innerHTML = "";
  confirmBody.hidden = true;
  speakerInput.value = "";
  speakerInputAgain.value = "";
});

// ---------- Tab 4: operations (NFR-11) ----------

async function loadOps() {
  await loadHealth();
  await loadStats();
  await loadAudit();
}

function yesNo(v) {
  return v ? '<span class="badge COMPLETED">có</span>' : '<span class="badge FAILED">không</span>';
}

async function loadHealth() {
  const el = document.getElementById("health-body");
  const d = await getJson("/api/v1/health", el);
  if (!d) return;

  let h = `<h2>Tình trạng hệ thống</h2>
    <table>
      <tr><th>Mục</th><th>Giá trị</th></tr>
      <tr><td>Trạng thái</td><td>${escapeHtml(d.status)}</td></tr>
      <tr><td>Engine nhận dạng tiếng nói</td><td><code>${escapeHtml(
        d.asr_engine
      )}</code></td></tr>
      <tr><td>Engine ASR là engine thật</td><td>${yesNo(d.asr_is_real)}</td></tr>
      <tr><td>Cho phép ghi âm ngay trên trình duyệt</td><td>${yesNo(
        d.recording_enabled
      )}</td></tr>
      <tr><td>Phiên bản mô hình</td><td><code>${escapeHtml(d.model_version)}</code></td></tr>
      <tr><td>Phiên bản cấu hình</td><td><code>${escapeHtml(d.config_version)}</code></td></tr>
      <tr><td>Đơn vị suy luận</td><td>${escapeHtml(d.unit_of_inference)}</td></tr>
      <tr><td>PCC (kiểm định chéo)</td><td>${numberOrDash(d.cv_pcc, 4)}</td></tr>
    </table>`;
  if (d.asr_is_real === false) {
    h += `<div class="notice notice-danger">Hệ thống đang chạy engine ASR <b>giả lập</b>.
      Kết quả chấm chỉ dùng để thử giao diện, <b>không dùng để đánh giá người học</b>.</div>`;
  }
  if (d.recording_enabled === false) {
    h += `<div class="notice">Không tìm thấy ffmpeg trên máy chủ, nên nút ghi âm bị ẩn ở
      màn hình nộp bài. Người học vẫn tải tệp lên được.</div>`;
  }
  window.clearBusy(el);
  el.innerHTML = h;
}

async function loadStats() {
  const el = document.getElementById("stats-body");
  const d = await getJson("/api/v1/stats", el);
  if (!d) return;

  const byStatus = Object.entries(d.by_status || {});
  const byBand = Object.entries(d.by_band || {});
  let h = `<h2>Thống kê tổng quan</h2>
    <table>
      <tr><th>Mục</th><th>Số lượng</th></tr>
      <tr><td>Tổng số bài nộp</td><td><b>${escapeHtml(d.total ?? 0)}</b></td></tr>
      <tr><td>Bài đã được giảng viên duyệt</td><td><b>${escapeHtml(
        d.teacher_verified ?? 0
      )}</b></td></tr>
    </table>`;

  h += "<h2>Theo trạng thái xử lý</h2>";
  h += byStatus.length
    ? "<table><tr><th>Trạng thái</th><th>Số lượng</th></tr>" +
      byStatus
        .map(
          ([k, v]) =>
            `<tr><td>${window.ui.statusBadge(k)}</td><td>${escapeHtml(v)}</td></tr>`
        )
        .join("") +
      "</table>"
    : '<p class="muted">Chưa có bài nào.</p>';

  h += "<h2>Theo band CEFR</h2>";
  h += byBand.length
    ? "<table><tr><th>Band</th><th>Số lượng</th></tr>" +
      byBand
        .map(([k, v]) => `<tr><td><b>${escapeHtml(k)}</b></td><td>${escapeHtml(v)}</td></tr>`)
        .join("") +
      "</table>"
    : '<p class="muted">Chưa có bài nào được chấm xong.</p>';
  window.clearBusy(el);
  el.innerHTML = h;
}

async function loadAudit() {
  const el = document.getElementById("audit-body");
  const rows = await getJson("/api/v1/audit", el);
  if (!rows) return;
  if (!rows.length) {
    window.clearBusy(el);
    el.innerHTML = '<h2>Nhật ký kiểm toán</h2><p class="muted">Chưa có bản ghi nào.</p>';
    return;
  }
  let h = `<h2>Nhật ký kiểm toán gần đây</h2>
    <table><tr><th>Thời gian</th><th>Người thực hiện</th><th>Hành động</th>
    <th>Đối tượng</th><th>Lý do / chi tiết</th></tr>`;
  rows.forEach((x) => {
    h += `<tr>
      <td class="muted">${escapeHtml(window.ui.localTime(x.created_at))}</td>
      <td>${escapeHtml(x.actor_id)}</td>
      <td><code>${escapeHtml(x.action)}</code></td>
      <td>${escapeHtml(x.target_id ?? "—")}</td>
      <td>${escapeHtml(x.detail ?? "—")}</td>
    </tr>`;
  });
  window.clearBusy(el);
  el.innerHTML = h + "</table>";
}

// Open the tab named in the URL, or the first one; follow the back button too.
const tabFromHash = () => TABS.find((t) => `#${tabKey(t)}` === location.hash) || TABS[0];
window.addEventListener("hashchange", () => showTab(tabFromHash()));
showTab(tabFromHash());
