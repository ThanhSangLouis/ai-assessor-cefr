// Result report screen. See docs/web/SPEC_WEB.md section M4.
//
// HONESTY NOTE, and the reason this screen is shaped the way it is
// --------------------------------------------------------------------------
// The scorer is trained on ONE overall label per response: the Speak & Improve
// corpus carries no per-criterion labels. `RidgeScorer.score` therefore writes
// `round(overall, 2)` into all five CriterionScore rows -- they are the same
// number five times, not five independent judgements. The old screen printed
// them as a five-row table with a "Do tin cay" column, which read as five
// separate assessments each backed by its own certainty. That was untrue in
// two ways at once:
//
//   1. there is only one estimate, and
//   2. `confidence` is not a confidence. It is the fraction of that
//      criterion's features the pipeline managed to compute. 19 of 19 features
//      present gives 100% even when the prediction is completely wrong.
//
// So: one overall score is the headline, the per-criterion numbers are not
// printed at all, and what used to be called "Do tin cay" is now labelled
// "Day du du lieu" with a sentence saying what it actually measures. What is
// kept is the part that is genuinely measured and genuinely useful to a
// learner -- pauses, fillers, words the recogniser could not hear, vocabulary
// range -- shown as evidence with a timestamp.
const reportEl = document.getElementById("evidence");
const ID = reportEl.dataset.responseId;
// The QC limits in force, rendered by the server from active_qc().
const LIMITS = {
  minSeconds: Number(reportEl.dataset.minSeconds) || 20,
  maxSeconds: Number(reportEl.dataset.maxSeconds) || 300,
  maxMib: Number(reportEl.dataset.maxMib) || 25,
};
const escapeHtml = window.escapeHtml;
const mmss = window.ui.mmss;
const CRITERION_NAMES = window.ui.CRITERION_NAMES;
const isStudent = document.body.classList.contains("role-student");

// What the pipeline actually measures for each aspect. Mirrors
// CRITERION_FEATURES in aicefr/scoring/scorer.py. Written out in plain words so
// the reader can judge for themselves how much weight the evidence deserves.
const ASPECT_MEASURES = {
  range: "Số từ khác nhau, độ đa dạng từ vựng, độ dài trung bình của từ.",
  accuracy: "Mức độ máy nghe rõ từng từ.",
  fluency: "Tốc độ nói, số lần và độ dài các quãng ngừng.",
  coherence:
    "Số kiểu từ nối khác nhau trong bản chép lời. Mức đủ dữ liệu tính theo tổng số từ, " +
    "độ dài các đoạn nói liền mạch và tổng thời lượng.",
  phonology: "Mức độ máy nghe rõ và tỷ lệ im lặng trong bản ghi.",
};

// Aspects whose measurements are only an indirect proxy. Saying so beats
// letting the reader assume the machine judged their grammar or their accent.
const ASPECT_CAVEATS = {
  accuracy:
    "Đây là mức tự tin của bộ nhận dạng tiếng nói, không phải phép kiểm tra ngữ pháp. " +
    "Máy nghe không rõ có thể do phát âm, mà cũng có thể do micro hoặc tiếng ồn.",
  phonology:
    "Hệ thống không chấm phát âm theo âm vị. Chỉ số này suy ra từ việc máy nghe rõ đến đâu, " +
    "nên chịu ảnh hưởng của chất lượng bản ghi.",
  coherence:
    "Máy chỉ đếm từ nối, không biết từ nối có nối đúng ý hay cả bài có được sắp xếp " +
    "rõ ràng không.",
};

const EVIDENCE_KIND_NAMES = {
  pause: "ngừng dài",
  filler: "từ ngập ngừng",
  low_confidence_word: "từ máy nghe không rõ",
  lexical: "vốn từ",
  connector: "từ nối",
};

// "Day du du lieu": the share of the measurements for one aspect that the
// pipeline could actually compute on this recording. Deliberately NOT called a
// confidence, and deliberately not rounded up into a reassuring word.
function completeness(c) {
  if (c == null) return { percent: null, label: "Không đo được", full: false };
  const percent = Math.round(c * 100);
  if (percent >= 100) return { percent, label: "Đủ phép đo", full: true };
  return { percent, label: "Thiếu phép đo", full: false };
}

fetch(`/api/v1/responses/${ID}`)
  .then((r) => {
    if (window.redirectToLoginIfExpired(r)) return null;
    return r.json();
  })
  .then((d) => {
    if (d === null) return;
    window.clearBusy(reportEl);
    if (d.detail) {
      reportEl.innerHTML = notFoundState();
      return;
    }
    // Not scored yet, so send the user back to the progress screen.
    if (d.status === "QUEUED" || d.status === "RUNNING") {
      location.href = `/progress/${ID}`;
      return;
    }
    reportEl.innerHTML = buildReport(d);
    wirePlayer();
    wireKaraoke(d);
    loadCoach();
    // D056: guided listening adds its card once the player is on the page.
    document.dispatchEvent(new CustomEvent("report:ready"));
  })
  .catch(() => {
    window.clearBusy(reportEl);
    reportEl.innerHTML = offlineState();
    window.toast("Không kết nối được máy chủ.", "error");
  });

function notFoundState() {
  return (
    '<div class="empty-state"><div class="empty-mark" aria-hidden="true">∅</div>' +
    "<h2>Không tìm thấy bài này</h2>" +
    "<p>Mã bài có thể sai, hoặc bài thuộc về tài khoản khác. " +
    "Bạn chỉ xem được báo cáo của chính mình.</p>" +
    '<div class="button-row"><a class="button" href="/my-responses">Xem bài của tôi</a>' +
    '<a class="button secondary" href="/">Nộp bài mới</a></div></div>'
  );
}

