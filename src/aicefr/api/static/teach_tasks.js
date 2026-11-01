// The assessment prompts by band (D076), one band at a time: tabs by band,
// a search and a state filter, one row per prompt. Adding and editing happen
// in a dialog; saving a new wording makes a new version on the server.
(function () {
  const escapeHtml = window.escapeHtml;
  const icon = (name) => window.ui.icon(name);
  const $ = (id) => document.getElementById(id);
  const BANDS = ["A1", "A2", "B1", "B2", "C1", "C2"];
  const PART = { P3: "Quan điểm", P4: "Quy trình", P5: "Thuyết trình" };
  const send = (url, method, body) =>
    window.apiJson(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  let tasks = [];
  let band = "A1";
  let editing = null; // the prompt in the dialog, or null for a new one

  function remember() {
    try {
      localStorage.setItem("teach-tasks-band", band);
    } catch (e) {
      /* a private window: the first band it is */
    }
  }

  function tabs() {
    $("bank-tabs").innerHTML = BANDS.map((b) => {
      const on = tasks.filter((t) => t.band === b && t.active).length;
      return `<button type="button" role="tab" data-band="${b}" class="${b === band ? "chosen" : ""}"
        aria-selected="${b === band}">${b} <span class="tab-count">${on}</span></button>`;
    }).join("");
    $("bank-tabs").querySelectorAll("button").forEach((b) =>
      b.addEventListener("click", () => {
        band = b.dataset.band;
        remember();
        paint();
      }),
    );
  }

  function visible() {
    const q = $("bank-search").value.trim().toLowerCase();
    const state = $("bank-state").value;
    return tasks.filter(
      (t) =>
        t.band === band &&
        (state === "all" || (state === "on") === t.active) &&
        (!q || t.prompt_text.toLowerCase().includes(q) || (t.topic_keywords || []).join(" ").includes(q)),
    );
  }

  function paint() {
    tabs();
    const rows = visible();
    const el = $("task-bank");
    window.clearBusy(el);
    if (!rows.length) {
      el.innerHTML = `<p class="muted bank-empty">Không có đề nào ${$("bank-search").value ? "khớp tìm kiếm" : "ở band " + band}.</p>`;
      return;
    }
    el.innerHTML = `<table class="bank-table"><thead><tr><th scope="col">Dạng</th><th scope="col">Đề bài</th>
      <th scope="col">Từ khóa</th><th scope="col">Bản</th><th scope="col"><span class="visually-hidden">Thao tác</span></th></tr></thead><tbody>${rows
      .map(
        (t) => `<tr class="${t.active ? "" : "off"}">
          <td><span class="part-pill part-${escapeHtml(t.part)}">${escapeHtml(PART[t.part] || t.part)}</span></td>
          <td class="bank-text" title="${escapeHtml(t.prompt_text)}">${escapeHtml(t.prompt_text)}</td>
          <td class="num">${(t.topic_keywords || []).length}</td>
          <td class="num">${escapeHtml(t.prompt_version)}</td>
          <td class="bank-actions">
            <button type="button" class="icon-only" data-edit="${escapeHtml(t.task_id)}" aria-label="Sửa đề" title="Sửa">${icon("pencil")}</button>
            <button type="button" class="secondary small" data-toggle="${escapeHtml(t.task_id)}">${t.active ? "Tắt" : "Bật"}</button>
          </td></tr>`,
      )
      .join("")}</tbody></table>`;
    el.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", () => open(b.dataset.edit)));
    el.querySelectorAll("[data-toggle]").forEach((b) =>
      b.addEventListener("click", async () => {
        const t = tasks.find((x) => x.task_id === b.dataset.toggle);
        if (await send(`/api/v1/teach/tasks/${encodeURIComponent(t.task_id)}`, "PATCH", { active: !t.active })) {
          window.toast(t.active ? "Đã tắt đề." : "Đã bật lại đề.", "ok");
          load();
        }
      }),
    );
  }

  function open(taskId) {
    editing = tasks.find((t) => t.task_id === taskId) || null;
    const f = $("task-form");
    f.reset();
    $("task-dialog-h").textContent = editing ? "Sửa đề" : "Thêm đề";
    f.band.value = editing ? editing.band : band;
    f.part.value = editing && editing.part !== "P5" ? editing.part : "P3";
    f.prompt_text.value = editing ? editing.prompt_text : "";
    f.topic_keywords.value = editing ? (editing.topic_keywords || []).join(", ") : "";
    $("task-dialog").showModal();
    f.prompt_text.focus();
  }

  $("task-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    if (f.prompt_text.value.trim().length < 10) {
      window.toast("Đề bài cần ít nhất 10 ký tự.", "error");
      return;
    }
    const body = {
      band: f.band.value,
      part: f.part.value,
      prompt_text: f.prompt_text.value,
      topic_keywords: f.topic_keywords.value,
    };
    const d = editing
      ? await send(`/api/v1/teach/tasks/${encodeURIComponent(editing.task_id)}`, "PATCH", body)
      : await send("/api/v1/teach/tasks", "POST", body);
    if (!d) return;
    $("task-dialog").close();
    band = body.band;
    remember();
    window.toast(editing ? "Đã lưu đề." : "Đã thêm đề.", "ok");
    load();
  });
  $("task-cancel").addEventListener("click", () => $("task-dialog").close());
  $("bank-add").addEventListener("click", () => open(null));
  $("bank-search").addEventListener("input", paint);
  $("bank-state").addEventListener("change", paint);

  async function load() {
    const d = await window.apiJson("/api/v1/teach/tasks");
    if (!d) return;
    tasks = d.map((t) => ({ ...t, band: t.band || "B1" }));
    paint();
  }

  try {
    const kept = localStorage.getItem("teach-tasks-band");
    if (BANDS.includes(kept)) band = kept;
  } catch (e) {
    /* no storage: start at A1 */
  }
  load();
})();
