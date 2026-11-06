"use strict";
const $ = (id) => document.getElementById(id);
const preview = $("preview");
const art = "../../../../src/aicefr/api/static/art/adventure/";
const worlds = {
  forest: ["A1", "Rừng xanh"],
  volcano: ["A2", "Miền núi lửa"],
  snow: ["B1", "Xứ tuyết"],
  river: ["B2", "Sông ngọc"],
  desert: ["C1", "Sa mạc vàng"],
  flowers: ["C2", "Đồng hoa"],
};
let stage = 1;
let timer = null;
let seconds = 0;
const stepNames = ["Làm quen", "Nói theo mẫu", "Thử sức", "Về đích"];
const titles = [
  "Làm quen với “am” và “have”",
  "Cùng giới thiệu bản thân nhé!",
  "Bây giờ là câu chuyện của bạn",
  "Nhìn lại những gì bạn vừa học",
];
for (let i = 0; i < 43; i++) {
  const bar = document.createElement("i");
  bar.style.setProperty("--h", `${7 + Math.sin(i * 0.7) ** 2 * 23}px`);
  bar.style.setProperty("--delay", `${-i * 0.07}s`);
  document.querySelector(".wave").append(bar);
}
function scene() {
  const w = $("world").value,
    dark = $("theme").value === "dark";
  preview.classList.toggle("dark", dark);
  preview.style.setProperty(
    "--scene",
    `url("${art}${w}-${dark ? "night" : "day"}-a-v3-1536.webp")`,
  );
  $("mascot").src = art + `mascot-${w}-v3.webp`;
  $("mascot").alt = `Bạn đồng hành của vùng ${worlds[w][1]}`;
  $("band").textContent = worlds[w][0];
  $("world-name").textContent = worlds[w][1];
}
function state(value) {
  clearInterval(timer);
  timer = null;
  $("state").value = value;
  preview.dataset.state = value;
  const complete = value === "complete";
  document.querySelector(".completion").hidden = !complete;
  document.querySelector(".learning-layout").hidden = complete;
  document.querySelector(".feedback").hidden = value !== "feedback";
  const labels = {
    ready: [
      "Sẵn sàng khi bạn sẵn sàng",
      "Bắt đầu ghi âm",
      "Tìm một chỗ yên tĩnh, hít thở và bắt đầu thôi.",
    ],
    recording: [
      "Đang thu âm · Bản mô phỏng",
      "Dừng ghi âm",
      "Cứ nói tự nhiên. Bấm dừng khi bạn đã nói xong.",
    ],
    playback: [
      "Bản ghi mẫu · 00:18",
      "▷ Nghe lại bản ghi",
      "Đây là bản xem trước, không thu hoặc phát âm thanh.",
    ],
    feedback: [
      "Đã gửi lượt nói · Mô phỏng",
      "Thử nói thêm một lần",
      "Bạn có thể luyện thêm hoặc chuyển sang bước tiếp theo.",
    ],
    error: [
      "Chưa truy cập được micro",
      "Thử lại micro",
      "Kiểm tra quyền micro trong trình duyệt rồi thử lại.",
    ],
    complete: ["Hoàn thành", "Bắt đầu ghi âm", ""],
  };
  const text = labels[value];
  $("record-status").innerHTML = "<i></i> " + text[0];
  $("record").querySelector("span").textContent = text[1];
  $("record-hint").textContent = text[2];
  $("timer").textContent =
    value === "playback" ? "00:18 / 00:30" : "00:00 / 00:30";
  if (value === "recording") {
    seconds = 0;
    timer = setInterval(() => {
      seconds++;
      $("timer").textContent = `00:${String(seconds).padStart(2, "0")} / 00:30`;
      if (seconds >= 30) state("playback");
    }, 1000);
  }
  document.querySelector(".progress-track>span").style.width = complete
    ? "100%"
    : `${(stage + 1) * 25}%`;
}
function step(index) {
  stage = Math.max(0, Math.min(3, index));
  document.querySelectorAll(".step").forEach((el, i) => {
    el.classList.toggle("active", i === stage);
    el.classList.toggle("done", i < stage);
    el.querySelector(".step-number").textContent =
      i < stage ? "✓" : String(i + 1);
    if (i === stage) el.setAttribute("aria-current", "step");
    else el.removeAttribute("aria-current");
  });
  $("activity-title").textContent = titles[stage];
  $("activity-index").textContent = String(stage + 1).padStart(2, "0");
  $("activity-kind").textContent = stepNames[stage].toUpperCase();
  $("step-count").textContent = `${stage + 1} / 4`;
  $("previous").disabled = stage === 0;
  $("continue").textContent =
    stage === 3 ? "Hoàn thành bài học ✦" : "Bước tiếp theo →";
  $("instruction").textContent =
    stage === 0
      ? "Đọc câu mẫu để nhận ra cách dùng hai từ quen thuộc."
      : stage === 2
        ? "Giới thiệu tên, một điều về bạn và một điều bạn có. Thử nói mà không nhìn mẫu nhé."
        : stage === 3
          ? "Bạn đã luyện giới thiệu bản thân. Có thể nói thêm một lần trước khi kết thúc."
          : "Nghe câu mẫu, rồi thử nói về chính bạn. Không cần giống từng từ đâu.";
  state("ready");
}
$("world").onchange = scene;
$("theme").onchange = scene;
$("state").onchange = () => state($("state").value);
$("mobile").onclick = () => {
  const mobile = preview.classList.toggle("mobile");
  $("mobile").setAttribute("aria-pressed", String(mobile));
  $("mobile").textContent = mobile ? "Xem toàn chiều rộng" : "Xem mobile";
};
$("record").onclick = () =>
  state(
    preview.dataset.state === "recording"
      ? "playback"
      : preview.dataset.state === "playback"
        ? "playback"
        : "recording",
  );
$("retry").onclick = () => state("ready");
$("send").onclick = () => state("feedback");
$("continue").onclick = () =>
  stage === 3 ? state("complete") : step(stage + 1);
$("previous").onclick = () => step(stage - 1);
$("again").onclick = () => step(0);
document
  .querySelectorAll(".step")
  .forEach((el) => (el.onclick = () => step(Number(el.dataset.step))));
$("listen").onclick = () => {
  const b = $("listen");
  b.textContent = "▷ Nghe mẫu · mô phỏng";
  setTimeout(() => (b.textContent = "▷ Nghe mẫu"), 2000);
};
scene();
step(1);