function offlineState() {
  return (
    '<div class="empty-state"><div class="empty-mark" aria-hidden="true">⚠</div>' +
    "<h2>Không kết nối được máy chủ</h2>" +
    "<p>Báo cáo vẫn được lưu, chưa mất đi đâu. Hãy tải lại trang sau ít phút.</p>" +
    '<div class="button-row"><a class="button" href="">Tải lại trang</a></div></div>'
  );
}

// The report as a run of cards, in the order a learner asks: what did I get,
// what do I do next, what is that based on, and only then how it was measured.
// It used to be one card four screens long, with the next step in the middle
// and the evidence below two explanatory tables.
function buildReport(d) {
  const a = d.assessment || {};
  const rejected = d.status === "REJECTED" || d.status === "FAILED";
  const head =
    '<div class="card-head"><h2 id="result-h">Kết quả</h2>' +
    `${window.ui.statusBadge(d.status)}</div>`;

  // AC-09.2: when a response is rejected, the band and the score must NOT be
  // shown in any form whatsoever. That is why this branch comes before
  // everything else.
  if (rejected) return section("report-summary", "result-h", head + rejectionBlock(d)) + detailCard(d, a, true);

  // D040: in the score-only arm of the feedback study the server sends the
  // score and nothing else; say why the rest is missing instead of drawing
  // empty sections.
  if (d.feedback_withheld) {
    return section("report-summary", "result-h", head + scoreBlock(d, a) + withheldBlock()) + detailCard(d, a, false);
  }

  // D068: four parts. What the learner came for -- the result, what to work
  // on, the recording -- stays open; everything about how the machine got
  // there is one fold at the foot.
  return (
    section("report-summary", "result-h", head + scoreBlock(d, a) + nextStepBlock(a, d)) +
    '<section class="card anchor-target" id="report-coach" aria-labelledby="coach-h" hidden></section>' +
    commentsCard(a) +
    evidenceCard(d, a) +
    detailCard(d, a, false)
  );
}

function withheldBlock() {
  return (
    '<div class="notice" id="feedback-withheld"><b>Bạn đang ở nhóm “Chỉ điểm” của thực nghiệm phản hồi.</b> ' +
    "Trong thời gian thực nghiệm, báo cáo chỉ hiện điểm và mức. Bạn có thể rời thực nghiệm bất cứ lúc nào " +
    'ở trang <a href="/my-progress#study">Tiến độ của tôi</a> để xem lại đầy đủ nhận xét.</div>'
  );
}

function section(id, labelledBy, inner) {
  return `<section class="card anchor-target" id="${id}" aria-labelledby="${labelledBy}">${inner}</section>`;
}

// The next step sits in the result card itself. "Khía cạnh nên luyện trước"
// used to be a line of plain text under a fourteen-row table; it is now a
// button that opens the practice task for that aspect at this band.
function nextStepBlock(a, d) {
  const weak = a.weakest_criteria || [];
  let h = "";
  if (weak.length) {
    h +=
      '<p class="next-step-line"><b>Khía cạnh nên luyện trước:</b> ' +
      weak.map((c) => escapeHtml(CRITERION_NAMES[c] || c)).join(", ") +
      ". <span class=\"muted\">Xác định bằng vị trí các phép đo so với bài nói tham chiếu, " +
      "không phải điểm riêng của từng khía cạnh.</span></p>";
  }
  if (!isStudent) return h ? `<div class="next-step">${h}</div>` : "";
  // The lesson path picks its next lesson from this same weakest aspect (D068).
  const practise = weak.length
    ? `<a class="button" href="/practice">Luyện ${escapeHtml((CRITERION_NAMES[weak[0]] || "").toLowerCase())} theo lộ trình</a>`
    : '<a class="button" href="/practice">Mở trang luyện tập</a>';
  // D069: the same task again, three times, shorter each time.
  const scored = d && (d.status === "COMPLETED" || d.status === "REVIEW_REQUIRED");
  const retell = scored
    ? `<a class="button secondary" href="/retell/${encodeURIComponent(ID)}">Nói lại đề này</a>`
    : "";
  return (
    `<div class="next-step">${h}<div class="button-row">${practise}${retell}` +
    '<a class="button secondary" href="/">Nộp bài mới</a>' +
    '<a class="button secondary" href="/my-progress">Xem tiến độ</a></div></div>'
  );
}

function commentsCard(a) {
  const body = commentBlock(a) + priorityBlock(a);
  if (!body) return "";
  return section(
    "report-comments",
    "comments-h",
    '<h2 id="comments-h">Nhận xét và gợi ý luyện tập</h2>' + body
  );
}

// The recording, the evidence cards that seek it and the transcript, in one
// card with the player pinned to its top: clicking a piece of evidence plays
// it without the player scrolling out of sight.
function evidenceCard(d, a) {
  return section(
    "report-evidence",
    "evidence-h",
    '<div class="sticky-player"><h2 id="evidence-h">Nghe lại và xem bằng chứng</h2>' +
      '<audio id="phat" controls preload="metadata" ' +
      `src="/api/v1/responses/${encodeURIComponent(ID)}/audio"></audio></div>` +
      transcriptBlock(d) +
      foldedEvidence(a)
  );
}

// The evidence cards seek the player above, so they stay in this card, folded:
// the transcript already marks the same moments.
function foldedEvidence(a) {
  // The fold's summary is the heading; drop the block's own.
  const body = evidenceBlock(a).replace(/^<h3[^>]*>[^<]*<\/h3>/, "");
  const n = (a.evidence || []).length;
  return `<details class="fold" id="report-evidence-list"><summary>Bằng chứng trên bản ghi${n ? ` (${n})` : ""}</summary>${body}</details>`;
}

