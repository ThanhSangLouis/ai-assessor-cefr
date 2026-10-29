// Terms of use (FR-01, D058). One acceptance, kept with its first date: the
// server stores nothing of a learner's voice before it.

const form = document.getElementById("form");
const acceptEl = document.getElementById("accept");
const msgEl = document.getElementById("msg");
const stateEl = document.getElementById("state");
const nextEl = document.getElementById("next-links");

function render(state) {
  if (!state) return;
  stateEl.textContent = state.accepted
    ? `Đã đồng ý lúc ${window.ui.localTime(state.accepted_at)}`
    : "Chưa đồng ý";
  acceptEl.disabled = !!state.accepted;
  nextEl.hidden = !state.accepted;
}

// The page renders for anyone, but the form only for a signed-in user.
if (form) {
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    // Disabled while the request is in flight: a second click must not
    // send a second acceptance.
    acceptEl.disabled = true;
    try {
      const r = await fetch("/api/v1/me/terms", { method: "POST" });
      if (window.redirectToLoginIfExpired(r)) return;
      if (!r.ok) throw new Error(String(r.status));
      render(await r.json());
      msgEl.className = "muted";
      msgEl.textContent = "Đã ghi nhận. Bạn có thể luyện tập và nộp bài ngay.";
    } catch (e) {
      acceptEl.disabled = false;
      msgEl.className = "error";
      msgEl.textContent = "Ghi nhận thất bại, thử lại sau ít phút.";
    }
  });

  fetch("/api/v1/me/terms")
    .then((r) => (r.ok ? r.json() : null))
    .then(render)
    .catch(() => {});
}
