// The product page's 3D (D031): the hero scene turns toward the pointer and
// cards marked data-tilt lean toward it, with a glare where it points.
//
// Decoration only. With reduced motion asked for, or on a touch screen where
// there is no pointer to follow, this does nothing and the page keeps its
// resting angles from style.css. It writes CSS custom properties and nothing
// else; every transform is in the stylesheet.
(() => {
  "use strict";

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");

  // 3D Parallax and Tilting (Only for devices with fine pointer and no reduced motion)
  if (!reduced.matches && finePointer.matches) {
    const hero = document.querySelector(".lp-hero");
    const scene = document.querySelector("[data-scene]");
  if (hero && scene) {
    const EASE = 0.08;
    let target = { x: 0, y: 0 };
    let now = { x: 0, y: 0 };
    let frame = 0;

    const step = () => {
      now.x += (target.x - now.x) * EASE;
      now.y += (target.y - now.y) * EASE;
      scene.style.setProperty("--px", now.x.toFixed(4));
      scene.style.setProperty("--py", now.y.toFixed(4));
      // D037: the terraces under the scene drift the other way, a little.
      hero.style.setProperty("--px", now.x.toFixed(4));
      hero.style.setProperty("--py", now.y.toFixed(4));
      const left = Math.abs(target.x - now.x) + Math.abs(target.y - now.y);
      frame = left > 0.0005 ? window.requestAnimationFrame(step) : 0;
    };
    const aim = (x, y) => {
      target = { x, y };
      if (!frame) frame = window.requestAnimationFrame(step);
    };

    hero.addEventListener("pointermove", (event) => {
      const box = hero.getBoundingClientRect();
      aim(
        ((event.clientX - box.left) / box.width) * 2 - 1,
        ((event.clientY - box.top) / box.height) * 2 - 1
      );
    });
    hero.addEventListener("pointerleave", () => aim(0, 0));
  }

  // A tilting card: the edge nearest the pointer comes forward, at most MAX
  // degrees -- enough to feel, not enough to look like a toy. Leaving the
  // card hands it back to the stylesheet, which eases it to its resting angle
  // (a mock-up rests tilted, a step card rests flat).
  const MAX = 5;
  for (const card of document.querySelectorAll("[data-tilt]")) {
    card.addEventListener("pointermove", (event) => {
      const box = card.getBoundingClientRect();
      const x = (event.clientX - box.left) / box.width;
      const y = (event.clientY - box.top) / box.height;
      card.classList.add("is-tilting");
      card.style.setProperty("--tilt-x", ((y - 0.5) * 2 * MAX).toFixed(2) + "deg");
      card.style.setProperty("--tilt-y", ((0.5 - x) * 2 * MAX).toFixed(2) + "deg");
      card.style.setProperty("--glare-x", (x * 100).toFixed(1) + "%");
      card.style.setProperty("--glare-y", (y * 100).toFixed(1) + "%");
    });
    card.addEventListener("pointerleave", () => {
      card.classList.remove("is-tilting");
      for (const name of ["--tilt-x", "--tilt-y", "--glare-x", "--glare-y"]) {
        card.style.removeProperty(name);
      }
    });
  }
}

  // Interactive Speech Diagnostic Studio Playground
  const studioTabs = document.querySelectorAll(".lp-tab");
  const wordsDisplay = document.getElementById("lp-words-display");
  const tooltipCard = document.getElementById("lp-word-tooltip");
  const latencyEl = document.getElementById("lp-hud-latency");
  const bandEl = document.getElementById("lp-hud-band");
  const scoreEl = document.getElementById("lp-hud-score");
  const fluencyEl = document.getElementById("lp-hud-fluency");
  const pauseEl = document.getElementById("lp-hud-pause");
  const demoTimeEl = document.getElementById("lp-demo-time");
  const demoTotalEl = document.getElementById("lp-demo-total");
  const demoSpeedEl = document.getElementById("lp-demo-speed");
  const playBtn = document.getElementById("lp-demo-play-btn");
  const wavesContainer = document.getElementById("lp-studio-waves");

  if (wordsDisplay) {
    const demoData = {
      a2: {
        audio: "/static/audio/demo_a2.mp3",
        duration: 3.5,
        total: "0:04",
        speed: "Tốc độ chuẩn bản ngữ 132 wpm",
        words: [
          { w: "I", start: 0.0, end: 0.25, status: "heard", ipa: "/aɪ/", acc: "98% Tự tin", note: "Phát âm chuẩn âm đơn" },
          { w: "like", start: 0.25, end: 0.65, status: "heard", ipa: "/laɪk/", acc: "95% Tự tin", note: "Âm đuôi /k/ rõ ràng" },
          { w: "my", start: 0.65, end: 0.95, status: "heard", ipa: "/maɪ/", acc: "99% Tự tin", note: "Chuẩn xác" },
          { w: "neighborhood", start: 0.95, end: 1.70, status: "heard hint", ipa: "/ˈneɪ.bə.hʊd/", acc: "94% Tự tin", note: "Trọng âm 1 chính xác" },
          { w: "because", start: 1.70, end: 2.15, status: "heard", ipa: "/bɪˈkɒz/", acc: "92% Tự tin", note: "Nối âm tự nhiên" },
          { w: "the", start: 2.15, end: 2.35, status: "heard", ipa: "/ðə/", acc: "90% Tự tin", note: "Âm /ð/ đạt chuẩn" },
          { w: "people", start: 2.35, end: 2.75, status: "heard", ipa: "/ˈpiː.pəl/", acc: "96% Tự tin", note: "Chuẩn xác" },
          { w: "are", start: 2.75, end: 2.95, status: "missed", ipa: "/ɑːr/", acc: "42% Nuốt âm", note: "Cần phát âm rõ động từ to-be" },
          { w: "friendly.", start: 2.95, end: 3.50, status: "unsure hint", ipa: "/ˈfrend.li/", acc: "68% Cần rèn", note: "Lưu ý trọng âm âm tiết 1" }
        ],
        band: "A2",
        score: "3.4",
        latency: "0.92",
        fluency: "74%",
        pause: "1.6"
      },
      b1: {
        audio: "/static/audio/demo_b1.mp3",
        duration: 4.9,
        total: "0:05",
        speed: "Tốc độ chuẩn bản ngữ 145 wpm",
        words: [
          { w: "Traveling", start: 0.0, end: 0.65, status: "heard", ipa: "/ˈtræv.əl.ɪŋ/", acc: "97% Tự tin", note: "Trọng âm đầu chuẩn xác" },
          { w: "abroad", start: 0.65, end: 1.15, status: "heard", ipa: "/əˈbrɔːd/", acc: "93% Tự tin", note: "Nguyên âm đôi chuẩn" },
          { w: "helps", start: 1.15, end: 1.60, status: "heard", ipa: "/helps/", acc: "96% Tự tin", note: "Âm gió /s/ đầy đủ" },
          { w: "students", start: 1.60, end: 2.20, status: "heard hint", ipa: "/ˈstjuː.dənts/", acc: "95% Tự tin", note: "Phát âm rõ cụm phụ âm" },
          { w: "develop", start: 2.20, end: 2.75, status: "heard", ipa: "/dɪˈvel.əp/", acc: "91% Tự tin", note: "Trọng âm rơi đúng âm 2" },
          { w: "independence", start: 2.75, end: 3.60, status: "heard hint", ipa: "/ˌɪn.dɪˈpen.dəns/", acc: "89% Tự tin", note: "Trọng âm thứ cấp chuẩn" },
          { w: "and", start: 3.60, end: 3.85, status: "heard", ipa: "/ænd/", acc: "94% Tự tin", note: "Nối âm trôi chảy" },
          { w: "cultural", start: 3.85, end: 4.35, status: "heard", ipa: "/ˈkʌl.tʃər.əl/", acc: "92% Tự tin", note: "Âm /tʃ/ chuẩn xác" },
          { w: "awareness.", start: 4.35, end: 4.92, status: "heard", ipa: "/əˈweə.nəs/", acc: "88% Tự tin", note: "Độ trôi chảy tốt" }
        ],
        band: "B1+",
        score: "4.8",
        latency: "1.18",
        fluency: "84%",
        pause: "1.1"
      },
      b2: {
        audio: "/static/audio/demo_b2.mp3",
        duration: 5.6,
        total: "0:06",
        speed: "Tốc độ chuẩn bản ngữ 158 wpm",
        words: [
          { w: "Technological", start: 0.0, end: 0.95, status: "heard hint", ipa: "/ˌtek.nəˈlɒdʒ.ɪ.kəl/", acc: "95% Tự tin", note: "Từ học thuật cao cấp chuẩn xác" },
          { w: "innovation", start: 0.95, end: 1.75, status: "heard", ipa: "/ˌɪn.əˈveɪ.ʃən/", acc: "96% Tự tin", note: "Ngữ điệu tự nhiên" },
          { w: "is", start: 1.75, end: 1.95, status: "heard", ipa: "/ɪz/", acc: "98% Tự tin", note: "Liên kết câu mượt" },
          { w: "profoundly", start: 1.95, end: 2.70, status: "heard hint", ipa: "/prəˈfaʊnd.li/", acc: "91% Tự tin", note: "Trọng âm chính xác" },
          { w: "transforming", start: 2.70, end: 3.45, status: "heard", ipa: "/trænsˈfɔː.mɪŋ/", acc: "94% Tự tin", note: "Nguyên âm dài chuẩn" },
          { w: "higher", start: 3.45, end: 3.90, status: "heard", ipa: "/ˈhaɪ.ər/", acc: "97% Tự tin", note: "Tốc độ nói lưu loát" },
          { w: "education", start: 3.90, end: 4.60, status: "heard", ipa: "/ˌedʒ.ʊˈkeɪ.ʃən/", acc: "96% Tự tin", note: "Khớp chuẩn CEFR B2" },
          { w: "paradigms.", start: 4.60, end: 5.57, status: "heard hint", ipa: "/ˈpær.ə.daɪmz/", acc: "93% Tự tin", note: "Phát âm chuẩn từ khó" }
        ],
        band: "B2",
        score: "5.5",
        latency: "1.34",
        fluency: "92%",
        pause: "0.6"
      }
    };

    let currentLevel = "b1";
    let wordSpans = [];
    const audio = new Audio();
    audio.preload = "auto";

    function formatTime(sec) {
      const s = Math.floor(sec || 0);
      const m = Math.floor(s / 60);
      const r = s % 60;
      return `${m}:${r < 10 ? "0" + r : r}`;
    }

    function pronounceWord(text) {
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
        const clean = text.replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g, "");
        const utterance = new SpeechSynthesisUtterance(clean);
        utterance.lang = "en-US";
        utterance.rate = 0.85;
        window.speechSynthesis.speak(utterance);
      }
    }

    function setPlayingUI(playing) {
      if (playBtn) playBtn.classList.toggle("is-playing", playing);
      if (wavesContainer) wavesContainer.classList.toggle("is-active", playing);
      if (!playing) {
        wordSpans.forEach((s) => s.classList.remove("is-speaking"));
      }
    }

    function renderLevel(levelKey) {
      if (!audio.paused) {
        audio.pause();
      }
      setPlayingUI(false);

      currentLevel = levelKey;
      const data = demoData[levelKey] || demoData.b1;
      audio.src = data.audio;
      audio.currentTime = 0;

      wordsDisplay.innerHTML = "";
      wordSpans = [];

      data.words.forEach((item) => {
        const span = document.createElement("span");
        span.className = "w " + item.status;
        span.textContent = item.w;
        span.tabIndex = 0;
        span.setAttribute("role", "button");
        span.setAttribute("aria-label", `Nghe phát âm từ ${item.w}`);
        span.title = "Bấm để nghe phát âm riêng từ này";

        const showTooltip = () => {
          tooltipCard.innerHTML = `<strong>${item.w}</strong> <span class="ipa">${item.ipa}</span> · <span class="acc">${item.acc}</span> — <em>${item.note}</em>`;
        };

        span.addEventListener("mouseenter", showTooltip);
        span.addEventListener("focus", showTooltip);
        span.addEventListener("click", () => {
          showTooltip();
          pronounceWord(item.w);
        });
        span.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            showTooltip();
            pronounceWord(item.w);
          }
        });

        wordsDisplay.appendChild(span);
        wordsDisplay.appendChild(document.createTextNode(" "));
        wordSpans.push(span);
      });

      if (data.words.length > 0) {
        const first = data.words[0];
        tooltipCard.innerHTML = `<strong>${first.w}</strong> <span class="ipa">${first.ipa}</span> · <span class="acc">${first.acc}</span> — <em>${first.note}</em>`;
      }

      if (latencyEl) latencyEl.textContent = data.latency;
      if (bandEl) bandEl.textContent = data.band;
      if (scoreEl) scoreEl.textContent = data.score;
      if (fluencyEl) fluencyEl.textContent = data.fluency;
      if (pauseEl) pauseEl.textContent = data.pause;
      if (demoTimeEl) demoTimeEl.textContent = "0:00";
      if (demoTotalEl) demoTotalEl.textContent = data.total;
      if (demoSpeedEl) demoSpeedEl.textContent = data.speed;
    }

    // Audio playback events
    audio.addEventListener("timeupdate", () => {
      const cur = audio.currentTime;
      if (demoTimeEl) demoTimeEl.textContent = formatTime(cur);

      const data = demoData[currentLevel] || demoData.b1;
      data.words.forEach((item, idx) => {
        const span = wordSpans[idx];
        if (!span) return;
        if (cur >= item.start && cur <= item.end) {
          span.classList.add("is-speaking");
          tooltipCard.innerHTML = `<strong>${item.w}</strong> <span class="ipa">${item.ipa}</span> · <span class="acc">${item.acc}</span> — <em>${item.note}</em>`;
        } else {
          span.classList.remove("is-speaking");
        }
      });
    });

    audio.addEventListener("ended", () => {
      setPlayingUI(false);
      audio.currentTime = 0;
      if (demoTimeEl) demoTimeEl.textContent = "0:00";
    });

    audio.addEventListener("pause", () => {
      setPlayingUI(false);
    });

    audio.addEventListener("play", () => {
      setPlayingUI(true);
    });

    // Waveform click to seek
    if (wavesContainer) {
      wavesContainer.style.cursor = "pointer";
      wavesContainer.title = "Bấm để tua đoạn âm thanh";
      wavesContainer.addEventListener("click", (e) => {
        const rect = wavesContainer.getBoundingClientRect();
        const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        const dur = audio.duration || (demoData[currentLevel] && demoData[currentLevel].duration) || 5;
        audio.currentTime = pct * dur;
        if (audio.paused) {
          audio.play().catch(() => {});
        }
      });
    }

    // Play button toggle
    if (playBtn) {
      playBtn.addEventListener("click", () => {
        if (audio.paused) {
          audio.play().catch((err) => {
            console.warn("Audio playback issue:", err);
            // Fallback: speak entire sentence with speech synthesis
            const data = demoData[currentLevel] || demoData.b1;
            const fullText = data.words.map((x) => x.w).join(" ");
            if ("speechSynthesis" in window) {
              window.speechSynthesis.cancel();
              const u = new SpeechSynthesisUtterance(fullText);
              u.lang = "en-US";
              u.rate = 0.9;
              u.onstart = () => setPlayingUI(true);
              u.onend = () => setPlayingUI(false);
              window.speechSynthesis.speak(u);
            }
          });
        } else {
          audio.pause();
        }
      });
    }

    // Tabs switching
    studioTabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        studioTabs.forEach((t) => {
          t.classList.remove("active");
          t.setAttribute("aria-selected", "false");
        });
        tab.classList.add("active");
        tab.setAttribute("aria-selected", "true");
        renderLevel(tab.getAttribute("data-level"));
      });
    });

    // Microphone speech recognition or interactive voice trial
    const micBtn = document.getElementById("lp-demo-mic-btn");
    let isListening = false;
    let recognition = null;

    if (micBtn) {
      const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRec) {
        try {
          recognition = new SpeechRec();
          recognition.continuous = false;
          recognition.interimResults = true;
          recognition.lang = "en-US";

          recognition.onstart = () => {
            isListening = true;
            micBtn.classList.add("is-recording");
            const spanText = micBtn.querySelector("span");
            if (spanText) spanText.textContent = "Đang nghe...";
            if (!audio.paused) audio.pause();
            if (tooltipCard) {
              tooltipCard.innerHTML = `<span style="color:#ef4444">●</span> <em>Đang lắng nghe giọng bạn... Hãy thử nói câu trên!</em>`;
            }
          };

          recognition.onresult = (event) => {
            const transcript = Array.from(event.results)
              .map((r) => r[0].transcript)
              .join("")
              .toLowerCase();
            const data = demoData[currentLevel] || demoData.b1;
            const spokenTokens = transcript.split(/\s+/).filter(Boolean);

            data.words.forEach((item, idx) => {
              const clean = item.w.toLowerCase().replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g, "");
              const span = wordSpans[idx];
              if (!span) return;
              if (spokenTokens.includes(clean)) {
                span.classList.add("is-speaking");
              }
            });
          };

          recognition.onend = () => {
            isListening = false;
            micBtn.classList.remove("is-recording");
            const spanText = micBtn.querySelector("span");
            if (spanText) spanText.textContent = "Thử nói";
            if (window.toast) {
              window.toast("Đã ghi nhận giọng đọc thử! Hệ thống đối sánh phát âm hoàn tất.", "ok");
            }
          };

          recognition.onerror = (e) => {
            isListening = false;
            micBtn.classList.remove("is-recording");
            const spanText = micBtn.querySelector("span");
            if (spanText) spanText.textContent = "Thử nói";
            if (e.error !== "no-speech" && window.toast) {
              window.toast("Microphone chưa sẵn sàng. Bạn có thể bấm vào từng từ để nghe phát âm mẫu!", "info");
            }
          };

          micBtn.addEventListener("click", () => {
            if (isListening) {
              recognition.stop();
            } else {
              try {
                recognition.start();
              } catch (err) {
                console.warn("Speech recognition start issue:", err);
              }
            }
          });
        } catch (err) {
          console.warn("Speech recognition init issue:", err);
        }
      } else {
        micBtn.addEventListener("click", () => {
          if (!audio.paused) audio.pause();
          micBtn.classList.add("is-recording");
          const spanText = micBtn.querySelector("span");
          if (spanText) spanText.textContent = "Mô phỏng...";
          const data = demoData[currentLevel] || demoData.b1;
          let idx = 0;
          const timer = setInterval(() => {
            if (idx < wordSpans.length) {
              wordSpans.forEach((s) => s.classList.remove("is-speaking"));
              wordSpans[idx].classList.add("is-speaking");
              const item = data.words[idx];
              tooltipCard.innerHTML = `<strong>${item.w}</strong> <span class="ipa">${item.ipa}</span> · <span class="acc">${item.acc}</span> — <em>${item.note}</em>`;
              idx++;
            } else {
              clearInterval(timer);
              wordSpans.forEach((s) => s.classList.remove("is-speaking"));
              micBtn.classList.remove("is-recording");
              if (spanText) spanText.textContent = "Thử nói";
              if (window.toast) {
                window.toast("Đã hoàn tất phân tích mẫu câu trực quan!", "ok");
              }
            }
          }, 450);
        });
      }
    }

    // Mini-players in steps and float mock card
    const stepDemoPlayer = document.getElementById("lp-step-demo-player");
    const mockFloatPlayer = document.getElementById("lp-mock-float-player");
    const miniAudio = new Audio();
    miniAudio.preload = "auto";

    function setupMiniPlayer(el, audioSrc) {
      if (!el) return;
      el.addEventListener("click", () => {
        if (miniAudio.src.includes(audioSrc) && !miniAudio.paused) {
          miniAudio.pause();
          el.classList.remove("is-playing");
        } else {
          if (!audio.paused) audio.pause();
          if (stepDemoPlayer) stepDemoPlayer.classList.remove("is-playing");
          if (mockFloatPlayer) mockFloatPlayer.classList.remove("is-playing");

          miniAudio.src = audioSrc;
          miniAudio.currentTime = 0;
          miniAudio.play().then(() => {
            el.classList.add("is-playing");
          }).catch(() => {
            if ("speechSynthesis" in window) {
              window.speechSynthesis.cancel();
              const u = new SpeechSynthesisUtterance("I like my neighborhood because the people are friendly.");
              u.lang = "en-US";
              u.onstart = () => el.classList.add("is-playing");
              u.onend = () => el.classList.remove("is-playing");
              window.speechSynthesis.speak(u);
            }
          });
        }
      });

      el.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          el.click();
        }
      });
    }

    miniAudio.addEventListener("ended", () => {
      if (stepDemoPlayer) stepDemoPlayer.classList.remove("is-playing");
      if (mockFloatPlayer) mockFloatPlayer.classList.remove("is-playing");
    });
    miniAudio.addEventListener("pause", () => {
      if (stepDemoPlayer) stepDemoPlayer.classList.remove("is-playing");
      if (mockFloatPlayer) mockFloatPlayer.classList.remove("is-playing");
    });

    setupMiniPlayer(stepDemoPlayer, "/static/audio/demo_a2.mp3");
    setupMiniPlayer(mockFloatPlayer, "/static/audio/demo_b2.mp3");

    // Initialize with B1
    renderLevel("b1");
  }
})();
