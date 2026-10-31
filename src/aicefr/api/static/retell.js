// Say the same task again, three times, shorter each time (D069).
// Round 1 is the baseline; rounds 2 and 3 are compared with it on pace and
// pauses (the server's compare_rounds), and the three are listed side by side.
const root = document.getElementById("retell");
const RID = root.dataset.responseId;
const escapeHtml = window.escapeHtml;
const promptEl = document.getElementById("retell-prompt");
const roundsEl = document.getElementById("retell-rounds");
const roundNoEl = document.getElementById("retell-round-no");
const roundMaxEl = document.getElementById("retell-round-max");
const resultsEl = document.getElementById("retell-results");
const resultsBody = document.getElementById("retell-results-body");
const waitEl = document.getElementById("retell-wait");
const form = document.getElementById("retell-form");

let limits = [60, 45, 30];
let done = [];

const nextRound = () => Math.min(done.length + 1, limits.length);
const finished = () => done.length >= limits.length;

const recorder = window.setUpRecorder({
  minSeconds: () => 0,
  maxSeconds: () => limits[nextRound() - 1],
  onSubmit: submit,
});

function signalLine(s) {
  if (s.text) return escapeHtml(s.text);
  const value = s.value === null || s.value === undefined ? "—" : `${Math.round(s.value * 10) / 10}${s.unit ? " " + s.unit : ""}`;
  return `${escapeHtml(s.label)}: <b>${escapeHtml(value)}</b>`;
}

function roundCard(a) {
  const r = a.result;
  const signals = (r.signals || []).slice(0, 4).map((s) => `<li>${signalLine(s)}</li>`).join("");
  const changes = (r.changes || []).map((c) => `<li>${escapeHtml(c)}</li>`).join("");
  return (
    `<article class="retell-round"><h3>Lượt ${a.round} <span class="muted">(${limits[a.round - 1]} giây)</span></h3>` +
    (r.measured === false
      ? `<p class="error">${escapeHtml(r.tip || "Bản ghi chưa dùng được, hãy nói lại lượt này.")}</p>`
      : (signals ? `<ul class="plain-list">${signals}</ul>` : "") +
        (changes ? `<p class="retell-delta"><b>So với lượt đầu:</b></p><ul class="plain-list">${changes}</ul>` : "")) +
    `<audio controls preload="none" src="${escapeHtml(a.audio_url)}"></audio></article>`
  );
}

function paint() {
  roundsEl.innerHTML = limits
    .map((s, i) => {
      const state = i < done.length ? "is-done" : i === done.length ? "is-current" : "";
      return `<li class="${state}">Lượt ${i + 1}: ${s} giây</li>`;
    })
    .join("");
  if (finished()) {
    form.hidden = true;
  } else {
    roundNoEl.textContent = String(nextRound());
    roundMaxEl.textContent = String(limits[nextRound() - 1]);
    recorder.repaint && recorder.repaint();
  }
  resultsEl.hidden = !done.length;
  resultsBody.innerHTML =
    done.map(roundCard).join("") +
    (finished()
      ? '<div class="button-row"><a class="button" href="/">Nộp bài đánh giá mới</a>' +
        '<a class="button secondary" href="/practice">Về lộ trình</a></div>'
      : "");
}

async function submit(audio, name) {
  const body = new FormData();
  body.append("audio", audio, name);
  body.append("round", String(nextRound()));
  waitEl.textContent = "Đang đo lượt này…";
  try {
    const r = await fetch(`/api/v1/learn/retell/${encodeURIComponent(RID)}/rounds`, { method: "POST", body });
    if (window.redirectToLoginIfExpired(r)) return;
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      window.toast(typeof d.detail === "string" ? d.detail : "Không gửi được bản ghi.", "error", { sticky: true });
      return;
    }
    // A round the machine could not use is shown but not counted: say it again.
    if (d.result.measured !== false) done.push({ ...d, round: nextRound() });
    else window.toast(d.result.tip || "Bản ghi chưa dùng được, hãy nói lại lượt này.", "error");
    recorder.reset();
    paint();
  } catch (err) {
    window.toast("Mất kết nối khi gửi. Bản ghi vẫn còn, hãy thử lại.", "error", { sticky: true });
  } finally {
    waitEl.textContent = "";
  }
}

fetch(`/api/v1/learn/retell/${encodeURIComponent(RID)}`)
  .then((r) => (window.redirectToLoginIfExpired(r) ? null : r.ok ? r.json() : Promise.reject(r.status)))
  .then((d) => {
    if (!d) return;
    window.clearBusy(root);
    limits = d.rounds;
    promptEl.textContent = d.prompt;
    done = (d.done || []).filter((a) => a.result.measured !== false).slice(0, limits.length);
    if (d.upgraded) {
      document.getElementById("retell-upgrade").hidden = false;
      window.setUpShadowing(document.getElementById("retell-upgrade-text"), d.upgraded);
    }
    paint();
  })
  .catch(() => {
    window.clearBusy(root);
    root.innerHTML =
      '<div class="card"><div class="empty-state"><h2>Không mở được đề này</h2>' +
      "<p>Chỉ nói lại được bài đánh giá của chính bạn đã có kết quả.</p></div></div>";
  });

fetch("/api/v1/health")
  .then((r) => (r.ok ? r.json() : null))
  .then((h) => recorder.enable(!!(h && h.recording_enabled)))
  .catch(() => recorder.enable(false));
