// Behaviour shared by every page: theme, toasts, table wrapping, session expiry.
//
// Loaded on every screen from base.html. Everything it exports hangs off
// `window` because the other scripts are plain classic scripts (no modules) and
// the Content-Security-Policy is `script-src 'self'`, so nothing may be inlined.

// ---------------------------------------------------------------- escaping
// Every screen needs this; the page scripts all use this one copy.
//
// Quotes too: the result also goes inside attributes (title="…", data-name="…"),
// and the browser's own serialisation leaves " and ' alone, so a lesson title
// with a quote in it could otherwise close the attribute and add its own.
window.escapeHtml = function (t) {
  const d = document.createElement("div");
  d.textContent = t == null ? "" : String(t);
  return d.innerHTML.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
};

// ---------------------------------------------------------------- theme
// Three states: an explicit "light", an explicit "dark", and no choice at all,
// in which case the stylesheet follows prefers-color-scheme. Only an explicit
// choice is stored, so a user who never touches the button keeps following
// their operating system.
const THEME_KEY = "aicefr-theme";

function readStoredTheme() {
  try {
    const v = localStorage.getItem(THEME_KEY);
    return v === "dark" || v === "light" ? v : null;
  } catch (err) {
    // Private windows and locked-down browsers throw on access.
    return null;
  }
}

function systemPrefersDark() {
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function currentTheme() {
  return readStoredTheme() || (systemPrefersDark() ? "dark" : "light");
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  const button = document.getElementById("theme-toggle");
  const label = document.getElementById("theme-toggle-label");
  if (button) button.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
  // The label names what the button DOES, not the state it is in: "Giao diện
  // tối" on a light page means "switch to dark".
  if (label) label.textContent = theme === "dark" ? "Giao diện sáng" : "Giao diện tối";
}

applyTheme(currentTheme());

const themeToggle = document.getElementById("theme-toggle");
if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch (err) {
      /* the choice simply does not survive a reload; the page still switches */
    }
    applyTheme(next);
  });
}

// Follow the system while the user has made no explicit choice.
if (window.matchMedia) {
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (!readStoredTheme()) applyTheme(currentTheme());
  });
}

// ---------------------------------------------------------------- toasts
// Replaces the old habit of injecting a sentence into the middle of the page,
// which pushed the layout around and was easy to miss.
const TOAST_MS = { ok: 4000, info: 5000, warn: 8000, error: 9000 };

window.toast = function (message, kind = "info", options = {}) {
  const region = document.getElementById("toast-region");
  if (!region) return null;

  const el = document.createElement("div");
  el.className = `toast toast-${kind}`;

  const body = document.createElement("div");
  body.className = "toast-body";
  body.textContent = message;
  el.appendChild(body);

  const close = document.createElement("button");
  close.type = "button";
  close.className = "toast-close";
  close.setAttribute("aria-label", "Đóng thông báo");
  close.textContent = "×";
  close.addEventListener("click", () => dismiss());
  el.appendChild(close);

  region.appendChild(el);

  let timer = null;
  function dismiss() {
    if (timer) clearTimeout(timer);
    el.classList.add("leaving");
    setTimeout(() => el.remove(), 300);
  }
  // An error stays until dismissed when asked to: the reader may be away from
  // the screen when it appears.
  if (!options.sticky) timer = setTimeout(dismiss, TOAST_MS[kind] || 5000);
  return dismiss;
};

// ---------------------------------------------------------------- print
// A button marked data-print prints the page (a receipt, D033). The CSP blocks
// inline handlers, so the page says what it wants and this does it.
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-print]")) window.print();
});

// ---------------------------------------------------------------- skeletons
// Markup for a loading placeholder. Returned as a string because every screen
// builds its panels with innerHTML.
window.skeleton = function (kind = "lines") {
  if (kind === "table") {
    return (
      '<div class="skeleton skeleton-title"></div>' +
      '<div class="skeleton skeleton-row"></div>'.repeat(4)
    );
  }
  if (kind === "score") {
    return (
      '<div class="skeleton skeleton-title"></div>' +
      '<div class="skeleton skeleton-block"></div>' +
      '<div class="skeleton skeleton-line"></div>' +
      '<div class="skeleton skeleton-line medium"></div>'
    );
  }
  if (kind === "cards") {
    return '<div class="skeleton skeleton-block"></div>'.repeat(3);
  }
  return (
    '<div class="skeleton skeleton-title"></div>' +
    '<div class="skeleton skeleton-line"></div>' +
    '<div class="skeleton skeleton-line medium"></div>' +
    '<div class="skeleton skeleton-line short"></div>'
  );
};

