// Listen, then say it after the voice (D070): shadowing the upgraded answer.
//
// The voice is the browser's own speech synthesis, so nothing is sent
// anywhere and nothing is paid for; a browser without an English voice gets
// no player and a sentence saying why. "Nhại từng câu" reads one sentence,
// then waits about as long as that sentence took (plus a little) for the
// learner to say it, then reads the next one. Nothing records or judges the
// learner here -- "Nói lại đề này" does that.
(function () {
  const synth = window.speechSynthesis;
  const escapeHtml = window.escapeHtml;
  const GAP_FACTOR = 1.3; // the pause after a sentence, relative to its reading time
  const MIN_GAP_MS = 1500;

  function englishVoice() {
    if (!synth) return null;
    const voices = synth.getVoices().filter((v) => /^en[-_]/i.test(v.lang));
    return (
      voices.find((v) => /en[-_]US/i.test(v.lang) && v.localService) ||
      voices.find((v) => /en[-_]US/i.test(v.lang)) ||
      voices[0] ||
      null
    );
  }

  // Voices load late in Chrome: wait for them once, at most a second.
  function voiceReady() {
    return new Promise((resolve) => {
      if (!synth) return resolve(null);
      const now = englishVoice();
      if (now) return resolve(now);
      const done = () => resolve(englishVoice());
      synth.addEventListener("voiceschanged", done, { once: true });
      setTimeout(done, 1000);
    });
  }

  function sentencesOf(text) {
    return (text || "")
      .split(/(?<=[.!?])\s+/)
      .map((s) => s.trim())
      .filter(Boolean);
  }

  function say(text, voice, rate) {
    return new Promise((resolve) => {
      const u = new SpeechSynthesisUtterance(text);
      u.voice = voice;
      u.lang = voice.lang;
      u.rate = rate;
      const started = performance.now();
      u.onend = () => resolve(performance.now() - started);
      u.onerror = () => resolve(0);
      synth.speak(u);
    });
  }

  // A play button for one phrase or sentence; nothing when there is no voice.
  window.speakButton = function (text, label) {
    if (!synth) return "";
    return (
      `<button type="button" class="button secondary small speak-one" data-say="${escapeHtml(text)}">` +
      `${escapeHtml(label || "Nghe")}</button>`
    );
  };
  document.addEventListener("click", async (e) => {
    const b = e.target.closest(".speak-one");
    if (!b) return;
    const voice = await voiceReady();
    if (!voice) return window.toast("Trình duyệt này không có giọng đọc tiếng Anh.", "error");
    synth.cancel();
    say(b.dataset.say, voice, 0.9);
  });

  window.setUpShadowing = async function (host, text) {
    const parts = sentencesOf(text);
    if (!host || !parts.length) return;
    const voice = await voiceReady();
    if (!voice) {
      // The text itself still shows: the player is extra, the answer is not.
      host.innerHTML =
        `<p class="upgrade-text" lang="en">${escapeHtml(text)}</p>` +
        '<p class="muted small-note">Trình duyệt này không có giọng đọc tiếng Anh nên chưa nghe được bản này. ' +
        "Thử Chrome, Edge hoặc Safari.</p>";
      return;
    }
    host.classList.add("shadow");
    host.innerHTML =
      '<div class="button-row shadow-controls">' +
      '<button type="button" class="button secondary small" data-act="listen">Nghe cả bài</button>' +
      '<button type="button" class="button small" data-act="shadow">Nhại từng câu</button>' +
      '<button type="button" class="button secondary small" data-act="stop" hidden>Dừng</button>' +
      '<label class="shadow-rate">Tốc độ <select><option value="0.75">chậm</option>' +
      '<option value="0.9" selected>vừa</option><option value="1">thường</option></select></label>' +
      "</div>" +
      '<p class="shadow-status muted small-note" aria-live="polite"></p>' +
      `<ol class="shadow-lines" lang="en">${parts.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ol>` +
      `<p class="muted small-note">Giọng đọc của trình duyệt (${escapeHtml(voice.name)}), không gửi gì đi. ` +
      "Nhại theo: nghe một câu, nói lại ngay trong khoảng lặng, bắt chước nhịp và chỗ ngắt.</p>";
    const lines = host.querySelectorAll(".shadow-lines li");
    const status = host.querySelector(".shadow-status");
    const stopButton = host.querySelector('[data-act="stop"]');
    const rateOf = () => Number(host.querySelector("select").value) || 0.9;
    let run = 0; // bumped on every start and stop: an older loop sees it and quits

    const mark = (i, kind) =>
      lines.forEach((li, j) => {
        li.classList.toggle("is-now", j === i && kind === "now");
        li.classList.toggle("is-yours", j === i && kind === "yours");
      });

    function stop() {
      run += 1;
      synth.cancel();
      mark(-1);
      status.textContent = "";
      stopButton.hidden = true;
    }

    async function play(shadowing) {
      stop();
      const mine = run;
      stopButton.hidden = false;
      for (let i = 0; i < parts.length && mine === run; i += 1) {
        mark(i, "now");
        status.textContent = `Câu ${i + 1}/${parts.length}: nghe`;
        const took = await say(parts[i], voice, rateOf());
        if (mine !== run) return;
        if (shadowing) {
          mark(i, "yours");
          status.textContent = `Câu ${i + 1}/${parts.length}: đến lượt bạn nói`;
          await new Promise((r) => setTimeout(r, Math.max(MIN_GAP_MS, took * GAP_FACTOR)));
        }
      }
      if (mine === run) {
        stop();
        status.textContent = shadowing ? "Xong. Giờ thử nói cả bài bằng lời của bạn." : "";
      }
    }

    host.addEventListener("click", (e) => {
      const act = e.target.closest("[data-act]");
      if (!act) return;
      if (act.dataset.act === "stop") stop();
      else play(act.dataset.act === "shadow");
    });
    window.addEventListener("pagehide", stop);
  };
})();
