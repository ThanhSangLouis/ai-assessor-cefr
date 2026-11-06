// The student stage (D093): which world a band belongs to, as on the roadmap
// (practice_adventure.js), and the companion of that world. student_stage.css
// draws the scene from the page's data-world; this sets it and the mascot.
(() => {
  "use strict";

  const WORLDS = {
    A1: { world: "forest", name: "Rừng xanh", say: "Không cần hoàn hảo. Cứ bắt đầu bằng một câu!" },
    A2: { world: "volcano", name: "Miền núi lửa", say: "Kể thêm một chi tiết nữa là câu chuyện sống động hơn." },
    B1: { world: "snow", name: "Xứ tuyết", say: "Nối các ý bằng because, so, then nhé." },
    B2: { world: "river", name: "Dòng sông ngọc", say: "Nêu ý kiến, rồi cho một ví dụ của chính bạn." },
    C1: { world: "desert", name: "Sa mạc vàng", say: "So sánh hai mặt trước khi chốt quan điểm." },
    C2: { world: "flowers", name: "Đồng hoa", say: "Nói tự nhiên như đang trò chuyện với bạn bè." },
  };

  // Points one stage at the world of a band. `parts` names the elements to
  // fill: { band, name, mascot, say }, any of which may be missing.
  function setWorld(page, band, parts = {}) {
    const w = WORLDS[band] || WORLDS.A1;
    page.dataset.world = w.world;
    if (parts.band) parts.band.textContent = WORLDS[band] ? band : "A1";
    if (parts.name) parts.name.textContent = w.name;
    if (parts.say) parts.say.textContent = w.say;
    if (parts.mascot) {
      const src = `/static/art/adventure/mascot-${w.world}-v3.webp`;
      if (parts.mascot.getAttribute("src") !== src) parts.mascot.src = src;
    }
    return w;
  }

  window.studentStage = { WORLDS, setWorld };
})();