// FR-27: the provenance fields appear at the foot of every report. Folded,
// because the reader who needs them knows to open them, and printing opens
// every fold. Open from the start on a rejected response: there the audio
// quality table is the explanation.
function detailCard(d, a, open) {
  return (
    `<details class="card anchor-target detail-card" id="report-detail"${open ? " open" : ""}>` +
    "<summary>Chi tiết: các khía cạnh được đo, chất lượng bản ghi, nguồn gốc kết quả</summary>" +
    (open ? "" : `<div id="report-aspects">${aspectBlock(a)}${indicatorBlock(a)}</div>` + windowBlock(a)) +
    qualityBlock(d) +
    provenanceBlock(d, a) +
    "</details>"
  );
}

function rejectionBlock(d) {
  const reasons = (d.reasons || [])
    .map((r) => escapeHtml(HINTS[r] || window.ui.reasonName(r)))
    .join(" ");
  const again = isStudent
    ? '<div class="button-row"><a class="button" href="/">Ghi âm lại và nộp bài mới</a></div>'
    : "";
  return (
    '<div class="notice notice-danger"><b>Bản ghi chưa dùng được.</b> ' +
    `${reasons} Hệ thống không chấm điểm cho bài này.</div>` +
    again
  );
}

// Reason codes written out in Vietnamese for students to read. FR-09 and FR-28
// require saying which measure went over which threshold and how to fix it,
// instead of showing a bare technical code.
const HINTS = {
  AUDIO_TOO_SHORT:
    `Bài nói ngắn hơn ${LIMITS.minSeconds} giây. Hãy nói dài hơn, ` +
    "khoảng 30 giây trở lên để chấm ổn định.",
  AUDIO_TOO_LONG: `Bài nói dài hơn ${LIMITS.maxSeconds} giây. Hãy rút gọn lại.`,
  AUDIO_TOO_LARGE: `File vượt quá ${LIMITS.maxMib} MiB.`,
  WRONG_SAMPLE_RATE: "File không ở tần số 16 kHz. Hãy xuất lại đúng định dạng.",
  HIGH_SILENCE_RATIO: "Bản ghi có quá nhiều khoảng lặng. Hãy thu ở nơi yên tĩnh và nói liên tục hơn.",
  CLIPPING_DETECTED: "Âm thu quá to nên bị méo. Hãy để micro xa miệng hơn hoặc giảm mức thu.",
  LOW_SNR: "Tiếng ồn nền lấn át giọng nói. Hãy thu ở nơi yên tĩnh hơn.",
  ASR_FAILED: "Hệ thống không nhận dạng được bản ghi này.",
  ASR_EMPTY_TRANSCRIPT: "Không nghe được lời nói nào trong bản ghi.",
  PROCESSING_INTERRUPTED: "Quá trình xử lý bị gián đoạn. Hãy nộp lại bài.",
  LANGUAGE_NOT_ENGLISH:
    "Bản ghi có vẻ không phải tiếng Anh nên hệ thống không chấm. Giảng viên sẽ nghe lại.",
};

// Say which measurement fell outside what the model can handle, and what to do
// about it.
//
// "Not enough reliable evidence" is true but useless: a student cannot act on
// it. The commonest cause by far is a recording longer than anything the model
// was trained on, and that has an obvious remedy -- but only if somebody says so.
const OUT_OF_RANGE_TEXT = {
  total_dur: (it) =>
    `Bài dài <b>${Math.round(it.value)} giây</b>. Hệ thống chỉ chấm được bài khoảng ` +
    `${Math.round(it.trained_low)}–${Math.round(it.trained_high)} giây ` +
    `(tối đa ${Math.round(it.accepted_high)} giây). Hãy ghi lại ngắn gọn hơn.`,
  vad_speech_sec: (it) =>
    `Thời lượng nói thực tế <b>${Math.round(it.value)} giây</b>, dài hơn mức hệ thống ` +
    `chấm được (tối đa khoảng ${Math.round(it.accepted_high)} giây).`,
  n_words: (it) =>
    `Bài có <b>${Math.round(it.value)} từ</b>, ngoài khoảng ` +
    `${Math.round(it.trained_low)}–${Math.round(it.trained_high)} từ mà hệ thống chấm được.`,
  words_per_sec: (it) =>
    `Tốc độ nói <b>${it.value.toFixed(2)} từ/giây</b>, ngoài khoảng ` +
    `${it.trained_low.toFixed(2)}–${it.trained_high.toFixed(2)} mà hệ thống chấm được.`,
};

function whyNotScored(d, a) {
  const items = a.out_of_range || [];
  const reasons = d.reasons || [];
  let h = "";

  if (items.length) {
    h +=
      '<div class="notice"><b>Vì sao chưa chấm được.</b><ul>' +
      items
        .map((it) => {
          const line = OUT_OF_RANGE_TEXT[it.feature];
          return `<li>${
            line
              ? line(it)
              : `Phép đo <code>${escapeHtml(it.feature)}</code> = ${it.value}, ngoài khoảng ` +
                `${it.trained_low}–${it.trained_high}.`
          }</li>`;
        })
        .join("") +
      "</ul></div>";
  }

  // Bai khong phai tieng Anh khong bi tu choi ma chuyen giang vien (REVIEW_REQUIRED),
  // nen di qua day chu khong qua rejectionBlock -- phai noi ro ly do o day.
  if (reasons.includes("LANGUAGE_NOT_ENGLISH")) {
    h += `<div class="notice">${escapeHtml(HINTS.LANGUAGE_NOT_ENGLISH)}</div>`;
  }
  if (reasons.includes("ASR_HALLUCINATION")) {
    h +=
      '<div class="notice">Bộ nhận dạng tiếng nói lặp lại một từ nhiều lần bất thường — ' +
      "thường xảy ra khi bản ghi có đoạn im lặng dài ở cuối. Phần lặp đã được cắt bỏ, " +
      "nhưng bản chép lời có thể chưa đầy đủ.</div>";
  }
  if (reasons.includes("ASR_VERSION_MISMATCH")) {
    h +=
      '<div class="notice">Hệ nhận dạng đang chạy khác với hệ mà mô hình được huấn luyện, ' +
      "nên điểm có thể lệch. Kết quả cần giảng viên xác nhận.</div>";
  }
  return h;
}