// Put a skeleton into a container and mark it busy for assistive technology.
window.showSkeleton = function (el, kind) {
  if (!el) return;
  el.setAttribute("aria-busy", "true");
  el.innerHTML = window.skeleton(kind);
};

window.clearBusy = function (el) {
  if (el) el.removeAttribute("aria-busy");
};

// ---------------------------------------------------------------- tables
// Every table on the site is built by a script with innerHTML, in a dozen
// places. Rather than asking each of those to remember a wrapper, wrap them
// here: a wide table then scrolls inside its own box and the page body never
// scrolls sideways.
function wrapTables(root) {
  (root || document).querySelectorAll("table").forEach((table) => {
    if (table.parentElement && table.parentElement.classList.contains("table-scroll")) return;
    const box = document.createElement("div");
    box.className = "table-scroll";
    box.setAttribute("tabindex", "0");
    box.setAttribute("role", "region");
    box.setAttribute("aria-label", "Bảng dữ liệu, cuộn ngang để xem hết");
    table.parentNode.insertBefore(box, table);
    box.appendChild(table);
  });
}
window.wrapTables = wrapTables;

wrapTables(document);
const mainEl = document.getElementById("main");
if (mainEl && "MutationObserver" in window) {
  new MutationObserver(() => wrapTables(mainEl)).observe(mainEl, {
    childList: true,
    subtree: true,
  });
}

