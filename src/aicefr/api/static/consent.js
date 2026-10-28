// Consent screen. See FR-01 and FR-35, and docs/plan/KE_HOACH_KHAO_SAT.md phụ lục A.
//
// The two checkboxes are never merged into one button: the record of what a
// participant agreed to has to distinguish "you may keep my recording" from
// "you may use it in the study".

const form = document.getElementById("form");
const audioEl = document.getElementById("audio");
const researchEl = document.getElementById("research");
const signEl = document.getElementById("sign");
const withdrawEl = document.getElementById("withdraw");
const msgEl = document.getElementById("msg");
const stateEl = document.getElementById("state");
const nextEl = document.getElementById("next-links");

function show(text, kind) {
  msgEl.textContent = text;
  msgEl.className = kind === "error" ? "error" : "muted";
}

function render(state) {
  if (!state) return;
  audioEl.checked = !!state.audio_storage_allowed;
  researchEl.checked = !!state.research_use_allowed;
  if (state.signed) {
    stateEl.textContent = state.may_submit
      ? "Đã ký · nộp bài được"
      : "Đã ký nhưng chưa cho phép lưu bản ghi";
  } else {
    stateEl.textContent = "Chưa ký";
  }
  withdrawEl.disabled = !state.signed;
}

async function load() {
  try {
    const r = await fetch("/api/v1/me/consent");
    if (r.ok) render(await r.json());
  } catch (e) {
    show("Không đọc được trạng thái đồng thuận.", "error");
  }
}

// Both buttons stay disabled while a request is in flight: a second click on
// "Ký" must not record a second signature.
async function send(url, body) {
  signEl.disabled = true;
  withdrawEl.disabled = true;
  try {
    const r = await fetch(url, body ? { method: "POST", body } : { method: "POST" });
    if (window.redirectToLoginIfExpired(r)) return null;
    return r.ok ? await r.json() : null;
  } catch (e) {
    return null;
  } finally {
    signEl.disabled = false;
  }
}

// The page renders for anyone, but the form only for a signed-in student.
if (form) {
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const state = await send(
      "/api/v1/me/consent",
      new URLSearchParams({
        audio_storage_allowed: audioEl.checked ? "true" : "false",
        research_use_allowed: researchEl.checked ? "true" : "false",
      })
    );
    if (!state) {
      show("Ghi nhận đồng thuận thất bại.", "error");
      load();
      return;
    }
    render(state);
    nextEl.hidden = !state.may_submit;
    show(
      state.may_submit
        ? "Đã ghi nhận. Bạn có thể luyện tập và nộp bài ngay."
        : "Đã ghi nhận. Bạn chưa cho phép lưu bản ghi nên chưa nộp bài được."
    );
  });

  withdrawEl.addEventListener("click", async () => {
    const sure = window.confirm(
      "Rút lại đồng thuận? Sau đó hệ thống không nhận bài nói mới của bạn cho tới khi bạn ký lại."
    );
    if (!sure) return;
    const state = await send("/api/v1/me/consent/withdraw");
    if (!state) {
      show("Rút đồng thuận thất bại.", "error");
      load();
      return;
    }
    render(state);
    nextEl.hidden = true;
    show("Đã rút đồng thuận. Kết quả cũ vẫn xem được cho tới khi hết hạn lưu trữ.");
  });

  load();
}