// Trust Layer (D022): khoảng điểm có bảo đảm thống kê. Khoảng chạm hơn một
// band nghĩa là máy không đủ căn cứ để chọn band -- nói thẳng ra, đừng giấu.
function intervalBlock(a) {
  const iv = a.interval;
  if (!iv) return "";
  const pct = Math.round(iv.coverage * 100);
  const bands = (iv.band_set || []).map((b) => escapeHtml(b)).join(", ");
  let h =
    '<p class="interval-line">Khoảng tin cậy ' + pct + "%: <b>" +
    iv.low.toFixed(2) + " – " + iv.high.toFixed(2) + "</b> (band có thể: " + bands + ").";
  if ((iv.band_set || []).length > 1) {
    h += " Khoảng này chạm hơn một band, nên band cuối cùng do giảng viên quyết định.";
  }
  return h + "</p>";
}

// Cờ lạc đề / đọc lại đề: điểm vẫn giữ nguyên, chỉ báo để giảng viên nghe lại.
function flagBlock(d) {
  const reasons = d.reasons || [];
  let h = "";
  if (reasons.includes("OFF_TOPIC_SUSPECTED")) {
    h +=
      '<div class="notice">Bài nói có vẻ <b>chưa bám đề</b>. Điểm không bị trừ; ' +
      "giảng viên sẽ nghe lại để xác nhận.</div>";
  }
  if (reasons.includes("PROMPT_COPY_SUSPECTED")) {
    h +=
      '<div class="notice">Một phần lớn bài nói <b>trùng nguyên văn với đề bài</b>. ' +
      "Hãy trả lời bằng lời của bạn. Giảng viên sẽ nghe lại để xác nhận.</div>";
  }
  return h;
}

// D031, D059: where the estimate stands among the six bands, drawn as the blocks
// of the product's mark. The estimated band takes the accent colour; a band
// the confidence interval also reaches is a shade darker than the rest.
// Decorative: the band is written beside it.
function bandPodium(a) {
  const reach = new Set((a.interval && a.interval.band_set) || []);
  const heights = { A1: 34, A2: 46, B1: 58, B2: 70, C1: 82, C2: 94 };
  return window.ui.cubes(
    Object.keys(heights).map((b) => ({
      label: b,
      h: heights[b],
      cls: b === a.overall_band ? "is-band" : reach.has(b) ? "is-possible" : "is-dim",
    })),
    "band-podium"
  );
}

// ONE overall score. There is no second, third or fifth number to show.
function scoreBlock(d, a) {
  if (a.overall_0_6 == null) {
    return (
      '<div class="notice">Hệ thống <b>chưa chấm</b> bài này vì không đủ căn cứ tin cậy. ' +
      "Bài đã được chuyển cho giảng viên xem lại. Phần bằng chứng bên dưới vẫn dùng được " +
      "để tự luyện.</div>" +
      whyNotScored(d, a)
    );
  }

  let h = '<div class="score-panel">';
  h += `<div class="score-figure">
      <span class="score">${a.overall_0_6.toFixed(2)}</span>
      <span class="score-scale">trên thang 1 – 6</span>
    </div>`;
  h += bandPodium(a);
  h += '<div class="score-meta">';
  h += `<span class="score-band">${escapeHtml(a.overall_band)}</span>`;
  // FR-21: the "estimate" label goes with every report, it must never be missing.
  h += `<p class="score-caption">
      Đây là <b>một ước lượng tổng thể</b> cho cả bài nói, do mô hình đưa ra từ các phép đo
      trên bản ghi. Kết quả ước lượng — không phải chứng chỉ CEFR.
    </p>`;
  // D028: what the band describes, and what the machine measured of it.
  h += '<a class="band-help" href="/bands">Band này nghĩa là gì, máy đo được những gì?</a>';
  h += "</div></div>";
  h += intervalBlock(a);
  h += flagBlock(d);

  // Cảnh báo chưa hiệu chuẩn. Việc ĐỌC `calibration_version` để quyết định
  // đã hiệu chuẩn hay chưa nằm ở `Assessment.is_calibrated` phía máy chủ —
  // trước đây biểu thức chính quy này là bản sao thứ hai của cùng một luật.
  const cal = a.calibration_version || "";
  if (!a.is_calibrated && !a.interval) {
    h +=
      '<p class="muted" style="margin-top:var(--sp-3)">Mô hình <b>chưa được hiệu chuẩn</b> ' +
      "(<code>" + escapeHtml(cal || "chưa có") + "</code>), nên sai số quanh con số này chưa " +
      "được định lượng. Hãy đọc điểm như một chỉ dấu về mức độ, không phải một phép đo chính xác.</p>";
  }

  if (!a.teacher_verified) {
    h +=
      '<div class="notice" style="margin-top:var(--sp-4)">Đây <b>chưa phải kết quả cuối</b>. ' +
      "Giảng viên là người xác nhận.</div>";
  }
  return h;
}

// Long recordings: what was actually scored, and how the parts compared.
//
// The model was fitted on responses of 26.7-60.7 seconds. A five-minute talk is
// scored by cutting it into windows the model can handle and taking the median,
// which is a defensible rule but an UNMEASURED one -- no study says a median of
// window scores predicts a rater's judgement of the whole. So the screen never
// shows the aggregated number on its own: it shows where each window fell, what
// each one got, and how far apart they were, because a teacher's first question
// is whether the parts agreed with each other or the speaker changed halfway.
//
// `window_spread` is the number that carries the warning. Two windows agreeing
// to within 0.2 says the median is standing on something. Windows 1.5 apart say
// the single figure above is hiding two different performances, and the reader
// should distrust it rather than round it off.
const SPREAD_DISAGREE = 0.8;