// ---------------------------------------------------------------- names
// One Vietnamese name per code, shared by every screen under `window.ui`. Each
// script used to keep its own copy and the copies had drifted ("Bị từ chối" on
// one page, "Bản ghi bị từ chối" on the next).
//
// A namespace rather than loose globals on purpose: these are classic scripts,
// and a page's own top-level `function statusBadge()` would silently replace a
// global of the same name for every other script on the page.
// A block, so these consts do not land in the global lexical scope that every
// classic script on the page shares (a page's own `const STATUS_NAMES` would
// then be a redeclaration error).
{
  const STATUS_NAMES = {
    QUEUED: "Đang chờ xử lý",
    RUNNING: "Đang chấm",
    COMPLETED: "Đã chấm xong",
    REVIEW_REQUIRED: "Chờ giảng viên duyệt",
    REJECTED: "Bản ghi bị từ chối",
    FAILED: "Xử lý thất bại",
  };

  // Reason codes as a teacher reads them in the queue and on the review screen.
  // Every ReasonCode must have a line here (test_web.py checks it): a new code
  // without a name would surface as SCORE_AGGREGATED in the middle of a sentence.
  const REASON_NAMES = {
    SCORE_NEAR_BOUNDARY: "Điểm sát ranh giới band",
    FEATURE_NOT_COMPUTABLE: "Thiếu phép đo",
    OUT_OF_DISTRIBUTION: "Ngoài phân bố huấn luyện",
    TOO_FEW_WORDS: "Quá ít từ",
    ASR_LOW_CONFIDENCE: "Máy nghe không rõ",
    ASR_FAILED: "Nhận dạng thất bại",
    ASR_EMPTY_TRANSCRIPT: "Bản chép rỗng",
    MODEL_VERSION_MISSING: "Thiếu mô hình",
    HIGH_SILENCE_RATIO: "Quá nhiều khoảng lặng",
    CLIPPING_DETECTED: "Âm bị méo",
    LOW_SNR: "Nhiễu nền lớn",
    WRONG_SAMPLE_RATE: "Sai tần số mẫu",
    AUDIO_TOO_SHORT: "Bản ghi quá ngắn",
    AUDIO_TOO_LONG: "Bản ghi quá dài",
    AUDIO_TOO_LARGE: "File quá lớn",
    AUDIO_UNSUPPORTED: "Định dạng không hỗ trợ",
    PROCESSING_INTERRUPTED: "Xử lý bị gián đoạn",
    // Long recordings are scored in windows. Not an error: every long recording
    // carries this code, and they are the ones most worth a teacher's time,
    // because the way window scores are combined has not been validated.
    SCORE_AGGREGATED: "Điểm gộp từ nhiều đoạn",
    ASR_HALLUCINATION: "Máy sinh ra chữ không có trong tiếng",
    ASR_VERSION_MISMATCH: "Khác bộ nhận dạng lúc huấn luyện",
    VAD_VERSION_MISMATCH: "Khác bộ tách tiếng lúc huấn luyện",
    CONSENT_MISSING: "Chưa ký đồng thuận",
    LANGUAGE_NOT_ENGLISH: "Không phải tiếng Anh",
    OFF_TOPIC_SUSPECTED: "Nghi lạc đề",
    PROMPT_COPY_SUSPECTED: "Nghi đọc lại đề bài",
  };

  window.ui = {
    STATUS_NAMES,
    REASON_NAMES,
    // The CEFR qualitative aspects, as the report and the review screen name them.
    CRITERION_NAMES: {
      fluency: "Độ trôi chảy",
      coherence: "Độ mạch lạc",
      range: "Phạm vi ngôn ngữ",
      accuracy: "Độ chính xác",
      phonology: "Phát âm",
    },
    // The same aspects in practice mode (D023, D025), named for a learner, as
    // the server words its suggestions (practice/bank.py CRITERION_NAMES).
    PRACTICE_NAMES: {
      fluency: "Độ trôi chảy",
      coherence: "Mạch lạc",
      range: "Vốn từ",
      accuracy: "Ngữ pháp",
      phonology: "Phát âm dễ nghe",
    },
    // Lessons (D025, D027): the icon and the stage of each kind of step, and
    // the topics a unit can be about. One copy for the learner's path, the
    // lesson screen and the editor; the stages follow lessons/model.py STAGE_OF.
    STEP_ICONS: {
      read_aloud: "book-open",
      repeat: "headphones",
      look_up: "eye-off",
      gap: "puzzle",
      keywords: "key",
      starter: "message",
      picture: "image",
      outline: "list",
      free: "chat",
    },
    STEP_STAGES: {
      read_aloud: "model",
      repeat: "model",
      look_up: "controlled",
      gap: "controlled",
      keywords: "guided",
      starter: "guided",
      picture: "guided",
      outline: "guided",
      free: "free",
    },
    // [name, icon]; names as lessons/model.py TOPIC_NAMES.
    TOPICS: {
      daily_life: ["Đời sống hằng ngày", "house"],
      education: ["Giáo dục", "cap"],
      travel: ["Du lịch", "plane"],
      career: ["Nghề nghiệp", "briefcase"],
      food: ["Ẩm thực", "bowl"],
      health: ["Sức khoẻ", "heart"],
      technology: ["Công nghệ", "chip"],
      environment: ["Môi trường", "leaf"],
      people: ["Con người", "users"],
      society: ["Xã hội", "news"],
    },
    topicOf: (u) => (u.topic && window.ui.TOPICS[u.topic] ? u.topic : "none"),
    practiceName: (c) => (c && window.ui.PRACTICE_NAMES[c]) || "",
    // "2026-10-06" or an ISO time -> "06/10/2026"; `empty` when there is none.
    dmy: (iso, empty = "") => (iso ? String(iso).slice(0, 10).split("-").reverse().join("/") : empty),
    // D039: the pronunciation patterns of Vietnamese learners, as the server names them.
    PRONUNCIATION_NAMES: {
      ed_ending: "Đuôi -ed",
      s_ending: "Đuôi -s, -es",
      final_consonant: "Âm cuối",
      th_sound: "Âm th (/θ/, /ð/)",
      cluster: "Cụm phụ âm đầu",
    },
    // One list for the learner's progress page and the class page: each pattern
    // with its errors against its chances, never a rate before there are enough.
    pronunciationList(d, { lessonLinks = false } = {}) {
      const items = (d.patterns || []).filter((p) => p.opportunities > 0);
      if (!items.length) {
        return '<p class="muted">Chưa có bài đọc to, nhắc lại hay điền từ nào được đo, nên chưa có gì để chẩn đoán.</p>';
      }
      let h = '<ul class="pron-list">';
      for (const p of items) {
        const pct = p.rate == null ? null : Math.round(p.rate * 100);
        const count = p.enough
          ? `<span class="badge${pct >= 30 ? " warn" : ""}">${p.errors}/${p.opportunities} lần · ${pct}%</span>`
          : `<span class="badge muted">Chưa đủ dữ liệu · ${p.opportunities}/${d.min_opportunities} lần gặp</span>`;
        h += `<li class="pron-item"><div class="pron-head"><b>${window.escapeHtml(p.name)}</b>${count}</div>`;
        if (pct != null) {
          h += `<span class="bar low" aria-hidden="true"><span style="width:${Math.min(100, pct)}%"></span></span>`;
        }
        if (p.errors) {
          const ex = p.examples
            .map((e) => {
              const pair = `«${window.escapeHtml(e.word)}» → máy nghe «${window.escapeHtml(e.said)}»`;
              return lessonLinks && e.lesson_id
                ? `<li><a href="/practice/lessons/${encodeURIComponent(e.lesson_id)}">${pair}</a></li>`
                : `<li>${pair}</li>`;
            })
            .join("");
          h += `<ul class="pron-examples" lang="en">${ex}</ul>`;
          h += `<p class="pron-tip">${window.escapeHtml(p.tip)}</p>`;
        }
        h += "</li>";
      }
      h += "</ul>";
      h +=
        '<p class="muted">Máy đọc lỗi qua chữ nó nghe được, nên chỉ đếm thiếu chứ không bịa thêm. ' +
        "Giọng Việt không phải lỗi: chỉ những chỗ làm người nghe khó hiểu mới được tính.</p>";
      return h;
    },
    statusName: (s) => STATUS_NAMES[s] || s,
    statusBadge: (s) =>
      `<span class="badge ${window.escapeHtml(s)}">${window.escapeHtml(STATUS_NAMES[s] || s)}</span>`,
    reasonName: (code) => REASON_NAMES[code] || code,

    // The practice task that trains one aspect at one band, e.g. PR-RAN-B1. Same
    // id scheme as practice/bank.py; bands outside the practice bank (A2 to B2)
    // are clamped to its nearest end.
    practiceTaskFor(criterion, band) {
      const codes = { fluency: "FLU", coherence: "COH", range: "RAN", accuracy: "ACC", phonology: "PHO" };
      if (!codes[criterion]) return null;
      const order = ["A1", "A2", "B1", "B2", "C1", "C2"];
      const i = order.indexOf(band);
      return `PR-${codes[criterion]}-${i < 0 ? "A2" : order[Math.min(3, Math.max(1, i))]}`;
    },

    // "06/10/2026 18:30", the way a Vietnamese reader writes it.
    localTime(iso) {
      const t = new Date(iso);
      if (Number.isNaN(t.getTime())) return iso || "—";
      const p = (n) => String(n).padStart(2, "0");
      return `${p(t.getDate())}/${p(t.getMonth() + 1)}/${t.getFullYear()} ${p(t.getHours())}:${p(t.getMinutes())}`;
    },
    // An icon of the sprite (D027), the same markup as the template macro in
    // _icons.html. Decorative: the text beside it carries the meaning.
    icon(name, cls = "icon") {
      const sprite = (document.body && document.body.dataset.icons) || "/static/icons.svg";
      return (
        `<svg class="${cls}" aria-hidden="true" focusable="false">` +
        `<use href="${sprite}#i-${name}"></use></svg>`
      );
    },
    // A row of 3D blocks on one floor (D031), the same markup as the template
    // macro cube() in _icons.html: the band podium of a report, the class's
    // band columns. Decorative -- the numbers are written elsewhere on the
    // page -- so the row is hidden from screen readers.
    // items: [{ label, sub, cls, h }], h being the block's height in pixels.
    cubes(items, cls = "") {
      const one = (c) =>
        `<span class="cube ${c.cls || ""}" style="--h:${Math.round(c.h)}px">` +
        `<span class="f-front">${window.escapeHtml(c.label)}` +
        (c.sub == null ? "" : `<small>${window.escapeHtml(String(c.sub))}</small>`) +
        '</span><span class="f-side"></span><span class="f-top"></span></span>';
      return (
        `<div class="cube-stage ${cls}" aria-hidden="true">` +
        `<div class="cube-row">${items.map(one).join("")}</div></div>`
      );
    },
    // Seconds as m:ss.
    mmss(seconds) {
      const s = Math.max(0, Math.floor(Number(seconds) || 0));
      return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
    },
  };
}

