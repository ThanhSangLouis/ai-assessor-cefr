// Guided listening (D056): a few six-second moments of my own recording, the
// same four answers at each, and what I meant to say. Some moments are where
// the machine measured something and some are chosen at random; the page is
// not told which, so it cannot let it slip.
(function () {
  const escapeHtml = window.escapeHtml;
  const reportEl = document.getElementById("evidence");
  const ID = reportEl.dataset.responseId;
  const mmss = window.ui.mmss;

  function playSpan(player, start, end) {
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

  function card(d) {
    const choices = Object.entries(d.choices);
    const items = d.moments
      .map(
        (m, i) => `<li class="replay-moment" data-moment="${escapeHtml(m.moment_id)}">
        <div class="replay-head"><b>Đoạn ${i + 1}</b> <span class="muted">${mmss(m.start_s)}–${mmss(m.end_s)}</span>
          <button type="button" class="button secondary small" data-play="${m.start_s}" data-end="${m.end_s}">▶ Nghe đoạn này</button></div>
        <fieldset><legend class="small">Ở đoạn này, bạn thấy mình nói thế nào?</legend>
          ${choices
            .map(
              ([key, label]) => `<label class="check-row"><input type="radio" name="c-${escapeHtml(m.moment_id)}" value="${escapeHtml(key)}"${m.choice === key ? " checked" : ""}> ${escapeHtml(label)}</label>`,
            )
            .join("")}
        </fieldset>
        <label class="field small"><span>Bạn định nói gì ở đoạn này? (không bắt buộc)</span>
          <input name="intended" maxlength="300" value="${escapeHtml(m.intended)}"></label>
        <span class="muted small replay-saved" aria-live="polite">${m.choice ? "Đã lưu" : ""}</span>
      </li>`,
      )
      .join("");
    return `<section class="card anchor-target" id="report-replay" aria-labelledby="replay-h">
      <h2 id="replay-h">Tự nghe lại bài của mình</h2>
      <p class="muted">Nghe từng đoạn ngắn rồi chọn câu đúng nhất với cảm nhận của bạn. Không có đáp án đúng sai;
      câu trả lời chỉ dùng để hiện lại cho bạn trên trang Tiến độ và, nếu bạn đã cho phép dùng cho nghiên cứu, để
      kiểm tra xem các đoạn máy chọn có thật sự hữu ích không.</p>
      <ol class="plain-list replay-list">${items}</ol>
    </section>`;
  }

  async function save(li) {
    const picked = li.querySelector("input[type=radio]:checked");
    if (!picked) return;
    const r = await fetch(
      `/api/v1/responses/${encodeURIComponent(ID)}/replay/${encodeURIComponent(li.dataset.moment)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ choice: picked.value, intended: li.querySelector("input[name=intended]").value }),
      },
    );
    li.querySelector(".replay-saved").textContent = r.ok ? "Đã lưu" : "Chưa lưu được";
  }

  document.addEventListener("report:ready", async () => {
    const r = await fetch(`/api/v1/responses/${encodeURIComponent(ID)}/replay`);
    if (!r.ok) return; // off, not mine, or held back by the study: nothing to show
    const d = await r.json();
    if (!d.moments.length) return;
    const anchor = document.getElementById("report-evidence");
    if (!anchor) return;
    anchor.insertAdjacentHTML("afterend", card(d));
    const box = document.getElementById("report-replay");
    const player = document.getElementById("phat");
    box.querySelectorAll("[data-play]").forEach((b) =>
      b.addEventListener("click", () => player && playSpan(player, Number(b.dataset.play), Number(b.dataset.end))),
    );
    box.querySelectorAll(".replay-moment").forEach((li) => {
      li.querySelectorAll("input[type=radio]").forEach((x) => x.addEventListener("change", () => save(li)));
      li.querySelector("input[name=intended]").addEventListener("change", () => save(li));
    });
  });
})();
