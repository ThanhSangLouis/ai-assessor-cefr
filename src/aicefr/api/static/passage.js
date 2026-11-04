// Read a passage written around the words still being said again (D090).
// The passage is the language model's (paid once per set of words, read again
// for free) or the learner's own phrases put together (free). A reading is
// measured as a read-aloud step; each word heard clearly counts towards its
// two clear takes in a row (D089), a word that is not goes to spaced review.
const root = document.getElementById("passage");
const escapeHtml = window.escapeHtml;
const listEl = document.getElementById("passage-words");
const emptyEl = document.getElementById("passage-empty");
const makeEl = document.getElementById("passage-make");
const readEl = document.getElementById("passage-read");
const resultEl = document.getElementById("passage-result");
const waitEl = document.getElementById("passage-wait");
const modelBtn = document.getElementById("passage-model");

let state = null;
let passage = null;

const recorder = window.setUpRecorder({
  minSeconds: () => 0,
  maxSeconds: () => 90,
  onSubmit: submit,
});

// "2026-11-03" -> "03/11/2026"
const dmy = (iso) => iso.split("-").reverse().join("/");
const plain = (t) => t.toLowerCase().replace(/[^a-z']/g, "");
const runs = (n) => `${String(n).replace(".", ",")} lượt`;

function badge(w) {
  if (w.passed) return '<span class="badge ok">đã rõ</span>';
  return `<span class="badge">${w.streak}/${state.pass_streak}</span>`;
}

function paintWords() {
  listEl.innerHTML = state.words
    .map((w) => `<li><span class="drill-word${w.passed ? " is-done" : ""}"><span lang="en">${escapeHtml(w.word)}</span> ${badge(w)}</span></li>`)
    .join("");
}

// The written words as the server counts them (`lessons.text.split_words`):
// a hyphenated word is two words, so the marks' indices line up.
const hasLetters = (t) => /[\p{L}\p{N}]/u.test(t);
function textHtml(text, words, marks) {
  const status = new Map((marks || []).map((m) => [m.index, m.teacher || m.status]));
  let i = 0;
  const word = (t) => {
    const s = status.get(i++);
    const cls = s ? (s === "heard" ? " is-heard" : " is-unclear") : "";
    const inner = escapeHtml(t);
    return words.includes(plain(t)) ? `<mark class="passage-target${cls}">${inner}</mark>` : inner;
  };
  return text
    .split(/\s+/)
    .map((raw) => {
      const parts = raw.split("-").filter(hasLetters);
      return parts.length > 1 ? parts.map(word).join("-") : word(raw);
    })
    .join(" ");
}

function paintOffer() {
  const o = state.offer || {};
  let note;
  if (!o.available) {
    note = "AI viết đoạn đang tắt trên máy chủ. Bạn vẫn ghép được đoạn từ chính các cụm của mình.";
  } else if (state.daily_left <= 0) {
    note = "Hôm nay AI đã viết đủ số đoạn cho bạn. Ghép từ cụm của bạn, hoặc quay lại ngày mai.";
  } else {
    const price = o.price ? `${runs(o.price.runs)} (${o.price.idpoint.toLocaleString("vi-VN")} IDPoint)` : "miễn phí";
    note = `AI viết một đoạn ngắn đúng band của bạn: ${price}, chỉ trừ khi viết xong. Đọc lại đoạn đó bao nhiêu lần cũng không mất thêm. Chỉ các từ và band được gửi đi, không gửi giọng nói.`;
  }
  document.getElementById("passage-offer").textContent = note;
  const allowed = !!o.available && state.daily_left > 0;
  modelBtn.disabled = !allowed;
  readEl.querySelector('[data-fresh="model"]').disabled = !allowed;
}

function show(p) {
  passage = p;
  makeEl.hidden = true;
  readEl.hidden = false;
  document.getElementById("passage-source").textContent =
    p.source === "model" ? "Đoạn do AI viết theo band của bạn." : "Đoạn ghép từ các cụm trong bài nói của bạn.";
  document.getElementById("passage-text").innerHTML = textHtml(p.text, p.words, null);
  document.getElementById("passage-voice").innerHTML =
    window.speakButton(p.text, "Nghe giọng mẫu, chậm", 0.85) ||
    '<span class="muted">Trình duyệt này không có giọng đọc tiếng Anh. Thử Chrome, Edge hoặc Safari.</span>';
  resultEl.innerHTML = "";
  recorder.reset();
}

async function make(source, fresh) {
  const buttons = root.querySelectorAll("#passage-model, #passage-phrases, [data-fresh]");
  buttons.forEach((b) => (b.disabled = true));
  const busy = window.toast(source === "model" ? "AI đang viết đoạn…" : "Đang ghép đoạn…", "info");
  try {
    const r = await fetch("/api/v1/learn/passage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source, fresh }),
    });
    if (window.redirectToLoginIfExpired(r)) return;
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      window.toast(typeof d.detail === "string" ? d.detail : "Chưa tạo được đoạn đọc.", "error", { sticky: true });
      return;
    }
    if (source === "model") state.daily_left = Math.max(0, state.daily_left - 1);
    show(d);
  } catch (err) {
    window.toast("Mất kết nối. Hãy thử lại.", "error", { sticky: true });
  } finally {
    if (typeof busy === "function") busy();
    buttons.forEach((b) => (b.disabled = false));
    paintOffer();
  }
}

