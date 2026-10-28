// Shared recorder for every screen that takes a spoken answer (submit, practice).
//
// One big button, a clock against the task's time window and a live level meter.
// After stopping, the learner listens back and then submits or records again --
// the project owner's choice on 06/10/2026, so a slip of the finger never sends a
// recording nobody heard. Uploading an existing file is the secondary path,
// folded away until needed, and it ends in the same listen-then-submit step.
//
// The space bar starts and stops recording when focus is not in a form control:
// reaching for the mouse in the middle of an answer breaks the flow of speech.
// It does nothing once a recording is waiting to be heard, so a second press
// can neither throw that recording away nor submit it.
//
// Markup: templates/_recorder.html. A page calls `window.setUpRecorder` once and
// keeps the returned controller.
(function () {
  const $ = (id) => document.getElementById(id);

  function clock(seconds) {
    const s = Math.max(0, Math.floor(seconds));
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  }

  function humanSize(bytes) {
    if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  // Why live recording is unavailable, or null when it works. The three causes
  // need three different fixes, so the learner is told which one applies.
  function blockedReason(serverCanTranscode) {
    if (!serverCanTranscode) {
      return "Máy chủ chưa cài <code>ffmpeg</code> nên chưa ghi âm trực tiếp được. Hãy chọn file.";
    }
    if (!navigator.mediaDevices || typeof MediaRecorder === "undefined") {
      return "Trình duyệt này không hỗ trợ ghi âm. Hãy dùng Chrome, Edge hoặc Firefox bản mới, hoặc chọn file.";
    }
    if (!window.isSecureContext) {
      return "Trình duyệt chỉ cho ghi âm trên kết nối bảo mật (https hoặc localhost). Hãy chọn file.";
    }
    return null;
  }

  // Options:
  //   minSeconds(), maxSeconds()  the task's time window
  //   onSubmit(blob, name)        sends the take; may be async
  //   onChange(state, take)       optional, after every state change
  //   onTake(take)                optional, returns an extra note for the take
  //                               (called again once a file's length is known)
  window.setUpRecorder = function (opts) {
    const root = $("rec");
    // A step with no minimum (read one sentence) passes 0; only a missing
    // value falls back to the assessment window.
    const num = (v, fallback) => (Number.isFinite(Number(v)) && v !== null ? Number(v) : fallback);
    const minS = () => num(opts.minSeconds(), 20);
    const maxS = () => num(opts.maxSeconds(), 300) || 300;
    // The QC floor in force. Under it a recording is rejected outright; between
    // it and the task minimum it is accepted but short of what the task asks.
    const floorS = () => Number(root.dataset.floorSeconds) || minS();
    const scaleS = () => maxS() * 1.25;

    const live = $("rec-live");
    const button = $("rec-button");
    const buttonLabel = $("rec-button-label");
    const clockEl = $("rec-clock");
    const windowEl = $("rec-window");
    const level = $("rec-level");
    const guide = $("duration-guide");
    const fill = $("duration-fill");
    const span = $("duration-window");
    const hint = $("rec-hint");
    const off = $("recorder-off");
    const review = $("rec-review");
    const take = $("rec-take");
    const preview = $("rec-preview");
    const verdictEl = $("rec-verdict");
    const note = $("rec-note");
    const submit = $("rec-submit");
    const submitLabel = submit.textContent;
    const redo = $("rec-redo");
    const upload = $("rec-upload");
    const fileEl = $("audio");
    const dropzone = $("dropzone");
    const status = $("rec-status");
    const form = root.closest("form");

    let canRecord = false;
    let blocked = false;
    let recorder = null;
    let stream = null;
    let chunks = [];
    let startedAt = 0;
    let ticker = null;
    let audioCtx = null;
    let current = null; // { blob, name, seconds, fromFile }

    const state = () => root.getAttribute("data-state");

    function setState(next) {
      root.setAttribute("data-state", next);
      review.hidden = !["review", "submitting", "submitted"].includes(next);
      button.classList.toggle("recording", next === "recording");
      buttonLabel.textContent = next === "recording" ? "Dừng ghi âm" : "Bắt đầu ghi âm";
      submit.disabled = blocked || next !== "review";
      redo.disabled = next !== "review";
      submit.textContent =
        next === "submitting" ? "Đang gửi…" : next === "submitted" ? "Đã nộp" : submitLabel;
      if (opts.onChange) opts.onChange(next, current);
    }

    function say(text) {
      hint.textContent = text;
      status.textContent = text;
    }

    function paintWindow() {
      const left = (minS() / scaleS()) * 100;
      span.style.left = `${left}%`;
      span.style.width = `${(maxS() / scaleS()) * 100 - left}%`;
      windowEl.textContent = minS() > 0 ? `/ ${minS()}–${maxS()} giây` : `/ tối đa ${maxS()} giây`;
    }

    function paint(seconds) {
      fill.style.width = `${Math.min(100, (seconds / scaleS()) * 100)}%`;
      guide.classList.toggle("in-range", seconds >= minS() && seconds <= maxS());
      guide.classList.toggle("over", seconds > maxS());
      clockEl.textContent = clock(seconds);
    }

    function meterOn(s) {
      try {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 512;
        audioCtx.createMediaStreamSource(s).connect(analyser);
        const buf = new Uint8Array(analyser.frequencyBinCount);
        (function draw() {
          if (!audioCtx) return;
          analyser.getByteTimeDomainData(buf);
          let peak = 0;
          for (const v of buf) peak = Math.max(peak, Math.abs(v - 128));
          level.style.width = `${Math.min(100, (peak / 128) * 180)}%`;
          requestAnimationFrame(draw);
        })();
      } catch (err) {
        level.style.width = "0";
      }
    }

    function meterOff() {
      if (audioCtx) audioCtx.close();
      audioCtx = null;
      level.style.width = "0";
    }

    function tick() {
      const s = (Date.now() - startedAt) / 1000;
      paint(s);
      if (minS() <= 0) {
        hint.textContent = `Đang ghi. Dừng khi bạn nói xong, tối đa ${maxS()} giây.`;
      } else {
        hint.textContent =
          s < minS()
            ? `Đang ghi. Cần thêm ${Math.ceil(minS() - s)} giây để đủ ${minS()} giây.`
            : `Đã đủ ${minS()} giây. Dừng khi bạn nói xong, tối đa ${maxS()} giây.`;
      }
      // Stop at the ceiling: talking past it only produces a file QC rejects.
      if (s >= maxS()) stop();
    }

    async function start() {
      if (blocked) return;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (err) {
        say("Không truy cập được micro. Hãy cấp quyền micro cho trang này, hoặc chọn file.");
        window.toast("Không truy cập được micro.", "error");
        return;
      }
      clearTake();
      chunks = [];
      recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      recorder.onstop = finish;
      recorder.start();
      startedAt = Date.now();
      ticker = setInterval(tick, 200);
      meterOn(stream);
      setState("recording");
      say(
        minS() > 0
          ? `Đang ghi. Nói tối thiểu ${minS()} giây, tối đa ${maxS()} giây.`
          : `Đang ghi. Tối đa ${maxS()} giây.`
      );
    }

    function stop() {
      if (recorder && recorder.state !== "inactive") recorder.stop();
    }

    function finish() {
      clearInterval(ticker);
      meterOff();
      stream.getTracks().forEach((t) => t.stop());
      const seconds = (Date.now() - startedAt) / 1000;
      // MediaRecorder gives WebM/Opus on Chrome and Firefox, MP4/AAC on Safari;
      // the extension must match because the server picks its decoder by it.
      const type = recorder.mimeType || "audio/webm";
      const ext = type.includes("mp4") ? "mp4" : type.includes("ogg") ? "ogg" : "webm";
      setTake({ blob: new Blob(chunks, { type }), name: `recording.${ext}`, seconds, fromFile: false });
    }

    // What to tell the learner about a take of this length, and whether it is
    // a warning. Null length: a file whose length is not known yet.
    function verdict(seconds) {
      if (seconds == null) return ["Nghe lại bản ghi, rồi bấm nộp hoặc chọn file khác.", false];
      const s = Math.round(seconds);
      if (seconds < floorS()) {
        return [`Bản ghi ${s} giây, ngắn hơn ${floorS()} giây nên sẽ bị từ chối vì quá ngắn. Hãy ghi lại.`, true];
      }
      if (minS() > 0 && seconds < minS()) {
        return [`Bản ghi ${s} giây, ngắn hơn ${minS()} giây đề yêu cầu. Vẫn nộp được, nhưng nên ghi lại dài hơn.`, true];
      }
      if (seconds > maxS()) {
        return [`Bản ghi ${s} giây, dài hơn ${maxS()} giây đề yêu cầu. Nên ghi lại gọn hơn.`, true];
      }
      return [`Bản ghi ${s} giây. Nghe lại rồi bấm nộp, hoặc ghi lại.`, false];
    }

    function describeTake() {
      const c = current;
      const parts = [c.fromFile ? c.name : "Bản ghi vừa thu"];
      if (c.fromFile) parts.push(humanSize(c.blob.size));
      if (c.seconds != null) parts.push(clock(c.seconds));
      take.textContent = parts.join(" · ");
      const extra = opts.onTake ? opts.onTake(c) : "";
      note.textContent = extra || "";
      note.hidden = !extra;
      if (c.seconds != null) paint(c.seconds);
      const [text, warn] = verdict(c.seconds);
      verdictEl.textContent = text;
      verdictEl.classList.toggle("warn", warn);
      status.textContent = extra ? `${text} ${extra}` : text;
    }

    function setTake(next) {
      current = next;
      if (preview.src) URL.revokeObjectURL(preview.src);
      preview.src = URL.createObjectURL(next.blob);
      redo.textContent = next.fromFile ? "Chọn file khác" : "Ghi lại";
      setState("review");
      describeTake();
      // Focus the player, never the submit button: the space bar that just
      // stopped the recording would otherwise send it unheard.
      preview.focus();
    }

    function clearTake() {
      current = null;
      if (preview.src) URL.revokeObjectURL(preview.src);
      preview.removeAttribute("src");
      fileEl.value = "";
      note.hidden = true;
    }

    function toggle() {
      if (!canRecord || blocked) return;
      if (recorder && recorder.state === "recording") stop();
      else start();
    }

    button.addEventListener("click", toggle);
    redo.addEventListener("click", () => {
      const wasFile = current && current.fromFile;
      clearTake();
      paint(0);
      if (canRecord && !wasFile) {
        start();
        return;
      }
      setState("idle");
      upload.open = true;
      say("Chọn một file khác.");
      fileEl.click();
    });

    document.addEventListener("keydown", (e) => {
      if (e.code !== "Space" || e.repeat || !canRecord || blocked) return;
      if (state() !== "idle" && state() !== "recording") return;
      // Only while the recorder is on screen: the lesson builder hides it for
      // steps that take no model audio, and a hidden recorder must not listen.
      if (!root.getClientRects().length) return;
      const t = e.target;
      if (t && t.closest && t.closest("input, textarea, select, button, a, summary, audio, [contenteditable]")) return;
      e.preventDefault();
      toggle();
    });

    // ------------------------------------------------------------ upload
    function takeFile(file) {
      if (!file || blocked) return;
      if (recorder && recorder.state === "recording") stop();
      setTake({ blob: file, name: file.name, seconds: null, fromFile: true });
      // Read the length so the learner hears about a file that is too short or
      // too long before submitting it, not after.
      const probe = new Audio();
      probe.preload = "metadata";
      probe.addEventListener("loadedmetadata", () => {
        if (!current || current.blob !== file || !isFinite(probe.duration)) return;
        current.seconds = probe.duration;
        describeTake();
      });
      probe.src = preview.src;
    }

    fileEl.addEventListener("change", () => takeFile(fileEl.files[0]));
    let dragDepth = 0;
    ["dragenter", "dragover"].forEach((name) =>
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        if (name === "dragenter") dragDepth += 1;
        dropzone.classList.add("dragging");
      })
    );
    ["dragleave", "dragend"].forEach((name) =>
      dropzone.addEventListener(name, () => {
        dragDepth = Math.max(0, dragDepth - 1);
        if (!dragDepth) dropzone.classList.remove("dragging");
      })
    );
    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dragDepth = 0;
      dropzone.classList.remove("dragging");
      const files = e.dataTransfer && e.dataTransfer.files;
      if (files && files.length) takeFile(files[0]);
    });
    // A file dropped beside the zone must not navigate away from the page.
    window.addEventListener("dragover", (e) => e.preventDefault());
    window.addEventListener("drop", (e) => e.preventDefault());

    // ------------------------------------------------------------ submit
    // Listening on the form, not the button, also catches an implicit
    // submission, which would otherwise reload the page and lose the take.
    async function send(e) {
      e.preventDefault();
      if (!current || state() !== "review" || blocked) return;
      setState("submitting");
      try {
        await opts.onSubmit(current.blob, current.name);
      } finally {
        if (state() === "submitting") setState("review");
      }
    }
    if (form) form.addEventListener("submit", send);
    else submit.addEventListener("click", send);

    paintWindow();
    setState("idle");

    return {
      // The server says whether it can transcode browser recordings.
      enable(serverCanTranscode) {
        const reason = blockedReason(serverCanTranscode);
        canRecord = !reason;
        live.hidden = !canRecord;
        if (reason) {
          off.innerHTML = `<b>Không ghi âm trực tiếp được.</b> ${reason}`;
          off.hidden = false;
          upload.open = true;
          if (!blocked && state() === "idle") say("Chọn file ghi âm có sẵn ở ô bên dưới.");
        }
      },
      repaint: paintWindow,
      // Refuse both paths up front, for a page that must not take a recording
      // yet (no consent). The server refuses too; this saves a wasted minute.
      block(reason) {
        blocked = true;
        if (recorder && recorder.state === "recording") stop();
        button.disabled = true;
        fileEl.disabled = true;
        dropzone.classList.add("disabled");
        say(reason);
        setState(state());
      },
      done() {
        setState("submitted");
      },
      // Start recording now if the recorder is idle and allowed: the end of a
      // preparation countdown starts the answer, as in a test room (D028).
      // Returns false when it cannot (no microphone path, blocked, busy).
      startNow() {
        if (!canRecord || blocked || state() !== "idle") return false;
        start();
        return true;
      },
      canRecordLive: () => canRecord && !blocked,
      // Back to an empty recorder, for the next step of a lesson.
      reset() {
        if (recorder && recorder.state === "recording") stop();
        clearTake();
        paint(0);
        paintWindow();
        setState("idle");
        if (!blocked) say(canRecord ? "Bấm nút ghi âm hoặc nhấn phím cách để bắt đầu." : "Chọn file ghi âm có sẵn ở ô bên dưới.");
      },
    };
  };
})();
