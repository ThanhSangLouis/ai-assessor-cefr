// The assessment prompts by band (D076): add, reword, retire. A prompt is
// edited in place; saving a new wording makes a new version on the server.
(function () {
  const escapeHtml = window.escapeHtml;
  const $ = (id) => document.getElementById(id);
  const PART = { P3: "Nêu quan điểm", P4: "Mô tả một quy trình", P5: "Thuyết trình (đã ngừng)" };
  const send = (url, method, body) =>
    window.apiJson(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  function row(t) {
    return `<li class="bank-item${t.active ? "" : " off"}" data-id="${escapeHtml(t.task_id)}">
      <div class="bank-meta"><span class="band-badge">${escapeHtml(t.band || "—")}</span>
        <b>${escapeHtml(PART[t.part] || t.part)}</b>
        <span class="muted small">${escapeHtml(t.prompt_version)}${t.active ? "" : " · đã tắt"}</span></div>
      <textarea class="bank-text" rows="2" maxlength="600" aria-label="Đề bài">${escapeHtml(t.prompt_text)}</textarea>
      <input class="bank-keywords" maxlength="600" lang="en" aria-label="Từ khóa" value="${escapeHtml((t.topic_keywords || []).join(", "))}">
      <div class="button-row">
        <button type="button" class="secondary small" data-save>Lưu</button>
        <button type="button" class="secondary small" data-toggle>${t.active ? "Tắt đề" : "Bật lại"}</button>
      </div>
    </li>`;
  }

  async function load() {
    const el = $("task-bank");
    const tasks = await window.apiJson("/api/v1/teach/tasks");
    if (!tasks) return;
    window.clearBusy(el);
    const bands = ["A1", "A2", "B1", "B2", "C1", "C2", ""];
    el.innerHTML = bands
      .map((b) => {
        const mine = tasks.filter((t) => (t.band || "") === b);
        if (!mine.length) return "";
        const on = mine.filter((t) => t.active).length;
        return `<section class="card" aria-label="Band ${escapeHtml(b || "khác")}">
          <div class="card-head"><h2><span class="band-badge">${escapeHtml(b || "—")}</span> ${on} đề đang dùng</h2></div>
          <ul class="bank-list">${mine.map(row).join("")}</ul></section>`;
      })
      .join("");
    el.querySelectorAll(".bank-item").forEach((li) => {
      const id = li.dataset.id;
      const t = tasks.find((x) => x.task_id === id);
      li.querySelector("[data-save]").addEventListener("click", async () => {
        const d = await send(`/api/v1/teach/tasks/${encodeURIComponent(id)}`, "PATCH", {
          prompt_text: li.querySelector(".bank-text").value,
          topic_keywords: li.querySelector(".bank-keywords").value,
        });
        if (d) {
          window.toast("Đã lưu đề.", "ok");
          load();
        }
      });
      li.querySelector("[data-toggle]").addEventListener("click", async () => {
        const d = await send(`/api/v1/teach/tasks/${encodeURIComponent(id)}`, "PATCH", { active: !t.active });
        if (d) load();
      });
    });
  }

  $("task-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    const d = await send("/api/v1/teach/tasks", "POST", {
      band: f.band.value,
      part: f.part.value,
      prompt_text: f.prompt_text.value,
      topic_keywords: f.topic_keywords.value,
    });
    if (d) {
      window.toast("Đã thêm đề.", "ok");
      f.prompt_text.value = "";
      f.topic_keywords.value = "";
      load();
    }
  });

  load();
})();
