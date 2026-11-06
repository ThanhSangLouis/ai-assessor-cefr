"use strict";
const $ = (id) => document.getElementById(id);
const preview = $("preview");
const art = "../../../../src/aicefr/api/static/art/adventure/";
const tasks = [
  {
    title: "Một nơi bạn yêu thích",
    prompt:
      "Describe a place where you feel relaxed. Where is it, what do you do there, and why do you enjoy it?",
    hints: [
      "Nơi đó ở đâu?",
      "Bạn thường làm gì ở đó?",
      "Vì sao bạn thích nơi đó?",
    ],
  },
  {
    title: "Một người truyền cảm hứng",
    prompt:
      "Describe someone who inspires you. Who are they, how did you meet them, and what have you learned from them?",
    hints: [
      "Người đó là ai?",
      "Bạn biết họ như thế nào?",
      "Bạn đã học được điều gì từ họ?",
    ],
  },
  {
    title: "Một điều mới bạn đã thử",
    prompt:
      "Describe a time you tried something new. What did you try, how did you feel, and what did you learn?",
    hints: [
      "Bạn đã thử điều gì?",
      "Bạn cảm thấy thế nào?",
      "Trải nghiệm đó mang lại điều gì?",
    ],
  },
];
let selected = null,
  timer = null,
  sendTimer = null,
  seconds = 0,
  hasTake = false;
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
}
function selectTask(index) {
  selected = index;
  document
    .querySelectorAll("[name=task]")
    .forEach((el, i) => (el.checked = i === index));
  $("task-title").textContent = tasks[index].title;
  $("prompt").textContent = tasks[index].prompt;
  $("hints").replaceChildren(
    ...tasks[index].hints.map((t) => {
      const li = document.createElement("li");
      li.textContent = t;
      return li;
    }),
  );
}
function state(value, seed = false) {
  clearInterval(timer);
  clearTimeout(sendTimer);
  timer = null;
  sendTimer = null;
  if (seed && !["choose", "empty"].includes(value) && selected === null)
    selectTask(0);
  preview.dataset.state = value;
  $("state").value = value;
  const choose = value === "choose",
    empty = value === "empty",
    sending = value === "sending",
    success = value === "success",
    playback = value === "playback",
    error = value === "error";
  if (choose || empty) {
    selected = null;
    hasTake = false;
    document
      .querySelectorAll("[name=task]")
      .forEach((el) => (el.checked = false));
  }
  if (playback) hasTake = true;
  const exists = selected !== null;
  document.querySelector(".task-list").hidden = empty;
  document.querySelector(".empty-state").hidden = !empty;
  document.querySelector(".placeholder").hidden = !choose && !empty;
  document.querySelector(".studio-content").hidden =
    !exists || sending || success;
  document.querySelector(".sending").hidden = !sending;
  document.querySelector(".success").hidden = !success;
  document.querySelector(".review-recording").hidden = !playback;
  document.querySelector(".recorder").hidden = playback;
  document.querySelector(".error-note").hidden = !error;
  document.querySelector(".preparation").hidden = [
    "recording",
    "playback",
    "error",
  ].includes(value);
  document.querySelector(".upload").hidden = value === "recording";
  const busy = ["recording", "sending", "playback"].includes(value);
  document
    .querySelectorAll("[name=task]")
    .forEach((el) => (el.disabled = busy));
  $("shuffle").disabled = busy;
  $("change").disabled = busy;
  $("back").disabled = value === "sending";
  document.querySelectorAll("[data-phase]").forEach((el) => {
    const i = Number(el.dataset.phase);
    const current =
      choose || empty ? 0 : playback || sending || success ? 2 : 1;
    el.classList.toggle("active", i === current);
    el.classList.toggle("done", i < current);
    el.disabled =
      (i > 0 && !exists) ||
      (i === 2 && !hasTake) ||
      sending ||
      value === "recording";
    if (i === current) el.setAttribute("aria-current", "step");
    else el.removeAttribute("aria-current");
  });
  $("record").disabled = false;
  $("record-status").innerHTML =
    "<i></i> " +
    (value === "recording"
      ? "Đang ghi âm · Mô phỏng"
      : error
        ? "Micro chưa được cấp quyền"
        : "Micro · Chưa bắt đầu");
  if (value === "recording")
    $("record-status").innerHTML = "<i></i> Đang ghi âm · Mô phỏng";
  $("record").querySelector("span").textContent =
    value === "recording"
      ? "Dừng ghi âm"
      : error
        ? "Thử lại micro"
        : "Bắt đầu ghi âm";
  $("timer").textContent = "00:00";
  $("record-hint").textContent =
    value === "recording"
      ? "Cứ nói tự nhiên. Bấm dừng khi bạn đã nói xong."
      : "Nói tự nhiên, hướng tới 40–60 giây.";
  $("prep-clock").textContent = "30";
  $("prep-title").textContent =
    value === "prep"
      ? "Đang chuẩn bị câu trả lời…"
      : "Một chút thời gian suy nghĩ";
  $("prep-description").textContent =
    value === "prep"
      ? "Hết thời gian sẽ bắt đầu ghi âm mô phỏng."
      : "30 giây chuẩn bị, hoặc nói ngay khi bạn sẵn sàng.";
  $("prepare").textContent = value === "prep" ? "Nói ngay" : "Chuẩn bị";
  document.querySelector(".duration-track>span").style.width = "0";
  $("mascot-message").innerHTML = success
    ? "Bạn đã dám cất lời.<br>Đó là một bước tiến rồi!"
    : value === "recording"
      ? "Mình đang lắng nghe.<br>Cứ nói theo cách của bạn!"
      : "Bạn không cần hoàn hảo.<br>Cứ bắt đầu bằng một câu nhé!";
  if (value === "prep") {
    seconds = 30;
    timer = setInterval(() => {
      $("prep-clock").textContent = String(--seconds);
      if (seconds === 0) state("recording");
    }, 1000);
  }
  if (value === "recording") {
    seconds = 0;
    timer = setInterval(() => {
      seconds++;
      $("timer").textContent =
        `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
      document.querySelector(".duration-track>span").style.width =
        `${(seconds / 120) * 100}%`;
      if (seconds >= 120) state("playback");
    }, 1000);
  }
}
$("theme").onchange = scene;
$("world").onchange = scene;
$("state").onchange = () => state($("state").value, true);
$("mobile").onclick = () => {
  const on = preview.classList.toggle("mobile");
  $("mobile").setAttribute("aria-pressed", String(on));
  $("mobile").textContent = on ? "Xem toàn chiều rộng" : "Xem mobile";
};
document.querySelectorAll("[name=task]").forEach(
  (el) =>
    (el.onchange = () => {
      selectTask(Number(el.value));
      hasTake = false;
      state("ready");
    }),
);
$("prepare").onclick = () =>
  state(preview.dataset.state === "prep" ? "recording" : "prep");
$("record").onclick = () =>
  state(
    preview.dataset.state === "recording"
      ? "playback"
      : preview.dataset.state === "error"
        ? "ready"
        : "recording",
  );
$("retry").onclick = () => {
  hasTake = false;
  state("ready");
};
$("retry-mic").onclick = () => state("ready");
$("send").onclick = () => {
  state("sending");
  sendTimer = setTimeout(() => state("success"), 1800);
};
$("play").onclick = () => {
  $("play").textContent = "▷ Nghe lại · mô phỏng";
};
$("new-attempt").onclick = () => state("choose");
$("change").onclick = () => state("choose");
$("back").onclick = () => state("choose");
$("reload").onclick = () => state("choose");
$("shuffle").onclick = () => {
  if (selected === null) selectTask(0);
  else selectTask((selected + 1) % 3);
  hasTake = false;
  state("ready");
};
$("audio").onchange = () => {
  if ($("audio").files.length) {
    hasTake = true;
    state("playback");
  }
};
document.querySelectorAll("[data-phase]").forEach(
  (el) =>
    (el.onclick = () => {
      const i = Number(el.dataset.phase);
      state(i === 0 ? "choose" : i === 1 ? "ready" : "playback");
    }),
);
scene();
state("choose");
