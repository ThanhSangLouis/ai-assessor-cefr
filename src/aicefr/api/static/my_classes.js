// "Lớp của tôi" (D109): the classes a student is in, the invitations waiting
// for an answer, and the join code box. Joining, accepting and leaving are the
// student's own acts: a class's teachers see its members' work.
const escapeHtml = window.escapeHtml;
const post = (url, body) =>
  window.apiJson(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
const teachersOf = (c) => (c.teachers || []).map((t) => escapeHtml(t.name)).join(", ") || "chưa có giảng viên";
const base = (id) => `/api/v1/me/classes/${encodeURIComponent(id)}`;

async function load() {
  const d = await window.apiJson("/api/v1/me/classes");
  if (!d) return;
  const invitesCard = document.getElementById("invites-card");
  invitesCard.hidden = !d.invitations.length;
  document.getElementById("invites").innerHTML = d.invitations
    .map(
      (c) => `<li class="assign-row"><div><b>${escapeHtml(c.name)}</b>
        <div class="muted small">Giảng viên: ${teachersOf(c)}</div></div>
        <div class="button-row">
          <button class="button small" data-accept="${escapeHtml(c.class_id)}">Vào lớp</button>
          <button class="button secondary small" data-decline="${escapeHtml(c.class_id)}">Từ chối</button>
        </div></li>`,
    )
    .join("");
  const mine = document.getElementById("mine");
  mine.removeAttribute("aria-busy");
  mine.innerHTML = d.classes.length
    ? `<ul class="plain-list">${d.classes
        .map(
          (c) => `<li class="assign-row"><div><b>${escapeHtml(c.name)}</b>${c.archived ? ' <span class="badge muted">đã kết thúc</span>' : ""}
            <div class="muted small">Giảng viên: ${teachersOf(c)}</div></div>
            <button class="button secondary small" data-leave="${escapeHtml(c.class_id)}" data-name="${escapeHtml(c.name)}">Rời lớp</button></li>`,
        )
        .join("")}</ul>`
    : '<p class="muted">Bạn chưa ở lớp nào. Nhập mã giảng viên đưa để vào lớp.</p>';

  document.querySelectorAll("button[data-accept]").forEach((b) =>
    b.addEventListener("click", async () => {
      if (await post(`${base(b.dataset.accept)}/accept`)) {
        window.toast("Đã vào lớp.", "ok");
        done();
      }
    }),
  );
  document.querySelectorAll("button[data-decline]").forEach((b) =>
    b.addEventListener("click", async () => {
      if (await post(`${base(b.dataset.decline)}/decline`)) {
        window.toast("Đã từ chối lời mời.", "ok");
        done();
      }
    }),
  );
  document.querySelectorAll("button[data-leave]").forEach((b) =>
    b.addEventListener("click", async () => {
      const sure = await window.ui.confirm({
        title: `Rời lớp “${b.dataset.name}”?`,
        message: "Giảng viên của lớp sẽ không còn xem và duyệt bài của bạn. Muốn quay lại, bạn cần mã lớp hoặc lời mời.",
        ok: "Rời lớp",
        cancel: "Ở lại",
        danger: true,
        icon: "logout",
      });
      if (!sure) return;
      if (await post(`${base(b.dataset.leave)}/leave`)) {
        window.toast("Đã rời lớp.", "ok");
        done();
      }
    }),
  );
}

function done() {
  window.ui?.refreshBadges?.();
  load();
}

document.getElementById("join-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const d = await post("/api/v1/me/classes/join", { code: e.target.code.value });
  if (!d) return;
  window.toast(d.joined ? `Đã vào lớp “${d.class.name}”.` : `Bạn đã ở trong lớp “${d.class.name}”.`, "ok");
  e.target.reset();
  done();
});

load();