function windowBlock(a) {
  const ws = a.windows || [];
  if (ws.length < 2) return "";

  const scored = ws.filter((w) => w.overall_0_6 != null);
  const spread = a.window_spread;
  const total = ws[ws.length - 1].end_s || 0;

  let h = '<h3 class="block-title">Bài dài được chấm theo từng đoạn</h3>';
  h +=
    '<div class="notice notice-warn"><b>Điểm tạm, chưa kiểm định.</b> ' +
    `Bản ghi dài ${Math.round(total)} giây, dài hơn mọi bài mà mô hình từng được huấn luyện. ` +
    `Hệ thống cắt thành ${ws.length} đoạn nằm trong tầm mô hình chấm được, chấm riêng từng ` +
    "đoạn rồi lấy <b>trung vị</b>. Cách gộp này là một quy tắc có lý lẽ nhưng " +
    "<b>chưa được kiểm định trên dữ liệu</b>, nên bài luôn được chuyển cho giảng viên. " +
    "Muốn có điểm chấm trực tiếp thì nộp bài ngắn hơn.</div>";

  // The strip is laid out to scale: a reader can see at a glance that the
  // windows tile the whole recording without gaps, which is the property that
  // stops a speaker losing a sentence at a boundary.
  h += '<div class="window-strip" role="list">';
  for (const w of ws) {
    const width = total ? ((w.end_s - w.start_s) / total) * 100 : 100 / ws.length;
    const label =
      w.overall_0_6 == null ? "chưa chấm được" : `${w.overall_0_6.toFixed(2)} · ${w.band}`;
    h +=
      `<div class="window-chunk${w.overall_0_6 == null ? " unscored" : ""}" role="listitem"` +
      ` style="flex:0 0 ${width.toFixed(2)}%"` +
      ` title="Đoạn ${w.index + 1}: ${mmss(w.start_s)}–${mmss(w.end_s)}">` +
      `<b>${escapeHtml(label)}</b>` +
      `<span class="muted">${mmss(w.start_s)}–${mmss(w.end_s)}</span></div>`;
  }
  h += "</div>";

  if (spread != null && scored.length > 1) {
    const wide = spread >= SPREAD_DISAGREE;
    h +=
      `<p class="${wide ? "notice notice-warn" : "muted"}">` +
      `Khoảng cách giữa đoạn cao nhất và thấp nhất: <b>${spread.toFixed(2)} điểm</b>. ` +
      (wide
        ? "Các đoạn chênh nhau nhiều, nên con số tổng ở trên đang che mất hai phần bài " +
          "nói rất khác nhau. Hãy nghe lại từng đoạn thay vì đọc mỗi điểm tổng."
        : "Các đoạn cho kết quả gần nhau, nên điểm tổng phản ánh khá nhất quán cả bài.") +
      "</p>";
  }

  const failed = ws.length - scored.length;
  if (failed) {
    h +=
      `<p class="muted">${failed} đoạn không chấm được và đã bị loại khỏi phép tính trung vị.</p>`;
  }
  return h;
}

const INDICATOR_NAMES = {
  log_uniq: "Số từ khác nhau (log)",
  ttr: "Tỉ lệ từ khác nhau",
  mean_word_len: "Độ dài từ trung bình",
  asr_conf_mean: "Độ rõ khi máy nghe",
  asr_conf_geo: "Độ rõ khi máy nghe (trung bình nhân)",
  words_per_sec: "Tốc độ nói",
  vad_articulation_rate: "Tốc độ phát âm",
  vad_mean_pause: "Độ dài khoảng ngừng",
  vad_pause_per_min: "Số lần ngừng mỗi phút",
  vad_long_pause_ratio: "Tỉ lệ ngừng dài",
  n_words: "Số từ",
  vad_mean_seg_len: "Độ dài đoạn nói liền",
  total_dur: "Thời lượng",
  vad_silence_ratio: "Tỉ lệ im lặng",
};

// Chỉ báo theo tiêu chí (D022). Vị trí của một phép đo so với bài nói tham
// chiếu, đã quy về cùng chiều "cao hơn là tốt hơn". KHÔNG phải điểm tiêu chí.
function indicatorBlock(a) {
  const rows = a.indicators || [];
  if (!rows.length) return "";
  let h =
    '<details class="fold"><summary>Chỉ báo theo khía cạnh (không phải điểm), ' +
    `${rows.length} phép đo</summary>`;
  h +=
    '<p class="muted">Mỗi dòng cho biết phép đo của bạn đứng ở đâu so với các bài nói ' +
    "trong tập tham chiếu. Đây là vị trí, không phải điểm; mô hình chỉ có một điểm tổng thể.</p>";
  h += "<table><thead><tr><th>Khía cạnh</th><th>Phép đo</th><th>Vị trí</th></tr></thead><tbody>";
  rows.forEach((r) => {
    const standing = r.higher_is_better ? r.percentile : 1 - r.percentile;
    h +=
      `<tr><td>${escapeHtml(CRITERION_NAMES[r.criterion] || r.criterion)}</td>` +
      `<td>${escapeHtml(INDICATOR_NAMES[r.feature] || r.feature)}</td>` +
      `<td>tốt hơn khoảng ${Math.round(standing * 100)}% bài tham chiếu</td></tr>`;
  });
  return h + "</tbody></table></details>";
}

