"use strict";

const form = document.querySelector("form[data-recorder]");
if (form) {
  const taskPicker = document.getElementById("task-selector");
  const taskId = document.getElementById("task-id");
  const taskVersion = document.getElementById("task-version");
  const taskPrompt = document.getElementById("task-prompt");
  const prepPanel = document.querySelector("[data-preparation]");
  const prepBegin = document.getElementById("prep-begin");
  const prepSkip = document.getElementById("prep-skip");
  const prepClock = document.getElementById("prep-clock");
  const controls = document.getElementById("recording-controls");
  const start = document.getElementById("record-start");
  const stop = document.getElementById("record-stop");
  const notice = document.getElementById("record-notice");
  const preview = document.getElementById("record-preview");
  const file = document.getElementById("audio");
  const progress = document.getElementById("upload-progress");
  const retryPanel = document.getElementById("retry-confirm");
  const retryChecked = document.getElementById("retry-checked");
  const submit = form.querySelector("button[type=submit]");
  const recordingEnabled = form.dataset.recordingEnabled === "true";
  let recorder, stream, recorded, previewURL, timer, ticker, preparationTimer;
  let prepared = false;
  let ambiguousSubmit = false;

  const hasTask = () => Boolean(taskId.value && taskVersion.value);
  const selectedAudio = () => recorded || file.files[0] || null;
  const clearPreview = () => {
    if (previewURL) URL.revokeObjectURL(previewURL);
    previewURL = null;
    preview.removeAttribute("src");
    preview.hidden = true;
  };
  const updateSubmit = () => {
    submit.disabled = !hasTask() || !prepared || !selectedAudio() ||
      (ambiguousSubmit && !retryChecked.checked);
    start.disabled = !recordingEnabled || !prepared || !hasTask() || !navigator.mediaDevices?.getUserMedia || !window.MediaRecorder;
  };
  const cleanup = () => {
    clearTimeout(timer);
    clearInterval(ticker);
    if (stream) stream.getTracks().forEach(track => track.stop());
    if (taskPicker) {
      taskPicker.disabled = !taskPicker.selectedOptions[0]?.dataset.taskId;
    }
    if (file) file.disabled = !hasTask();
    if (start) start.disabled = true;
    if (stop) stop.disabled = true;
  };
  const useTaskOption = option => {
    taskId.value = option?.dataset.taskId || "";
    taskVersion.value = option?.dataset.taskVersion || "";
    taskPrompt.textContent = option?.dataset.prompt || "Khi có đề bài, nội dung sẽ hiện ở đây.";
    if (file) file.value = "";
    recorded = null;
    clearPreview();
    ambiguousSubmit = false;
    retryPanel.hidden = true;
    retryChecked.checked = false;
    updateSubmit();
  };
  const markPrepared = message => {
    prepared = true;
    clearInterval(preparationTimer);
    prepClock.textContent = message;
    prepBegin.hidden = true;
    prepSkip.hidden = true;
    controls.hidden = !recordingEnabled;
    notice.textContent = "Bạn đã sẵn sàng. Chọn tệp hoặc ghi âm, sau đó nghe lại trước khi nộp.";
    updateSubmit();
  };

  if (taskPicker) {
    taskPicker.addEventListener("change", () => useTaskOption(taskPicker.selectedOptions[0]));
    useTaskOption(taskPicker.selectedOptions[0]);
  }

  prepBegin.addEventListener("click", () => {
    if (!hasTask()) return;
    prepBegin.disabled = true;
    prepSkip.disabled = false;
    let remaining = 30;
    prepClock.textContent = `Còn ${remaining} giây chuẩn bị.`;
    preparationTimer = setInterval(() => {
      remaining -= 1;
      if (remaining <= 0) markPrepared("Đã xong phần chuẩn bị.");
      else prepClock.textContent = `Còn ${remaining} giây chuẩn bị.`;
    }, 1000);
  });
  prepSkip.addEventListener("click", () => {
    if (hasTask()) markPrepared("Bạn đã bỏ qua phần chuẩn bị.");
  });

  const available = recordingEnabled && navigator.mediaDevices?.getUserMedia && window.MediaRecorder;
  if (!available) notice.textContent = "Ghi âm trực tiếp chưa khả dụng trên trình duyệt này. Bạn vẫn có thể chọn tệp.";
  start.disabled = true;
  stop.disabled = true;

  start.addEventListener("click", async () => {
    if (!prepared || !hasTask()) return;
    start.disabled = true;
    try {
      stream = await navigator.mediaDevices.getUserMedia({audio: true});
      const mime = ["audio/webm;codecs=opus", "audio/mp4"].find(type => MediaRecorder.isTypeSupported(type));
      if (!mime) throw new Error("unsupported");
      recorder = new MediaRecorder(stream, {mimeType: mime});
      const parts = [];
      let bytes = 0;
      recorded = null;
      file.value = "";
      recorder.addEventListener("dataavailable", event => {
        parts.push(event.data);
        bytes += event.data.size;
        if (bytes > Number(form.dataset.maxBytes) && recorder.state === "recording") recorder.stop();
      });
      recorder.addEventListener("stop", () => {
        const blob = new Blob(parts, {type: mime});
        recorded = new File([blob], mime.startsWith("audio/webm") ? "recording.webm" : "recording.mp4", {type: mime});
        clearPreview();
        previewURL = URL.createObjectURL(blob);
        preview.src = previewURL;
        preview.hidden = false;
        file.required = false;
        notice.textContent = "Đã ghi âm. Nghe lại trước khi nộp; bạn có thể ghi lại để thay thế.";
        cleanup();
        updateSubmit();
      });
      recorder.addEventListener("error", () => {
        notice.textContent = "Không thể ghi âm. Hãy chọn tệp âm thanh rồi thử lại.";
        cleanup();
        updateSubmit();
      });
      recorder.start(1000);
      if (taskPicker) taskPicker.disabled = true;
      file.disabled = true;
      stop.disabled = false;
      const begun = Date.now();
      const maximum = Math.min(Number(form.dataset.maxSeconds), 300);
      ticker = setInterval(() => {
        notice.textContent = `Đang ghi: ${Math.floor((Date.now() - begun) / 1000)} / ${maximum} giây`;
      }, 500);
      timer = setTimeout(() => {
        if (recorder.state === "recording") recorder.stop();
      }, maximum * 1000);
    } catch (_) {
      notice.textContent = "Không thể bật micro. Kiểm tra quyền trình duyệt hoặc chọn tệp âm thanh.";
      cleanup();
      updateSubmit();
    }
  });

  stop.addEventListener("click", () => {
    if (recorder?.state === "recording") recorder.stop();
  });
  file.addEventListener("change", () => {
    recorded = null;
    file.required = true;
    clearPreview();
    const selected = file.files[0];
    if (selected) {
      previewURL = URL.createObjectURL(selected);
      preview.src = previewURL;
      preview.hidden = false;
      notice.textContent = `Đã chọn ${selected.name}. Nghe lại trước khi nộp.`;
    } else {
      notice.textContent = prepared ? "Chọn tệp âm thanh hoặc ghi âm trực tiếp." : "Bắt đầu phần chuẩn bị để tiếp tục.";
    }
    ambiguousSubmit = false;
    retryPanel.hidden = true;
    retryChecked.checked = false;
    updateSubmit();
  });
  retryChecked.addEventListener("change", updateSubmit);

  form.addEventListener("submit", event => {
    event.preventDefault();
    if (!prepared) {
      notice.textContent = "Hãy hoàn thành hoặc bỏ qua phần chuẩn bị trước khi nộp.";
      prepPanel.scrollIntoView({block: "center"});
      return;
    }
    if (recorder?.state === "recording") {
      notice.textContent = "Dừng ghi âm trước khi nộp.";
      return;
    }
    const audio = selectedAudio();
    if (!audio) {
      notice.textContent = "Ghi âm hoặc chọn tệp trước khi nộp.";
      return;
    }
    if (ambiguousSubmit && !retryChecked.checked) {
      notice.textContent = "Hãy kiểm tra lịch sử bài nộp trước khi xác nhận gửi lại.";
      return;
    }
    if (audio.size > Number(form.dataset.maxBytes)) {
      notice.textContent = "Tệp vượt giới hạn dung lượng. Hãy chọn bản ghi ngắn hoặc nhỏ hơn.";
      return;
    }
    const payload = new FormData(form);
    payload.set("audio", audio);
    submit.disabled = true;
    prepBegin.disabled = true;
    prepSkip.disabled = true;
    progress.hidden = false;
    notice.textContent = "Đang gửi bài… Không đóng trang trong lúc tải lên.";
    const request = new XMLHttpRequest();
    request.open("POST", "/api/student/responses");
    request.upload.addEventListener("progress", event => {
      if (event.lengthComputable) progress.value = 100 * event.loaded / event.total;
    });
    request.addEventListener("load", () => {
      let response = {};
      try { response = JSON.parse(request.responseText); } catch (_) { /* handled below */ }
      if (request.status === 201 && response.response_id) {
        window.location.assign("/student/responses/" + encodeURIComponent(response.response_id));
        return;
      }
      progress.hidden = true;
      const messages = {
        CONSENT_VERSION_STALE: "Đồng ý xử lý dữ liệu đã thay đổi. Hãy xem lại trạng thái đồng ý trước khi nộp.",
        UNSUPPORTED_AUDIO_FORMAT: "Định dạng tệp chưa được chấp nhận. Hãy chọn tệp âm thanh được hỗ trợ.",
        AUDIO_TOO_LARGE: "Tệp vượt giới hạn dung lượng. Hãy chọn bản ghi nhỏ hơn.",
        EMPTY_AUDIO: "Tệp âm thanh không có dữ liệu. Hãy chọn hoặc ghi lại âm thanh.",
        TASK_NOT_OPEN: "Đề bài hiện không mở. Hãy quay lại danh sách đề bài.",
        RATE_LIMITED: "Bạn vừa gửi nhiều yêu cầu. Hãy đợi trước khi thử lại.",
        SESSION_REQUIRED: "Phiên đăng nhập đã kết thúc. Hãy đăng nhập lại.",
        ACCESS_DENIED: "Tài khoản hiện không thể nộp bài này.",
      };
      const code = String(response.error || "REQUEST_FAILED");
      notice.textContent = messages[code] || "Server chưa xác nhận trạng thái bài nộp. Hãy kiểm tra lịch sử trước khi gửi lại.";
      if (request.status >= 500 || request.status === 0) {
        ambiguousSubmit = true;
        retryPanel.hidden = false;
      } else {
        ambiguousSubmit = false;
        retryPanel.hidden = true;
      }
      prepBegin.disabled = false;
      prepSkip.disabled = false;
      updateSubmit();
    });
    request.addEventListener("error", () => {
      progress.hidden = true;
      ambiguousSubmit = true;
      retryPanel.hidden = false;
      notice.textContent = "Kết nối bị gián đoạn; server chưa xác nhận trạng thái. Kiểm tra lịch sử trước khi gửi lại.";
      prepBegin.disabled = false;
      prepSkip.disabled = false;
      updateSubmit();
    });
    request.send(payload);
  });
  window.addEventListener("pagehide", () => {
    clearInterval(preparationTimer);
    cleanup();
    if (previewURL) URL.revokeObjectURL(previewURL);
  });
}
