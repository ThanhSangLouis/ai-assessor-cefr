"use strict";
const reportAudio = document.getElementById("report-audio");
const audioStatus = document.getElementById("audio-status");
if (reportAudio && audioStatus) {
  reportAudio.addEventListener("playing", () => {
    audioStatus.textContent = "Đang phát âm thanh bài nộp.";
  });
  reportAudio.addEventListener("error", () => {
    audioStatus.textContent = "Không thể phát âm thanh. Hãy thử tải lại trang hoặc quay về lịch sử bài nộp.";
  });
}
for (const button of document.querySelectorAll("button[data-seek-second]")) {
  button.addEventListener("click", () => {
    const audio = reportAudio;
    const seconds = Number(button.dataset.seekSecond);
    if (!audio || !Number.isFinite(seconds) || seconds < 0) return;
    const seek = () => {
      audio.currentTime = seconds;
      audio.play().catch(() => {});
    };
    if (audio.readyState >= 1) seek();
    else { audio.addEventListener("loadedmetadata", seek, {once: true}); audio.load(); }
  });
}