// ---------------------------------------------------------------- display preferences
// D029. Theme and text size, chosen on the account page and kept in this
// browser only. The theme shares its key with the toggle in the account menu,
// so the two never disagree; "system" is simply no stored choice.
{
  const FONT_KEY = "aicefr-font";
  const read = (key) => {
    try {
      return localStorage.getItem(key);
    } catch (err) {
      return null;
    }
  };
  const write = (key, value) => {
    try {
      if (value === null) localStorage.removeItem(key);
      else localStorage.setItem(key, value);
    } catch (err) {
      /* the choice holds for this page only */
    }
  };
  const applyFont = (value) => {
    if (value === "large") document.documentElement.setAttribute("data-font", "large");
    else document.documentElement.removeAttribute("data-font");
  };
  applyFont(read(FONT_KEY));
  window.ui.prefs = {
    theme: () => readStoredTheme() || "system",
    setTheme(value) {
      write(THEME_KEY, value === "light" || value === "dark" ? value : null);
      applyTheme(currentTheme());
    },
    font: () => (read(FONT_KEY) === "large" ? "large" : "normal"),
    setFont(value) {
      write(FONT_KEY, value === "large" ? "large" : null);
      applyFont(read(FONT_KEY));
    },
  };
}

// ---------------------------------------------------------------- account menu
// A <details> menu stays open until toggled; close it on a click elsewhere and
// on Escape, as a menu is expected to behave.
document.querySelectorAll("details.account-menu").forEach((menu) => {
  document.addEventListener("click", (e) => {
    if (menu.open && !menu.contains(e.target)) menu.open = false;
  });
  menu.addEventListener("keydown", (e) => {
    if (e.key !== "Escape" || !menu.open) return;
    menu.open = false;
    menu.querySelector("summary").focus();
  });
});