function showResult(d) {
  document.getElementById("passage-text").innerHTML = textHtml(passage.text, passage.words, d.marks);
  let h = "<ul class=\"passage-verdicts\">";
  for (const w of d.words) {
    h += "<li>";
    if (w.passed) {
      h += `<span class="drill-ok">«${escapeHtml(w.word)}»: máy nghe rõ.</span>`;
    } else {
      h += w.said
        ? `<span class="drill-miss">«${escapeHtml(w.word)}»: máy nghe thành «${escapeHtml(w.said)}».</span>`
        : `<span class="drill-miss">«${escapeHtml(w.word)}»: máy chưa nghe rõ.</span>`;
      if (w.pattern_tip) h += ` <b>${escapeHtml(w.pattern_name)}.</b> ${escapeHtml(w.pattern_tip)}`;
      if (w.review_due) h += ` <span class="muted small-note">Vào danh sách ôn, nhắc lại ngày ${escapeHtml(dmy(w.review_due))}.</span>`;
    }
    h += "</li>";
  }
  h += "</ul>";
  if (d.transcript) h += `<p class="muted small-note">Máy nghe được: <span lang="en">${escapeHtml(d.transcript)}</span></p>`;
  if (state.words.every((w) => w.passed)) {
    h += '<p class="drill-ok">Các từ trong đoạn đã rõ cả.</p><div class="button-row"><a class="button" href="/my-progress">Xem tiến độ</a></div>';
  }
  resultEl.innerHTML = h;
}

async function submit(audio, name) {
  if (!passage) return;
  const body = new FormData();
  body.append("audio", audio, name);
  waitEl.textContent = "Đang nghe lần đọc này…";
  try {
    const r = await fetch(`/api/v1/learn/passage/${encodeURIComponent(passage.passage_id)}/takes`, { method: "POST", body });
    if (window.redirectToLoginIfExpired(r)) return;
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      window.toast(typeof d.detail === "string" ? d.detail : "Không gửi được bản ghi.", "error", { sticky: true });
      return;
    }
    recorder.reset();
    if (!d.measured) {
      window.toast(d.tip || "Bản ghi chưa dùng được, hãy đọc lại.", "error");
      return;
    }
    for (const w of d.words) {
      const kept = state.words.find((x) => x.word === w.word);
      if (kept && w.drill) Object.assign(kept, w.drill);
    }
    paintWords();
    showResult(d);
  } catch (err) {
    window.toast("Mất kết nối khi gửi. Bản ghi vẫn còn, hãy thử lại.", "error", { sticky: true });
  } finally {
    waitEl.textContent = "";
  }
}

modelBtn.addEventListener("click", () => make("model", false));
document.getElementById("passage-phrases").addEventListener("click", () => make("phrases", false));
readEl.querySelectorAll("[data-fresh]").forEach((b) => b.addEventListener("click", () => make(b.dataset.fresh, true)));

fetch("/api/v1/learn/passage")
  .then((r) => (window.redirectToLoginIfExpired(r) ? null : r.ok ? r.json() : Promise.reject(r.status)))
  .then((d) => {
    if (!d) return;
    window.clearBusy(root);
    state = d;
    paintWords();
    if (!d.enough) {
      emptyEl.hidden = false;
      emptyEl.innerHTML =
        `Cần ít nhất ${d.min_words} từ đang luyện dở để viết đoạn đọc; bạn đang có ${d.words.length}. ` +
        "Mở một báo cáo bài nói và bấm «Luyện lại các từ này» trước. " +
        '<a href="/my-progress">Về Tiến độ</a>';
      return;
    }
    paintOffer();
    if (d.passage) show(d.passage);
    else makeEl.hidden = false;
  })
  .catch(() => {
    window.clearBusy(root);
    root.innerHTML =
      '<div class="card"><div class="empty-state"><h2>Không mở được trang này</h2>' +
      "<p>Trang đọc đoạn văn dành cho học viên.</p></div></div>";
  });

fetch("/api/v1/health")
  .then((r) => (r.ok ? r.json() : null))
  .then((h) => recorder.enable(!!(h && h.recording_enabled)))
  .catch(() => recorder.enable(false));