// Replaces the old five-row score table. No per-aspect score is printed,
// because no per-aspect score exists: the model has one output.
function aspectBlock(a) {
  const rows = a.criteria || [];
  let h = '<h2 id="aspects-h">Các khía cạnh được đo</h2>';
  h +=
    '<div class="notice notice-info"><b>Không có điểm riêng cho từng tiêu chí.</b> ' +
    "Mô hình được huấn luyện trên <b>một điểm tổng thể mỗi bài</b>; kho ngữ liệu không có " +
    "nhãn riêng cho phạm vi ngôn ngữ, độ chính xác, độ trôi chảy, độ mạch lạc hay phát âm. " +
    "Bảng dưới đây cho biết hệ thống <b>đo được những gì</b> ở mỗi khía cạnh, " +
    "không phải năm đánh giá độc lập.</div>";

  if (!rows.length) {
    h += '<p class="muted">Không có phép đo nào cho bài này.</p>';
    return h;
  }

  h +=
    "<table><thead><tr><th>Khía cạnh</th><th>Hệ thống đo gì</th>" +
    "<th>Đầy đủ dữ liệu</th></tr></thead><tbody>";
  rows.forEach((c) => {
    // `coverage` la ten moi; `confidence` la ten cu con nam trong cac bao
    // cao da luu truoc khi doi ten. Doc ca hai, khong migrate CSDL.
    const done = completeness(c.coverage ?? c.confidence);
    let cell;
    if (done.percent == null) {
      cell = '<span class="muted">Không đo được trên bản ghi này</span>';
    } else {
      cell =
        `<b>${done.percent}%</b> phép đo tính được` +
        (done.full ? "" : '<br><span class="muted">Một số phép đo thiếu dữ liệu</span>');
    }
    let what = escapeHtml(ASPECT_MEASURES[c.criterion] || "—");
    if (ASPECT_CAVEATS[c.criterion]) {
      what += `<br><span class="muted">${escapeHtml(ASPECT_CAVEATS[c.criterion])}</span>`;
    }
    h +=
      `<tr><td><b>${escapeHtml(CRITERION_NAMES[c.criterion] || c.criterion)}</b></td>` +
      `<td>${what}</td><td>${cell}</td></tr>`;
  });

  h += "</tbody></table>";

  // The one-line explanation the column header alone cannot carry. This used to
  // be labelled "Do tin cay", which it never was.
  h +=
    '<p class="muted"><b>“Đầy đủ dữ liệu”</b> chỉ cho biết hệ thống tính được bao nhiêu phần ' +
    "trăm số phép đo cần thiết trên bản ghi này. Nó <b>không</b> cho biết điểm đúng hay sai: " +
    "đủ 100% phép đo vẫn có thể ra một ước lượng lệch.</p>";
  return h;
}

// FR-25. Every sentence here cites the evidence it stands on, and the citation
// is rendered -- not kept in the payload where nobody would ever check it. A
// reader who cannot trace a claim has no way to tell measurement from filler.
function commentBlock(a) {
  const cs = a.comments || [];
  if (!cs.length) return "";
  let h = '<ul class="comment-list">';
  for (const c of cs) {
    const refs = (c.evidence_refs || []).join(", ");
    h += '<li class="comment">';
    h += `<p>${escapeHtml(c.text)}</p>`;
    if (refs) h += `<p class="muted comment-refs">Dựa trên bằng chứng: ${escapeHtml(refs)}</p>`;
    h += "</li>";
  }
  return h + "</ul>";
}

// FR-26. At most two, and none at all when confidence is low: advice built on a
// measurement the system does not trust is worse than saying nothing, because
// the student cannot tell which kind they are reading.
function priorityBlock(a) {
  const ps = a.priorities || [];
  if (!ps.length) return "";
  let h = '<h3 class="block-title">Nên luyện gì tiếp theo</h3>';
  h += '<ol class="priority-list">';
  for (const p of ps) {
    h += '<li class="priority">';
    h += `<p>${escapeHtml(p.text)}</p>`;
    h += `<p class="muted">Ước tính đang làm giảm khoảng ${Number(p.impact).toFixed(2)} điểm.</p>`;
    h += "</li>";
  }
  return h + "</ol>";
}

// The genuinely measured part, and the part a learner can act on.
function evidenceBlock(a) {
  const ev = a.evidence || [];
  let h = '<h3 class="block-title">Bằng chứng trên bản ghi</h3>';
  if (!ev.length) {
    return (
      h +
      '<p class="muted">Chưa đủ bằng chứng để đưa nhận xét: hệ thống không tìm thấy quãng ' +
      "ngừng dài, từ ngập ngừng hay từ nghe không rõ nào đáng nêu. Bài nói dài hơn thường " +
      "cho nhiều bằng chứng hơn.</p>"
    );
  }
  h += '<p class="muted">Những chỗ cụ thể hệ thống đo được. Bấm một thẻ để nghe lại đúng đoạn đó.</p>';
  h += '<div class="evidence-grid">';
  // FR-24: at most 6 items.
  ev.slice(0, 6).forEach((e) => {
    const seekable = e.start_s != null;
    const tag = seekable ? "button" : "div";
    const attrs = seekable ? ` type="button" data-seconds="${e.start_s}"` : "";
    h += `<${tag} class="evidence"${attrs}>`;
    h += '<span class="evidence-head">';
    h += `<span class="evidence-kind">${escapeHtml(EVIDENCE_KIND_NAMES[e.kind] || e.kind)}</span>`;
    if (seekable) h += `<span class="evidence-time">${mmss(e.start_s)}</span>`;
    h += "</span>";
    h += `<p class="evidence-note">${escapeHtml(e.note)}</p>`;
    if (e.snippet) h += `<p class="evidence-snippet">…${escapeHtml(e.snippet)}…</p>`;
    h += `<span class="muted">Khía cạnh: ${escapeHtml(CRITERION_NAMES[e.criterion] || e.criterion)}</span>`;
    if (seekable) h += '<span class="evidence-action">▶ Nghe đoạn này</span>';
    h += `</${tag}>`;
  });
  return h + "</div>";
}