// ---------------------------------------------------------------- badges
// How many things wait behind a sidebar item (D028): teacher decisions a
// student has not seen, reviews due today, the review queue, blind ratings. A
// number for the eye and a sentence for a screen reader; nothing at zero.
{
  const BADGE_WORDS = {
    results: "kết quả mới được giảng viên xác nhận",
    reviews_due: "mục ôn tập hôm nay",
    queue: "bài chờ duyệt",
    ratings: "phiếu chấm mù chưa làm",
  };
  const setBadge = (name, count) => {
    document.querySelectorAll(`.nav-badge[data-badge="${name}"]`).forEach((el) => {
      const n = Math.max(0, Number(count) || 0);
      el.hidden = n === 0;
      // Empty at zero, not just hidden: the link's text stays its own label.
      el.innerHTML = n
        ? `<span aria-hidden="true">${n > 99 ? "99+" : n}</span>` +
          `<span class="visually-hidden">, ${n} ${BADGE_WORDS[el.dataset.badge] || "mục mới"}</span>`
        : "";
    });
  };
  window.ui.setBadge = setBadge;
  if (document.querySelector(".nav-badge[data-badge]")) {
    fetch("/api/v1/learn/reviews/due")
      .then((r) => (r.ok ? r.json() : null))
      .then((value) => {
        if (!value || !Array.isArray(value.reviews)) return;
        setBadge("reviews_due", value.reviews.length);
      })
      // A badge is a convenience; a failed count must not disturb the page.
      .catch(() => {});
  }
}

// ---------------------------------------------------------------- session
const logoutLink = document.getElementById("logout-link");
if (logoutLink) {
  logoutLink.addEventListener("click", async (e) => {
    e.preventDefault();
    await fetch("/api/v1/auth/logout", { method: "POST" });
    location.href = "/login";
  });
}

// When an API call returns 401, send the user to the login page together with
// the path to come back to. Returning a raw 401 for an HTML page would leave
// the user staring at JSON.
window.redirectToLoginIfExpired = function (r) {
  if (r.status === 401) {
    location.href = "/login?next=" + encodeURIComponent(location.pathname);
    return true;
  }
  return false;
};

// One API call as the admin tabs make it: the session check, the JSON, and the
// server's reason in a toast that stays until read. Returns the data, or null
// when the call did not succeed (the toast has already said why).
window.apiJson = async function (url, options = {}) {
  const r = await fetch(url, options);
  if (window.redirectToLoginIfExpired(r)) return null;
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    window.toast(typeof d.detail === "string" ? d.detail : "Thao tác không thành công.", "error", {
      sticky: true,
    });
    return null;
  }
  return d;
};
