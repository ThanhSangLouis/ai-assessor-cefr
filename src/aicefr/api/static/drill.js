// Say again the words the machine heard unclearly (D089).
// Four steps per word: the learner's own recording of it, the browser's voice
// reading it slowly, a tip when the spelling gives one, then the phrase said
// again and measured. Clear twice in a row closes a word; a take that is not
// sends the word to spaced review, which the server reports back.
const root = document.getElementById("drill");
const RID = root.dataset.responseId;
const escapeHtml = window.escapeHtml;
const player = document.getElementById("drill-audio");
const listEl = document.getElementById("drill-words");
const stepEl = document.getElementById("drill-step");
const resultEl = document.getElementById("drill-result");
const waitEl = document.getElementById("drill-wait");

let words = [];
let passStreak = 2;
let current = null;

const recorder = window.setUpRecorder({
  minSeconds: () => 0,
  maxSeconds: () => 12,
  onSubmit: submit,
});

// "2026-11-03" -> "03/11/2026"
const dmy = (iso) => iso.split("-").reverse().join("/");
const plain = (t) => t.toLowerCase().replace(/[^a-z']/g, "");

// Play [start, end] of the response's own recording, then stop.
function playSpan(start, end) {
  player.currentTime = start;
  const stop = () => {
    if (player.currentTime >= end) {
      player.pause();
      player.removeEventListener("timeupdate", stop);
    }
  };
  player.addEventListener("timeupdate", stop);
  player.play();
}

function state(w) {
  if (w.passed) return '<span class="badge ok">đã rõ</span>';
  if (w.takes) return `<span class="badge">${w.streak}/${passStreak}</span>`;
  return '<span class="badge">chưa luyện</span>';
}

function paintList() {
  listEl.innerHTML = words
    .map(
      (w) =>
        `<li><button type="button" class="drill-word${w === current ? " is-current" : ""}${w.passed ? " is-done" : ""}"` +
        ` data-word="${escapeHtml(w.word)}" aria-pressed="${w === current}">` +
        `<span lang="en">${escapeHtml(w.word)}</span> ${state(w)}</button></li>`,
    )
    .join("");
}

function phraseHtml(w) {
  return w.phrase
    .split(/\s+/)
    .map((t) => (plain(t) === w.word ? `<mark>${escapeHtml(t)}</mark>` : escapeHtml(t)))
    .join(" ");
}

function select(w) {
  current = w;
  paintList();
  stepEl.hidden = false;
  document.getElementById("drill-word").textContent = w.word;
  document.getElementById("drill-model").innerHTML =
    (window.speakButton(w.word, "Nghe từ, chậm", 0.7) || "") +
    (window.speakButton(w.phrase, "Nghe cả cụm, chậm", 0.75) ||
      '<span class="muted">Trình duyệt này không có giọng đọc tiếng Anh. Thử Chrome, Edge hoặc Safari.</span>');
  document.getElementById("drill-tip").innerHTML = w.tip
    ? `<b>${escapeHtml(w.pattern_name)}.</b> ${escapeHtml(w.tip)}`
    : "Từ này không rơi vào năm lỗi hay gặp của người Việt. Nghe giọng mẫu vài lần rồi nhại theo, chú ý âm cuối.";
  document.getElementById("drill-phrase").innerHTML = phraseHtml(w);
  resultEl.innerHTML = "";
  recorder.reset();
}

function nextOpen() {
  const i = words.indexOf(current);
  return words.slice(i + 1).find((w) => !w.passed) || words.find((w) => !w.passed) || null;
}

function showResult(d) {
  const w = current;
  let h = "";
  if (d.passed) {
    h += `<p class="drill-ok">Máy nghe rõ «${escapeHtml(w.word)}».`;
    h += w.passed ? " Xong từ này." : ` Thêm ${passStreak - w.streak} lượt rõ nữa là xong.`;
    h += "</p>";
  } else {
    h += d.said
      ? `<p class="drill-miss">Máy nghe thành «${escapeHtml(d.said)}», chưa ra «${escapeHtml(w.word)}».</p>`
      : `<p class="drill-miss">Máy chưa nghe rõ «${escapeHtml(w.word)}».</p>`;
    if (d.pattern_tip) h += `<p><b>${escapeHtml(d.pattern_name)}.</b> ${escapeHtml(d.pattern_tip)}</p>`;
    if (d.review_due) {
      h += `<p class="muted small-note">Từ này đã vào danh sách ôn, nhắc lại ngày ${escapeHtml(dmy(d.review_due))}.</p>`;
    }
  }
  if (d.transcript) h += `<p class="muted small-note">Máy nghe được: <span lang="en">${escapeHtml(d.transcript)}</span></p>`;
  const next = w.passed ? nextOpen() : null;
  if (next) h += `<div class="button-row"><button type="button" class="button" id="drill-next">Từ tiếp theo: ${escapeHtml(next.word)}</button></div>`;
  else if (w.passed && words.every((x) => x.passed)) {
    h +=
      '<p class="drill-ok">Đã luyện xong mọi từ của bài này.</p>' +
      `<div class="button-row"><a class="button" href="/report/${encodeURIComponent(RID)}">Về báo cáo</a>` +
      '<a class="button secondary" href="/my-progress">Xem tiến độ</a></div>';
  }
  resultEl.innerHTML = h;
  const btn = document.getElementById("drill-next");
  if (btn) btn.addEventListener("click", () => select(next));
}

async function submit(audio, name) {
  const w = current;
  if (!w) return;
  const body = new FormData();
  body.append("audio", audio, name);
  body.append("word", w.word);
  waitEl.textContent = "Đang nghe lượt này…";
  try {
    const r = await fetch(`/api/v1/learn/drill/${encodeURIComponent(RID)}/takes`, { method: "POST", body });
    if (window.redirectToLoginIfExpired(r)) return;
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      window.toast(typeof d.detail === "string" ? d.detail : "Không gửi được bản ghi.", "error", { sticky: true });
      return;
    }
    recorder.reset();
    if (!d.measured) {
      window.toast(d.tip || "Bản ghi chưa dùng được, hãy nói lại.", "error");
      return;
    }
    Object.assign(w, d.drill);
    paintList();
    showResult(d);
  } catch (err) {
    window.toast("Mất kết nối khi gửi. Bản ghi vẫn còn, hãy thử lại.", "error", { sticky: true });
  } finally {
    waitEl.textContent = "";
  }
}

listEl.addEventListener("click", (e) => {
  const b = e.target.closest("[data-word]");
  if (b) select(words.find((w) => w.word === b.dataset.word));
});
stepEl.querySelectorAll("[data-play]").forEach((b) =>
  b.addEventListener("click", () => {
    if (!current) return;
    if (b.dataset.play === "word") playSpan(current.start_s, current.end_s);
    else playSpan(current.phrase_start_s, current.phrase_end_s);
  }),
);

fetch(`/api/v1/learn/drill/${encodeURIComponent(RID)}`)
  .then((r) => (window.redirectToLoginIfExpired(r) ? null : r.ok ? r.json() : Promise.reject(r.status)))
  .then((d) => {
    if (!d) return;
    window.clearBusy(root);
    document.getElementById("drill-note").textContent = d.note;
    passStreak = d.pass_streak;
    words = d.words;
    if (!words.length) {
      listEl.outerHTML =
        '<p class="empty-state">Bài này không có từ nào máy nghe chưa rõ. ' +
        `<a href="/report/${encodeURIComponent(RID)}">Về báo cáo</a></p>`;
      return;
    }
    select(words.find((w) => !w.passed) || words[0]);
  })
  .catch(() => {
    window.clearBusy(root);
    root.innerHTML =
      '<div class="card"><div class="empty-state"><h2>Không mở được bài này</h2>' +
      "<p>Chỉ luyện lại được từ trong bài đánh giá của chính bạn đã có điểm.</p></div></div>";
  });

fetch("/api/v1/health")
  .then((r) => (r.ok ? r.json() : null))
  .then((h) => recorder.enable(!!(h && h.recording_enabled)))
  .catch(() => recorder.enable(false));
