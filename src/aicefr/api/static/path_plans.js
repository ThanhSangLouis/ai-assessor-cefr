// Paths composed by the path model (D046), on two pages.
//
// The learner's practice page: a path of published lessons for what they ask,
// kept until they ask again or set it aside, with each lesson's reasons and
// state. The teacher's path list: a proposal to review, trim and save as a
// draft path. The model only picks and orders lessons teachers wrote; nothing
// here shows a sentence it made up, because it makes none.
(function () {
  const escapeHtml = window.escapeHtml;
  const icon = (name, cls) => window.ui.icon(name, cls);
  const criterionName = window.ui.practiceName;
  const TOPICS = window.ui.TOPICS;
  const STATUS = {
    completed: ["Đã hoàn thành", "state-on"],
    started: ["Đang học", "state-warn"],
    new: ["Chưa học", "state-off"],
    unavailable: ["Không còn mở", "state-off"],
  };

  async function call(method, url, body) {
    const r = await fetch(url, {
      method,
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (window.redirectToLoginIfExpired(r)) throw new Error("expired");
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      const err = new Error(typeof d.detail === "string" ? d.detail : "Không thực hiện được.");
      err.status = r.status;
      throw err;
    }
    return d;
  }

  function sentence(text) {
    return text ? text.charAt(0).toUpperCase() + text.slice(1) : text;
  }

  // The goal as the API takes it; empty fields stay out.
  function readGoal(form) {
    const values = (name) => [...form.querySelectorAll(`input[name="${name}"]:checked`)].map((i) => i.value);
    const goal = {
      wish: form.elements.wish.value.trim(),
      topics: values("topics"),
      criteria: values("criteria"),
      patterns: values("patterns"),
      // Not form.elements.length: that is the number of controls in the form.
      length: Number(form.querySelector('[name="length"]').value),
    };
    for (const key of ["band_from", "band_to"]) {
      if (form.elements[key] && form.elements[key].value) goal[key] = form.elements[key].value;
    }
    return goal;
  }

  function warnings(list) {
    if (!list || !list.length) return "";
    return (
      '<div class="notice notice-warn plan-warnings">' +
      list.map((w) => `<p>${escapeHtml(w)}</p>`).join("") +
      "</div>"
    );
  }

  function meta(item) {
    const parts = [item.band, `${Number(item.steps)} bước`];
    if (item.topic && TOPICS[item.topic]) parts.push(TOPICS[item.topic][0]);
    if (item.criterion) parts.push(criterionName(item.criterion));
    return parts.map((p) => escapeHtml(p)).join(" · ");
  }

  function reasons(item) {
    return (
      '<ul class="plan-reasons">' +
      (item.reasons || []).map((r) => `<li>${escapeHtml(r)}</li>`).join("") +
      "</ul>"
    );
  }

  // The model's own account of its order: learned from the paths, or the fixed rule.
  function orderNote(m) {
    if (!m) return "";
    const how = m.learned
      ? `Thứ tự học từ ${Number(m.pairs)} cặp bài liền nhau trong các lộ trình hiện có`
      : "Thứ tự theo trình độ rồi độ khó";
    const fit = m.agreement == null ? "" : ` (khớp ${Math.round(m.agreement * 100)}% thứ tự đang có)`;
    return `<p class="muted plan-model">${icon("info")}${escapeHtml(how + fit)}.</p>`;
  }

  // ------------------------------------------------------------ learner
  const mine = document.getElementById("my-plan");
  if (mine) {
    const body = document.getElementById("my-plan-body");
    const form = document.getElementById("my-plan-form");
    const wrap = document.getElementById("my-plan-form-wrap");
    const label = document.getElementById("my-plan-form-label");

    const learnerItem = (item) => {
      const [name, cls] = STATUS[item.status] || STATUS.new;
      const open = item.status === "unavailable";
      const title = open
        ? escapeHtml(item.title)
        : `<a href="/practice/lessons/${encodeURIComponent(item.lesson_id)}">${escapeHtml(item.title)}</a>`;
      return (
        `<li class="plan-item status-${escapeHtml(item.status)}">` +
        `<div class="plan-item-head"><b>${title}</b> <span class="badge ${cls}">${escapeHtml(name)}</span></div>` +
        `<p class="muted plan-meta">${meta(item)}</p>` +
        reasons(item) +
        "</li>"
      );
    };

    const show = (plan) => {
      if (!plan) {
        body.innerHTML =
          '<p class="muted">Bạn chưa có lộ trình riêng. Nhập điều muốn luyện ở dưới, hoặc để trống để hệ thống' +
          " dựa vào bài đánh giá gần nhất.</p>";
        label.textContent = "Ghép lộ trình";
        wrap.open = true;
        return;
      }
      const g = plan.goal || {};
      const asked = g.wish ? `Mục tiêu: “${escapeHtml(g.wish)}”` : "Theo bài đánh giá gần nhất và các ô đã chọn";
      body.innerHTML =
        `<div class="plan-summary"><p><b>${Number(plan.lessons_completed)}/${Number(plan.lessons_total)}</b> bài đã xong · ` +
        `${asked} · ghép ngày ${escapeHtml(window.ui.dmy(plan.created_at))}</p>` +
        `<button type="button" class="small secondary" id="my-plan-close">${icon("archive")}Bỏ lộ trình này</button></div>` +
        warnings(plan.warnings) +
        plan.units
          .map(
            (u) =>
              `<h3 class="plan-unit">${escapeHtml(u.title)}</h3>` +
              `<ol class="plan-list">${u.lessons.map(learnerItem).join("")}</ol>`
          )
          .join("") +
        orderNote(plan.order_model);
      label.textContent = "Ghép lộ trình khác";
      wrap.open = false;
      document.getElementById("my-plan-close").addEventListener("click", async () => {
        try {
          await call("DELETE", "/api/v1/learn/plan");
          show(null);
          window.toast("Đã bỏ lộ trình riêng.", "info");
        } catch (e) {
          if (e.message !== "expired") window.toast(sentence(e.message), "error");
        }
      });
    };

    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const button = form.querySelector('button[type="submit"]');
      button.disabled = true;
      try {
        show(await call("POST", "/api/v1/learn/plan", readGoal(form)));
        window.toast("Đã ghép lộ trình riêng.", "ok");
        mine.scrollIntoView({ behavior: "smooth", block: "start" });
      } catch (e) {
        if (e.message !== "expired") window.toast(sentence(e.message), "error");
      } finally {
        button.disabled = false;
      }
    });

    fetch("/api/v1/learn/plan")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return; // staff open this page too; the plan is a learner's
        mine.hidden = false;
        show(d.plan);
      })
      .catch(() => {});
  }

  // ------------------------------------------------------------ teacher
  const dialog = document.getElementById("compose-dialog");
  const opener = document.getElementById("compose-path");
  if (dialog && opener) {
    const form = document.getElementById("compose-form");
    const save = document.getElementById("compose-save");
    const result = document.getElementById("compose-result");
    let proposal = null;

    const teacherItem = (item) =>
      '<li class="plan-item">' +
      '<label class="plan-keep">' +
      `<input type="checkbox" name="keep" value="${escapeHtml(item.lesson_id)}" checked>` +
      `<span><b>${escapeHtml(item.title)}</b> <span class="muted">· từ “${escapeHtml(item.from_path)}”</span></span>` +
      "</label>" +
      `<p class="muted plan-meta">${meta(item)} · độ phù hợp ${Math.round(Number(item.relevance) * 100)}%</p>` +
      reasons(item) +
      "</li>";

    const back = () => {
      save.hidden = true;
      form.hidden = false;
    };

    opener.addEventListener("click", () => {
      back();
      dialog.showModal();
    });
    document.getElementById("compose-back").addEventListener("click", back);

    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const button = form.querySelector('button[type="submit"]');
      button.disabled = true;
      try {
        proposal = await call("POST", "/api/v1/teach/paths/compose", readGoal(form));
        const count = proposal.units.reduce((n, u) => n + u.lessons.length, 0);
        result.innerHTML =
          `<h3>Đề xuất: ${count} bài từ ${Number(proposal.candidates)} bài đã xuất bản</h3>` +
          warnings(proposal.warnings) +
          proposal.units
            .map(
              (u) =>
                `<h4 class="plan-unit">${escapeHtml(u.title)}</h4>` +
                `<ol class="plan-list">${u.lessons.map(teacherItem).join("")}</ol>`
            )
            .join("") +
          orderNote(proposal.order_model) +
          '<p class="muted">Bỏ chọn những bài không muốn giữ. Lộ trình lưu ra là bản nháp gồm bản sao các bài;' +
          " sửa bản sao không ảnh hưởng bài gốc.</p>";
        const wish = proposal.goal && proposal.goal.wish;
        document.getElementById("compose-title").value = wish ? `Lộ trình: ${wish}`.slice(0, 160) : "";
        form.hidden = true;
        save.hidden = false;
      } catch (e) {
        if (e.message !== "expired") window.toast(sentence(e.message), "error");
      } finally {
        button.disabled = false;
      }
    });

    save.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      if (!proposal) return;
      const keep = [...save.querySelectorAll('input[name="keep"]:checked')].map((i) => i.value);
      if (!keep.length) {
        window.toast("Giữ lại ít nhất một bài.", "error");
        return;
      }
      try {
        const d = await call("POST", `/api/v1/teach/paths/compose/${encodeURIComponent(proposal.plan_id)}/save`, {
          title: document.getElementById("compose-title").value.trim(),
          lesson_ids: keep,
        });
        dialog.close();
        window.toast(`Đã lưu lộ trình nháp gồm ${Number(d.lessons)} bài. Sửa rồi xuất bản như mọi lộ trình.`, "ok");
        setTimeout(() => location.reload(), 600);
      } catch (e) {
        if (e.message !== "expired") window.toast(sentence(e.message), "error");
      }
    });
  }
})();
