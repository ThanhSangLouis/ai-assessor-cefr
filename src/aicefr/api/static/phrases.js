// The phrase book (D070): today's few cards, then every card with its box.
// A card shows the phrase, its meaning and the sentence of the upgraded answer
// that used it; the learner says a sentence of their own, then says whether it
// came. The server moves the card (coach/phrasebook.py).
const root = document.getElementById("phrases");
const todayBody = document.getElementById("phrase-today-body");
const allCard = document.getElementById("phrase-all");
const allBody = document.getElementById("phrase-all-body");
const escapeHtml = window.escapeHtml;

// Box -> words: where the card is on its way to being learned.
const BOX_TEXT = ["Mới", "Ôn sau 1 ngày", "Ôn sau 3 ngày", "Ôn sau 7 ngày", "Ôn sau 16 ngày", "Ôn sau 35 ngày"];

let queue = [];
let book = null;

function dueDay(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  if (d <= new Date()) return "đến hạn";
  const two = (n) => String(n).padStart(2, "0");
  return `ôn lại ${two(d.getDate())}/${two(d.getMonth() + 1)}`;
}

function cardHtml(c) {
  return (
    '<article class="phrase-card">' +
    `<p class="phrase-text" lang="en"><b>${escapeHtml(c.phrase)}</b> ${window.speakButton(c.phrase)}</p>` +
    `<p class="phrase-meaning">${escapeHtml(c.meaning_vi)}</p>` +
    (c.example
      ? `<details class="phrase-example"><summary>Câu mẫu trong bài của bạn</summary>` +
        `<p lang="en">${escapeHtml(c.example)} ${window.speakButton(c.example)}</p></details>`
      : "") +
    '<p class="muted small-note">Nói to một câu của riêng bạn có dùng cụm này, về chủ đề bất kỳ.</p>' +
    '<div class="button-row">' +
    `<button type="button" class="button" data-key="${escapeHtml(c.key)}" data-ok="1">Nói được</button>` +
    `<button type="button" class="button secondary" data-key="${escapeHtml(c.key)}" data-ok="0">Chưa nhớ</button>` +
    "</div></article>"
  );
}

function paintToday() {
  if (!book.total) {
    todayBody.innerHTML =
      '<div class="empty-state"><h3>Sổ còn trống</h3>' +
      "<p>Mở báo cáo một bài đánh giá đã có kết quả, bấm <b>Xem bài của tôi ở band cao hơn</b>: " +
      'các cụm từ AI gợi ý sẽ vào đây. <a href="/my-responses">Bài đã nộp</a></p></div>';
    return;
  }
  if (!queue.length) {
    todayBody.innerHTML =
      `<p class="phrase-done">${window.ui.icon("check-circle")} Xong phần hôm nay.` +
      ` Đã thuộc <b>${book.learned}</b>/${book.total} cụm.</p>`;
    return;
  }
  todayBody.innerHTML =
    `<p class="muted">Còn <b>${queue.length}</b> cụm hôm nay (tối đa ${book.per_day} mỗi ngày).</p>` +
    cardHtml(queue[0]);
}

function paintAll() {
  allCard.hidden = !book.total;
  allBody.innerHTML =
    `<p class="muted">${book.total} cụm, đã thuộc ${book.learned} (ôn đúng ba lần liền trở lên).</p>` +
    '<ul class="phrase-list">' +
    book.cards
      .map(
        (c) =>
          `<li><span lang="en"><b>${escapeHtml(c.phrase)}</b></span> <span class="muted">${escapeHtml(c.meaning_vi)}</span>` +
          `<span class="phrase-box" data-box="${c.box}">${BOX_TEXT[c.box] || ""} · ${dueDay(c.due)}</span></li>`
      )
      .join("") +
    "</ul>";
}

async function load() {
  const r = await fetch("/api/v1/me/phrases");
  if (window.redirectToLoginIfExpired(r)) return;
  if (!r.ok) throw new Error(String(r.status));
  book = await r.json();
  queue = book.due.slice();
  window.clearBusy(root);
  paintToday();
  paintAll();
}

todayBody.addEventListener("click", async (e) => {
  const b = e.target.closest("button[data-key]");
  if (!b) return;
  todayBody.querySelectorAll("button[data-key]").forEach((x) => (x.disabled = true));
  try {
    const r = await fetch("/api/v1/me/phrases/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: b.dataset.key, remembered: b.dataset.ok === "1" }),
    });
    if (window.redirectToLoginIfExpired(r)) return;
    if (!r.ok) throw new Error(String(r.status));
    const card = await r.json();
    queue.shift();
    book.cards = book.cards.map((c) => (c.key === card.key ? card : c));
    book.learned = book.cards.filter((c) => c.box >= 3).length;
    paintToday();
    paintAll();
  } catch (err) {
    window.toast("Chưa lưu được, hãy thử lại.", "error");
    todayBody.querySelectorAll("button[data-key]").forEach((x) => (x.disabled = false));
  }
});

load().catch(() => {
  window.clearBusy(root);
  todayBody.innerHTML = '<p class="error">Không tải được sổ cụm từ. Hãy tải lại trang sau ít phút.</p>';
});