function transcriptBlock(d) {
  const asr = d.asr;
  if (!asr || !asr.text) return "";
  let h = '<h3 class="block-title">Bản chép lời</h3>';
  h += '<div class="transcript-toolbar">';
  h +=
    '<span>Từ đang phát được tô sáng theo tiếng. Bấm vào một từ để tua tới đó.</span>';
  h +=
    '<span class="legend"><span class="swatch" aria-hidden="true"></span>' +
    "Máy nghe không rõ</span>";
  h += "</div>";
  h += '<div class="transcript" id="transcript-body">';
  if (asr.words && asr.words.length) {
    asr.words.forEach((w, i) => {
      // FR-10, FR-16. Nguong nam o `Word.is_uncertain` phia may chu chu
      // khong o day: luat nay tung duoc viet lai o ba noi va ba cho co the
      // lech nhau ma khong ai biet.
      const uncertain = w.is_uncertain;
      h +=
        `<span class="word${uncertain ? " ngo" : ""}" data-word-index="${i}"` +
        ` data-seconds="${w.start_s}"` +
        `${uncertain ? ' title="Máy có thể nghe nhầm từ này"' : ""}>${escapeHtml(w.text)}</span> `;
    });
  } else {
    h += escapeHtml(asr.text);
  }
  return h + "</div>";
}

function qualityBlock(d) {
  if (!d.qc) return "";
  const q = d.qc;
  return (
    '<h3 class="block-title">Chất lượng bản ghi</h3><table class="kv"><tbody>' +
    `<tr><th>Kết luận</th><td>${escapeHtml(q.qc_status)}</td></tr>` +
    `<tr><th>Thời lượng</th><td>${(q.duration_ms / 1000).toFixed(1)} giây</td></tr>` +
    `<tr><th>Tần số mẫu</th><td>${q.sample_rate_hz} Hz</td></tr>` +
    `<tr><th>Tỷ lệ im lặng</th><td>${q.silence_ratio}</td></tr>` +
    `<tr><th>Tỷ lệ chạm trần</th><td>${q.clipping_ratio}</td></tr>` +
    `<tr><th>Tín hiệu trên nhiễu</th><td>${
      q.snr_db == null ? "không đo được" : `${q.snr_db} dB`
    }</td></tr></tbody></table>`
  );
}

// FR-27: the seven provenance fields must appear at the foot of every report.
function provenanceBlock(d, a) {
  const rows = [
    ["Phiên bản mô hình", a.model_version],
    ["Phiên bản đặc trưng", a.feature_version],
    ["Mô hình nhận dạng", d.asr ? `${d.asr.engine} / ${d.asr.model_version}` : null],
    ["Bản đồ band", a.band_map_version],
    ["Hiệu chuẩn", a.calibration_version],
    ["Bộ ngưỡng QC", d.qc ? d.qc.qc_config_version : null],
    ["Phiên bản đề", d.prompt_version],
    ["Thời điểm chấm", a.scored_at],
  ];
  let h = '<h3 class="block-title">Nguồn gốc kết quả</h3><table class="kv"><tbody>';
  rows.forEach(([label, value]) => {
    h += `<tr><th>${label}</th><td><code>${escapeHtml(value ?? "chưa có")}</code></td></tr>`;
  });
  return h + "</tbody></table>";
}

// Clicking a piece of evidence or a word makes the player jump to exactly that
// moment. FR-24 allows an error of at most 0.5 second; setting currentTime
// directly leaves an error no larger than the resolution of the audio file.
//
// `n.dataset.seconds` reads the `data-seconds` attribute. This is correct and
// was fixed once already -- do not "correct" it back.
function wirePlayer() {
  const player = document.getElementById("phat");
  if (!player) return;
  reportEl.querySelectorAll("[data-seconds]").forEach((n) => {
    n.addEventListener("click", () => {
      player.currentTime = parseFloat(n.dataset.seconds);
      player.play();
    });
  });
}

// Highlight the word being spoken, live, as the audio plays.
//
// A word ends where the next one begins. The search keeps a cursor instead of
// scanning the array on every tick: `timeupdate` fires about four times a
// second and the transcript can run to several hundred words.
function wireKaraoke(d) {
  const player = document.getElementById("phat");
  const body = document.getElementById("transcript-body");
  const words = (d.asr && d.asr.words) || [];
  if (!player || !body || !words.length) return;

  const nodes = Array.from(body.querySelectorAll(".word"));
  const starts = words.map((w) => (w.start_s == null ? Infinity : w.start_s));
  let current = -1;

  function indexAt(t) {
    // Walk from the current position; a seek can move in either direction.
    let i = current < 0 ? 0 : current;
    while (i + 1 < starts.length && starts[i + 1] <= t) i += 1;
    while (i > 0 && starts[i] > t) i -= 1;
    return starts[i] > t ? -1 : i;
  }

  function paint() {
    const i = indexAt(player.currentTime);
    if (i === current) return;
    if (current >= 0 && nodes[current]) nodes[current].classList.remove("speaking");
    current = i;
    if (current >= 0 && nodes[current]) {
      nodes[current].classList.add("speaking");
      // Keep the highlighted word inside the scrolling transcript box, without
      // dragging the whole page around it.
      const node = nodes[current];
      const top = node.offsetTop - body.offsetTop;
      if (top < body.scrollTop || top > body.scrollTop + body.clientHeight - 40) {
        body.scrollTop = top - body.clientHeight / 2;
      }
    }
  }

  function clear() {
    if (current >= 0 && nodes[current]) nodes[current].classList.remove("speaking");
    current = -1;
  }

  player.addEventListener("timeupdate", paint);
  player.addEventListener("seeked", paint);
  player.addEventListener("ended", clear);
  player.addEventListener("pause", () => {
    /* the highlight stays put while paused, so the reader keeps their place */
  });
}


// Printing is the export path. The browser already turns this page into a PDF
// using the print stylesheet in style.css, so there is no second renderer to
// keep in step with the screen -- and nothing that can silently drift away from
// what the student actually read.
const printButton = document.getElementById("print-report");
if (printButton) {
  // Remember which sections we opened, in a variable rather than a data-
  // attribute on the element. Marking the DOM to remember something about the
  // DOM leaves state behind when anything goes wrong between the two halves of
  // the operation; a list here cannot outlive the print.
  let openedForPrint = [];

  printButton.addEventListener("click", () => {
    // Open every collapsed section first. A <details> left closed prints as a
    // one-line summary, so the transcript would silently vanish from the PDF.
    openedForPrint = [...document.querySelectorAll("details:not([open])")];
    openedForPrint.forEach((d) => {
      d.open = true;
    });
    window.print();
  });

  window.addEventListener("afterprint", () => {
    openedForPrint.forEach((d) => {
      d.open = false;
    });
    openedForPrint = [];
  });
}

// ---------------------------------------------------------------- next band (D069)
// Targets in numbers read off the scoring model, and the learner's own answer
// rewritten one band higher by a language model, made on request and kept.
const COACH_DIR = { up: "tăng", down: "giảm" };

function coachTargets(nb) {
  const rows = nb.targets
    .map((t) => {
      const to = t.direction === "up" ? "lên" : "xuống";
      return (
        `<li><b>${escapeHtml(t.label)}</b>: ${COACH_DIR[t.direction]} từ ${escapeHtml(String(t.now))} ` +
        `${to} ${escapeHtml(String(t.target))} ${escapeHtml(t.unit)}</li>`
      );
    })
    .join("");
  return (
    `<p>Bài này ở <b>${escapeHtml(nb.from_band)}</b>, còn cách ngưỡng <b>${escapeHtml(nb.to_band)}</b> ` +
    `khoảng ${escapeHtml(String(nb.gap).replace(".", ","))} điểm. Lần nói tới, nhắm vào:</p>` +
    `<ul class="coach-targets">${rows}</ul>` +
    `<p class="muted small-note">${
      nb.enough ? "Đạt cả ba thì ước lượng của máy đủ để qua ngưỡng." : "Chưa đủ trong một lần: đây là hướng đi cho vài bài tới."
    } Tính từ chính các phép đo của mô hình trên bài này; giảng viên quyết định band.</p>`
  );
}

function coachUpgrade(u) {
  const changes = (u.changes || [])
    .map(
      (c) =>
        `<li><span class="was" lang="en">${escapeHtml(c.from)}</span> → <span class="now" lang="en">${escapeHtml(c.to)}</span>` +
        (c.why_vi ? `<br><span class="muted">${escapeHtml(c.why_vi)}</span>` : "") +
        "</li>"
    )
    .join("");
  const phrases = (u.phrases || [])
    .map((p) => `<li><b lang="en">${escapeHtml(p.phrase)}</b>: ${escapeHtml(p.meaning_vi)}</li>`)
    .join("");
  return (
    `<h3 class="block-title">Bài của bạn ở mức ${escapeHtml(u.to_band)} <span class="muted">(gợi ý của AI, có thể sai)</span></h3>` +
    `<p class="upgrade-text" lang="en">${escapeHtml(u.upgraded)}</p>` +
    (changes ? `<h4>Các chỗ đổi</h4><ul class="coach-changes">${changes}</ul>` : "") +
    (phrases ? `<h4>Cụm từ nên dùng</h4><ul class="coach-phrases">${phrases}</ul>` : "") +
    `<div class="button-row"><a class="button" href="/retell/${encodeURIComponent(ID)}">Đọc rồi nói lại đề này</a></div>`
  );
}

function paintCoach(card, c) {
  let h = '<h2 id="coach-h">Để lên band tiếp theo</h2>';
  if (c.next_band) h += coachTargets(c.next_band);
  if (c.upgrade) h += coachUpgrade(c.upgrade);
  else if (c.can_upgrade)
    h +=
      '<div class="button-row"><button type="button" id="coach-upgrade">Xem bài của tôi ở band cao hơn</button></div>' +
      '<p class="muted small-note">AI viết lại chính câu trả lời của bạn ở band kế tiếp, giữ ý của bạn. Chỉ bản chép lời được gửi đi, không gửi ghi âm.</p>';
  card.innerHTML = h;
  card.hidden = !(c.next_band || c.upgrade || c.can_upgrade);
  const button = document.getElementById("coach-upgrade");
  if (!button) return;
  button.addEventListener("click", async () => {
    button.disabled = true;
    button.textContent = "Đang viết lại…";
    try {
      const r = await fetch(`/api/v1/responses/${encodeURIComponent(ID)}/upgrade`, { method: "POST" });
      if (window.redirectToLoginIfExpired(r)) return;
      const d = await r.json().catch(() => ({}));
      if (!r.ok) {
        window.toast(typeof d.detail === "string" ? d.detail : "Chưa viết lại được.", "error");
        button.disabled = false;
        button.textContent = "Xem bài của tôi ở band cao hơn";
        return;
      }
      paintCoach(card, { ...c, upgrade: d, can_upgrade: false });
    } catch (err) {
      window.toast("Mất kết nối, hãy thử lại.", "error");
      button.disabled = false;
    }
  });
}

function loadCoach() {
  const card = document.getElementById("report-coach");
  if (!card) return;
  fetch(`/api/v1/responses/${encodeURIComponent(ID)}/coach`)
    .then((r) => (r.ok ? r.json() : null))
    .then((c) => c && paintCoach(card, c))
    .catch(() => {});
}
