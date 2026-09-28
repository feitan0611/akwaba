// Akwaba — interface conversationnelle du prototype Baoulé / Dioula.
// Servie par l'API sur /demo/ : l'API est donc sur la même origine.
//
// Deux façons de parler à l'assistant :
//  - à la voix : micro → WAV 16 kHz → POST /pipeline (détection + réponse vocale)
//  - à l'écrit : /translate (langue locale → pivot) → /ask → /translate (retour) → /speech

const API = window.API_BASE || "/api/v1";
const LANG_NAMES = { bci: "Baoulé", dyu: "Dioula", fra: "Français", eng: "Anglais" };
const TARGET_SAMPLE_RATE = 16000;
const STORE_CONVERSATIONS = "akwaba.conversations";
const STORE_SETTINGS = "akwaba.settings";
const MAX_SAVED_CONVERSATIONS = 30;

const $ = (id) => document.getElementById(id);
const ICONS = {
  play: '<svg viewBox="0 0 24 24" class="icon"><path d="M7 4v16l13-8z" fill="currentColor" stroke="none"/></svg>',
  pause: '<svg viewBox="0 0 24 24" class="icon"><path d="M7 4h4v16H7zM13 4h4v16h-4z" fill="currentColor" stroke="none"/></svg>',
  mic: '<svg viewBox="0 0 24 24" class="icon"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M19 10v1a7 7 0 0 1-14 0v-1M12 18v4"/></svg>',
  pen: '<svg viewBox="0 0 24 24" class="icon"><path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>',
  chat: '<svg viewBox="0 0 24 24" class="icon"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
};

// ---------------------------------------------------------------- stockage local
// Tout accès à localStorage peut échouer (navigation privée, blocage) : on ne plante jamais.
const store = {
  get(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* stockage indisponible : l'historique ne sera simplement pas conservé */
    }
  },
};

const settings = { autoplay: true, textLang: "bci", ...store.get(STORE_SETTINGS, {}) };
let pivotLanguage = "fra";
let lastLanguage = null; // dernière langue détectée : réutilisée pour les messages écrits
let isMock = true;
// Ce que le moteur sait réellement faire (fourni par /health). Par défaut : rien.
let capabilities = { language_detection: false, languages: {} };

const supportsLanguage = (code) => Boolean(capabilities.languages[code]?.full);
const supportedLanguages = () => Object.keys(capabilities.languages).filter(supportsLanguage);
let conversation = newConversation();
let busy = false;

function newConversation() {
  return { id: Date.now().toString(36), date: Date.now(), title: "", messages: [] };
}

function saveConversation() {
  if (!conversation.messages.length) return;
  const all = store.get(STORE_CONVERSATIONS, []).filter((c) => c.id !== conversation.id);
  all.unshift({ ...conversation, date: Date.now() });
  store.set(STORE_CONVERSATIONS, all.slice(0, MAX_SAVED_CONVERSATIONS));
}

// ---------------------------------------------------------------- utilitaires
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function relativeDate(timestamp) {
  const minutes = (Date.now() - timestamp) / 60000;
  if (minutes < 1) return "À l'instant";
  if (minutes < 60) return `Il y a ${Math.floor(minutes)} min`;
  if (minutes < 24 * 60) return `Il y a ${Math.floor(minutes / 60)} h`;
  return new Date(timestamp).toLocaleDateString("fr-FR", { day: "numeric", month: "long" });
}

function formatTime(seconds) {
  if (!Number.isFinite(seconds)) return "0:00";
  return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error?.message || `Erreur ${response.status}`);
  return body;
}

const postJson = (path, data) =>
  api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });

async function timed(timings, step, fn) {
  const start = performance.now();
  const result = await fn();
  timings[step] = performance.now() - start;
  return result;
}

// ---------------------------------------------------------------- lecteur vocal
let currentAudio = null;

function voicePlayer(src, { autoplay = false } = {}) {
  const wrap = el("div", "voice");
  const button = el("button", "voice-play");
  button.type = "button";
  button.setAttribute("aria-label", "Écouter");
  button.innerHTML = ICONS.play;
  const bars = el("div", "voice-bars");
  const heights = Array.from({ length: 28 }, (_, i) => 25 + Math.abs(Math.sin(i * 1.7) * 60) + (i % 3) * 5);
  heights.forEach((h) => {
    const bar = el("span");
    bar.style.height = `${Math.min(100, h)}%`;
    bars.append(bar);
  });
  const time = el("span", "voice-time", "0:00");
  wrap.append(button, bars, time);

  const audio = new Audio(src);
  audio.addEventListener("loadedmetadata", () => (time.textContent = formatTime(audio.duration)));
  audio.addEventListener("timeupdate", () => {
    const progress = audio.currentTime / (audio.duration || 1);
    [...bars.children].forEach((bar, i) => bar.classList.toggle("played", i / bars.children.length < progress));
    time.textContent = formatTime(audio.currentTime || audio.duration);
  });
  audio.addEventListener("play", () => (button.innerHTML = ICONS.pause));
  const reset = () => (button.innerHTML = ICONS.play);
  audio.addEventListener("pause", reset);
  audio.addEventListener("ended", () => {
    reset();
    [...bars.children].forEach((bar) => bar.classList.remove("played"));
    time.textContent = formatTime(audio.duration);
  });

  const play = () => {
    if (currentAudio && currentAudio !== audio) currentAudio.pause();
    currentAudio = audio;
    audio.play().catch(() => {}); // lecture auto parfois bloquée par le navigateur : pas grave
  };
  button.addEventListener("click", () => (audio.paused ? play() : audio.pause()));
  if (autoplay) play();
  return wrap;
}

// ---------------------------------------------------------------- messages
function startConversationView() {
  document.body.classList.add("in-conversation");
}

function addMessage(role) {
  startConversationView();
  const msg = el("div", `msg ${role}`);
  if (role !== "user") msg.append(el("div", "avatar", "A"));
  const bubble = el("div", "bubble");
  msg.append(bubble);
  $("messages").append(msg);
  msg.scrollIntoView({ behavior: "smooth", block: "end" });
  return { msg, bubble };
}

function addTyping() {
  const { msg, bubble } = addMessage("bot");
  const dots = el("div", "typing");
  dots.append(el("span"), el("span"), el("span"));
  bubble.append(dots);
  if (!isMock) {
    const hint = el("p", "sub", "");
    bubble.append(hint);
    // Sur un portable sans carte graphique, une réponse complète prend souvent 20 à 60 s.
    setTimeout(() => {
      hint.textContent =
        "Les modèles tournent sur le processeur : la réponse peut prendre jusqu'à une minute " +
        "(davantage la toute première fois, le temps de charger les modèles).";
    }, 4000);
  }
  return { msg, bubble };
}

function langTag(code, suffix = "") {
  return el("span", "lang-tag", `${LANG_NAMES[code] || code}${suffix}`);
}

function renderUserText(text, lang) {
  const { bubble } = addMessage("user");
  bubble.append(el("p", "", text), langTag(lang));
}

function renderUserVoice(audioUrl) {
  const { bubble } = addMessage("user");
  bubble.append(voicePlayer(audioUrl));
  const sub = el("p", "sub", "Transcription en cours…");
  bubble.append(sub);
  return {
    update(text, lang, confidence, source) {
      sub.textContent = text;
      const suffix = source === "detected" ? ` · détecté (${Math.round(confidence * 100)} %)` : "";
      bubble.append(langTag(lang, suffix));
    },
    fail() {
      sub.textContent = "Message non traité";
    },
  };
}

function renderBotAnswer(slot, answer, { autoplay }) {
  const { bubble } = slot;
  bubble.replaceChildren();
  bubble.append(el("p", "", answer.text));
  if (answer.audioBase64) {
    bubble.append(voicePlayer(`data:audio/wav;base64,${answer.audioBase64}`, { autoplay }));
  }
  bubble.append(langTag(answer.lang));
  if (answer.steps) {
    const details = el("details", "steps");
    details.append(el("summary", "", "Étapes du traitement"));
    const dl = el("dl");
    const total = Object.values(answer.timings || {}).reduce((a, b) => a + b, 0);
    [
      [`Question (${LANG_NAMES[pivotLanguage]})`, answer.steps.questionPivot],
      [`Réponse (${LANG_NAMES[pivotLanguage]})`, answer.steps.answerPivot],
      [
        "Sources",
        answer.sources?.length
          ? answer.sources.map((src) => `${src.title}${src.section ? ` › ${src.section}` : ""} (${src.source})`).join(" · ")
          : "aucune — réponse sans la base de connaissances",
      ],
      ["Temps total", `${Math.round(total)} ms`],
    ].forEach(([k, v]) => dl.append(el("dt", "", k), el("dd", "", v)));
    details.append(dl);
    bubble.append(details);
  }
  slot.msg.scrollIntoView({ behavior: "smooth", block: "end" });
}

function renderError(slot, message) {
  slot.msg.classList.add("error");
  slot.bubble.replaceChildren(el("p", "", `Désolé, une erreur est survenue : ${message}`));
}

function remember(role, text, lang) {
  conversation.messages.push({ role, text, lang });
  if (!conversation.title && role === "user") conversation.title = text;
  saveConversation();
}

// ---------------------------------------------------------------- envoi vocal
// Retourne { ok, transcript, answer, audioBase64 } ou { ok: false, error } (utilisé par l'orbe).
async function sendVoice(blob, filename = "question.wav", { autoplay = settings.autoplay } = {}) {
  if (busy) return { ok: false, error: "Un message est déjà en cours de traitement." };
  setBusy(true);
  const userMsg = renderUserVoice(URL.createObjectURL(blob));
  const slot = addTyping();

  const form = new FormData();
  form.append("audio", blob, filename);
  if ($("lang").value) form.append("language_hint", $("lang").value);

  try {
    const r = await api("/pipeline", { method: "POST", body: form });
    const d = r.detection;
    lastLanguage = d.language;
    userMsg.update(d.text, d.language, d.confidence, d.language_source);
    renderBotAnswer(
      slot,
      {
        text: r.answer_text,
        lang: d.language,
        audioBase64: r.answer_audio_base64,
        steps: { questionPivot: r.question_pivot, answerPivot: r.answer_pivot },
        sources: r.sources,
        timings: r.timings_ms,
      },
      { autoplay },
    );
    if (!conversation.title) conversation.title = "Message vocal";
    remember("user", `🎙️ ${d.text}`, d.language);
    remember("bot", r.answer_text, d.language);
    return { ok: true, transcript: d.text, answer: r.answer_text, audioBase64: r.answer_audio_base64 };
  } catch (error) {
    userMsg.fail();
    renderError(slot, error.message);
    return { ok: false, error: error.message };
  } finally {
    setBusy(false);
  }
}

// ---------------------------------------------------------------- envoi écrit
async function sendText(text) {
  if (busy || !text.trim()) return;
  setBusy(true);
  const lang = $("lang").value || lastLanguage || defaultLanguage();
  renderUserText(text, lang);
  const slot = addTyping();
  const timings = {};

  try {
    const question = await timed(timings, "translate_in", () =>
      postJson("/translate", { text, source: lang, target: pivotLanguage }),
    );
    const answer = await timed(timings, "ask", () =>
      postJson("/ask", { text: question.text, language: pivotLanguage }),
    );
    const back = await timed(timings, "translate_out", () =>
      postJson("/translate", { text: answer.text, source: pivotLanguage, target: lang }),
    );
    const speech = await timed(timings, "speech", () => postJson("/speech", { text: back.text, language: lang }));
    renderBotAnswer(
      slot,
      {
        text: back.text,
        lang,
        audioBase64: speech.audio_base64,
        steps: { questionPivot: question.text, answerPivot: answer.text },
        sources: answer.sources,
        timings,
      },
      { autoplay: settings.autoplay },
    );
    remember("user", text, lang);
    remember("bot", back.text, lang);
  } catch (error) {
    renderError(slot, error.message);
  } finally {
    setBusy(false);
  }
}

function setBusy(value) {
  busy = value;
  $("mic-btn").disabled = value;
  $("orb-btn").disabled = value && !voice.active;
  updateSendButton();
}

function updateSendButton() {
  $("send-btn").disabled = busy || !$("text-input").value.trim();
}

// ---------------------------------------------------------------- micro
const recording = { recorder: null, stream: null, chunks: [], cancelled: false, timer: null, raf: null, ctx: null };

async function startRecording() {
  if (busy) return;
  try {
    recording.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    const slot = addMessage("bot");
    renderError(slot, "accès au micro refusé ou indisponible. Vous pouvez joindre un fichier audio.");
    return;
  }
  recording.chunks = [];
  recording.cancelled = false;
  recording.recorder = new MediaRecorder(recording.stream);
  recording.recorder.ondataavailable = (e) => recording.chunks.push(e.data);
  recording.recorder.onstop = onRecordingStop;
  recording.recorder.start();

  $("composer").classList.add("recording");
  $("rec-bar").hidden = false;
  $("mic-btn").setAttribute("aria-label", "Arrêter et envoyer");
  const started = Date.now();
  $("rec-time").textContent = "0:00";
  recording.timer = setInterval(() => ($("rec-time").textContent = formatTime((Date.now() - started) / 1000)), 250);
  showLevels(recording.stream);
}

function stopRecording(cancel = false) {
  if (!recording.recorder || recording.recorder.state !== "recording") return;
  recording.cancelled = cancel;
  recording.recorder.stop();
}

// Barres de niveau sonore en direct pendant l'enregistrement.
function showLevels(stream) {
  const container = $("rec-levels");
  container.replaceChildren(...Array.from({ length: 48 }, () => el("span")));
  recording.ctx = new AudioContext();
  const analyser = recording.ctx.createAnalyser();
  analyser.fftSize = 256;
  recording.ctx.createMediaStreamSource(stream).connect(analyser);
  const data = new Uint8Array(analyser.frequencyBinCount);
  const bars = [...container.children];
  const draw = () => {
    analyser.getByteFrequencyData(data);
    bars.forEach((bar, i) => {
      const value = data[Math.floor((i / bars.length) * data.length * 0.6)] / 255;
      bar.style.height = `${Math.max(3, value * 28)}px`;
    });
    recording.raf = requestAnimationFrame(draw);
  };
  draw();
}

async function onRecordingStop() {
  clearInterval(recording.timer);
  cancelAnimationFrame(recording.raf);
  recording.ctx?.close();
  recording.stream.getTracks().forEach((t) => t.stop());
  $("composer").classList.remove("recording");
  $("rec-bar").hidden = true;
  $("mic-btn").setAttribute("aria-label", "Parler");
  if (recording.cancelled || !recording.chunks.length) return;

  try {
    const wav = await toWav(new Blob(recording.chunks, { type: recording.recorder.mimeType }));
    await sendVoice(wav);
  } catch {
    renderError(addMessage("bot"), "impossible de lire l'enregistrement.");
  }
}

// Les navigateurs enregistrent en WebM/Ogg ; l'API n'accepte que WAV/MP3.
// On décode l'enregistrement puis on le ré-encode en WAV PCM 16 bits mono 16 kHz.
async function toWav(blob) {
  const decodeCtx = new AudioContext();
  const decoded = await decodeCtx.decodeAudioData(await blob.arrayBuffer());
  decodeCtx.close();
  const length = Math.ceil(decoded.duration * TARGET_SAMPLE_RATE);
  const offline = new OfflineAudioContext(1, length, TARGET_SAMPLE_RATE);
  const source = offline.createBufferSource();
  source.buffer = decoded;
  source.connect(offline.destination);
  source.start();
  const samples = (await offline.startRendering()).getChannelData(0);

  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeString = (offset, s) => [...s].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
  writeString(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true); // taille du bloc fmt
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, TARGET_SAMPLE_RATE, true);
  view.setUint32(28, TARGET_SAMPLE_RATE * 2, true); // octets par seconde
  view.setUint16(32, 2, true); // octets par échantillon
  view.setUint16(34, 16, true); // bits par échantillon
  writeString(36, "data");
  view.setUint32(40, samples.length * 2, true);
  samples.forEach((s, i) => {
    const clamped = Math.max(-1, Math.min(1, s));
    view.setInt16(44 + i * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
  });
  return new Blob([buffer], { type: "audio/wav" });
}

// ---------------------------------------------------------------- conversation vocale (orbe)
// Mode « mains libres » : l'orbe écoute, détecte la fin de la phrase (silence), envoie,
// lit la réponse à voix haute puis se remet à écouter, sans toucher à aucun bouton.
//
// Détection de parole simple (VAD) par niveau sonore : on mesure le bruit ambiant pendant
// les 400 premières ms, puis on considère qu'il y a parole au-dessus de 3× ce niveau.
const VAD = {
  calibrationMs: 400,
  minThreshold: 0.015, // niveau RMS minimal considéré comme de la parole
  noiseFactor: 3,
  minSpeechMs: 300, // en dessous : bruit bref (toux, clic), ignoré
  endSilenceMs: 1200, // silence qui marque la fin de la phrase
  maxUtteranceMs: 30000,
  idleRestartMs: 15000, // sans parole : on recommence un enregistrement neuf
};
const ORB_STATUS = {
  listening: "Je vous écoute…",
  thinking: "Je réfléchis…",
  speaking: "Akwaba vous répond…",
};

const voice = {
  active: false,
  state: "idle",
  stream: null,
  ctx: null,
  analyser: null,
  outAnalyser: null,
  recorder: null,
  chunks: [],
  discard: false,
  raf: null,
  listenStart: 0,
  noiseSamples: [],
  speechStart: 0,
  lastVoice: 0,
  level: 0,
  audio: null,
};

function rms(analyser) {
  const buffer = new Float32Array(analyser.fftSize);
  analyser.getFloatTimeDomainData(buffer);
  let sum = 0;
  for (const v of buffer) sum += v * v;
  return Math.sqrt(sum / buffer.length);
}

function setOrb(state, text) {
  voice.state = state;
  $("voice-mode").dataset.state = state;
  $("orb-status").textContent = text || ORB_STATUS[state] || "";
}

async function openVoiceMode() {
  if (busy || voice.active) return;
  stopRecording(true);
  try {
    voice.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
  } catch {
    renderError(addMessage("bot"), "accès au micro refusé ou indisponible.");
    return;
  }
  voice.ctx = new AudioContext();
  voice.analyser = voice.ctx.createAnalyser();
  voice.analyser.fftSize = 1024;
  voice.ctx.createMediaStreamSource(voice.stream).connect(voice.analyser);
  voice.active = true;

  const lang = $("lang").value;
  $("voice-lang").textContent = lang ? LANG_NAMES[lang] : "Détection auto";
  $("orb-caption").replaceChildren();
  $("voice-mode").hidden = false;
  document.body.classList.add("voice-open");
  voiceLoop();
  listen();
}

function closeVoiceMode() {
  if (!voice.active) return;
  voice.active = false;
  cancelAnimationFrame(voice.raf);
  if (voice.recorder?.state === "recording") {
    voice.discard = true;
    voice.recorder.stop();
  }
  voice.audio?.pause();
  voice.stream?.getTracks().forEach((t) => t.stop());
  voice.ctx?.close();
  Object.assign(voice, { stream: null, ctx: null, analyser: null, outAnalyser: null, audio: null, state: "idle" });
  $("voice-mode").hidden = true;
  document.body.classList.remove("voice-open");
  $("orb-btn").focus();
}

function listen() {
  if (!voice.active) return;
  setOrb("listening");
  Object.assign(voice, { chunks: [], discard: false, speechStart: 0, lastVoice: 0, noiseSamples: [] });
  voice.listenStart = performance.now();
  voice.recorder = new MediaRecorder(voice.stream);
  voice.recorder.ondataavailable = (e) => voice.chunks.push(e.data);
  voice.recorder.onstop = onUtteranceEnd;
  voice.recorder.start();
}

function endUtterance() {
  setOrb("thinking"); // change d'état AVANT l'arrêt : la boucle cesse d'écouter
  voice.recorder.stop();
}

function restartListening() {
  voice.discard = true;
  voice.recorder.stop(); // onUtteranceEnd relancera l'écoute
}

// Boucle d'animation : détection de parole pendant l'écoute, et taille de l'orbe
// proportionnelle au volume (votre voix quand il écoute, la sienne quand il parle).
function voiceLoop() {
  if (!voice.active) return;
  const now = performance.now();
  let target = 0;

  if (voice.state === "listening" && voice.analyser && voice.recorder?.state === "recording") {
    const level = rms(voice.analyser);
    target = Math.min(1, level * 10);
    const elapsed = now - voice.listenStart;
    if (elapsed < VAD.calibrationMs) {
      voice.noiseSamples.push(level);
    } else {
      // Bruit de fond = moyenne de la moitié la plus calme des mesures de calibration.
      const quiet = [...voice.noiseSamples].sort((a, b) => a - b).slice(0, Math.ceil(voice.noiseSamples.length / 2));
      const noise = quiet.reduce((a, b) => a + b, 0) / (quiet.length || 1);
      const threshold = Math.max(VAD.minThreshold, noise * VAD.noiseFactor);
      if (level > threshold) {
        if (!voice.speechStart) voice.speechStart = now;
        voice.lastVoice = now;
      }
      if (voice.speechStart && now - voice.lastVoice > VAD.endSilenceMs) {
        if (voice.lastVoice - voice.speechStart >= VAD.minSpeechMs) endUtterance();
        else voice.speechStart = 0; // simple bruit : on continue d'écouter
      } else if (voice.speechStart && now - voice.speechStart > VAD.maxUtteranceMs) {
        endUtterance();
      } else if (!voice.speechStart && elapsed > VAD.idleRestartMs) {
        restartListening();
      }
    }
  } else if (voice.state === "speaking" && voice.outAnalyser) {
    target = Math.min(1, rms(voice.outAnalyser) * 5);
  }

  voice.level += (target - voice.level) * 0.25; // lissage
  $("orb").style.setProperty("--level", voice.level.toFixed(3));
  voice.raf = requestAnimationFrame(voiceLoop);
}

async function onUtteranceEnd() {
  if (!voice.active) return;
  if (voice.discard) return listen();

  let wav;
  try {
    wav = await toWav(new Blob(voice.chunks, { type: voice.recorder.mimeType }));
  } catch {
    return retryAfter("Je n'ai pas pu lire l'enregistrement.");
  }
  const result = await sendVoice(wav, "question.wav", { autoplay: false });
  if (!voice.active) return;
  if (!result.ok) return retryAfter(result.error);

  showCaption(result.transcript, result.answer);
  await speak(result.audioBase64);
  if (voice.active) setTimeout(listen, 300); // courte pause pour ne pas capter la fin de sa propre voix
}

function retryAfter(message) {
  setOrb("error", message);
  setTimeout(() => voice.active && listen(), 2500);
}

function showCaption(transcript, answer) {
  $("orb-caption").replaceChildren(el("span", "caption-you", `Vous : ${transcript}`), el("span", "caption-bot", answer));
}

function speak(audioBase64) {
  return new Promise((resolve) => {
    const audio = new Audio(`data:audio/wav;base64,${audioBase64}`);
    voice.audio = audio;
    try {
      // Analyseur branché sur la sortie : l'orbe pulse au rythme de la voix de l'assistant.
      voice.outAnalyser = voice.ctx.createAnalyser();
      voice.outAnalyser.fftSize = 1024;
      voice.ctx.createMediaElementSource(audio).connect(voice.outAnalyser);
      voice.outAnalyser.connect(voice.ctx.destination);
    } catch {
      voice.outAnalyser = null; // l'audio est joué quand même, sans animation synchronisée
    }
    const done = () => {
      voice.outAnalyser = null;
      resolve();
    };
    audio.addEventListener("ended", done);
    audio.addEventListener("pause", done);
    audio.addEventListener("error", done);
    setOrb("speaking");
    audio.play().catch(done);
  });
}

// ---------------------------------------------------------------- cartes d'accueil
function renderCards() {
  const cards = $("cards");
  cards.replaceChildren();
  const recent = store.get(STORE_CONVERSATIONS, []).slice(0, 5);

  const items = recent.length
    ? recent.map((c) => ({ title: c.title, meta: relativeDate(c.date), icon: ICONS.chat, action: () => openConversation(c) }))
    : [
        ...supportedLanguages().map((code) => ({
          title: `Parler en ${LANG_NAMES[code]}`,
          meta: "Micro",
          icon: ICONS.mic,
          action: () => quickStart(code),
        })),
        ...(capabilities.language_detection
          ? [{ title: "Laisser l'assistant détecter la langue", meta: "Micro", icon: ICONS.mic, action: () => quickStart("") }]
          : []),
        { title: "Conversation vocale mains libres", meta: "Orbe", icon: ICONS.mic, action: openVoiceMode },
        { title: "Écrire une question", meta: "Clavier", icon: ICONS.pen, action: () => $("text-input").focus() },
      ];

  items.forEach((item) => {
    const card = el("button", "card");
    card.type = "button";
    const meta = el("span", "card-meta");
    meta.innerHTML = item.icon;
    meta.append(item.meta);
    card.append(el("span", "", item.title), meta);
    card.addEventListener("click", item.action);
    cards.append(card);
  });
}

function quickStart(lang) {
  $("lang").value = lang;
  startRecording();
}

// ---------------------------------------------------------------- conversations
function resetChat() {
  stopRecording(true);
  conversation = newConversation();
  lastLanguage = null;
  $("messages").replaceChildren();
  document.body.classList.remove("in-conversation");
  renderCards();
  showView("chat");
}

function openConversation(saved) {
  resetChat();
  conversation = saved;
  startConversationView();
  saved.messages.forEach((m) => {
    const { bubble } = addMessage(m.role);
    bubble.append(el("p", "", m.text), langTag(m.lang));
    lastLanguage = m.lang;
  });
}

function renderHistory() {
  const list = $("history-list");
  list.replaceChildren();
  const all = store.get(STORE_CONVERSATIONS, []);
  if (!all.length) {
    list.append(el("p", "muted", "Aucune conversation pour l'instant."));
    return;
  }
  all.forEach((c) => {
    const item = el("button", "card history-item");
    item.type = "button";
    const meta = el("span", "card-meta", `${c.messages.length} messages · ${relativeDate(c.date)}`);
    item.append(el("span", "", c.title || "Conversation"), meta);
    item.addEventListener("click", () => openConversation(c));
    list.append(item);
  });
}

// ---------------------------------------------------------------- navigation
function showView(name) {
  ["chat", "history", "settings"].forEach((v) => ($(`view-${v}`).hidden = v !== name));
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === name));
  if (name === "history") renderHistory();
  document.body.classList.toggle("in-conversation", name === "chat" && $("messages").children.length > 0);
}

// ---------------------------------------------------------------- état du moteur
async function loadHealth() {
  const pill = $("engine-pill");
  try {
    const health = await api("/health");
    pivotLanguage = health.pivot_language || "fra";
    capabilities = health.capabilities || capabilities;
    const mock = health.engine === "mock";
    isMock = mock;
    applyCapabilities();
    pill.className = `pill status ${mock ? "mock" : "ok"}`;
    pill.textContent = mock ? "Mode test" : "En ligne";
    const models = Object.entries(health.models || {}).map(([task, name]) => `${task} : ${name}`).join(" · ");
    pill.title = mock ? "Moteur factice : les réponses ne sont pas réelles" : models;
    $("engine-info").textContent = mock
      ? "Mode test (mock) : les réponses sont factices, aucun modèle réel n'est chargé."
      : `Modèles réels — ${models}. Langue pivot : ${LANG_NAMES[pivotLanguage]}.`;
  } catch {
    pill.className = "pill status down";
    pill.textContent = "Hors ligne";
    $("engine-info").textContent = "API injoignable.";
  }
}

function defaultLanguage() {
  if (supportsLanguage(settings.textLang)) return settings.textLang;
  return supportedLanguages()[0] || settings.textLang;
}

// Adapte l'interface à ce que le moteur sait faire : pas d'option « Détection auto » sans
// détection, et les langues sans modèle sont affichées « bientôt » mais non sélectionnables.
function applyCapabilities() {
  const fill = (select, withAuto) => {
    const previous = select.value;
    select.replaceChildren();
    if (withAuto && capabilities.language_detection) select.append(new Option("Détection auto", ""));
    Object.keys(capabilities.languages).forEach((code) => {
      const available = supportsLanguage(code);
      const option = new Option(available ? LANG_NAMES[code] : `${LANG_NAMES[code]} — bientôt`, code);
      option.disabled = !available;
      select.append(option);
    });
    const values = [...select.options].filter((o) => !o.disabled).map((o) => o.value);
    select.value = values.includes(previous) ? previous : values[0] ?? "";
  };
  fill($("lang"), true);
  fill($("set-textlang"), false);
  $("set-textlang").value = defaultLanguage();

  const available = supportedLanguages().map((c) => LANG_NAMES[c]);
  const missing = Object.keys(capabilities.languages).filter((c) => !supportsLanguage(c)).map((c) => LANG_NAMES[c]);
  $("eyebrow").textContent =
    (available.join(" · ") || "Aucune langue disponible") +
    (isMock ? " — mode test" : missing.length ? ` — ${missing.join(", ")} en préparation` : "");
  renderCards();
}

// ---------------------------------------------------------------- initialisation
function init() {
  const hour = new Date().getHours();
  $("greeting").textContent = hour >= 18 || hour < 5 ? "Bonsoir !" : "Bonjour !";

  const input = $("text-input");
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = `${input.scrollHeight}px`;
    updateSendButton();
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      $("composer").requestSubmit();
    }
  });
  $("composer").addEventListener("submit", (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    input.style.height = "auto";
    sendText(text);
  });

  $("mic-btn").addEventListener("click", () =>
    recording.recorder?.state === "recording" ? stopRecording() : startRecording(),
  );
  $("rec-cancel").addEventListener("click", () => stopRecording(true));
  $("orb-btn").addEventListener("click", openVoiceMode);
  $("voice-close").addEventListener("click", closeVoiceMode);
  $("orb").addEventListener("click", closeVoiceMode);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && voice.active) closeVoiceMode();
  });
  $("file-input").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) sendVoice(file, file.name);
    e.target.value = "";
  });

  document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => showView(tab.dataset.view)));
  $("new-chat").addEventListener("click", resetChat);

  $("set-autoplay").checked = settings.autoplay;
  $("set-textlang").value = settings.textLang;
  $("set-autoplay").addEventListener("change", (e) => {
    settings.autoplay = e.target.checked;
    store.set(STORE_SETTINGS, settings);
  });
  $("set-textlang").addEventListener("change", (e) => {
    settings.textLang = e.target.value;
    store.set(STORE_SETTINGS, settings);
  });
  $("clear-history").addEventListener("click", () => {
    if (!confirm("Effacer toutes les conversations enregistrées sur cet appareil ?")) return;
    store.set(STORE_CONVERSATIONS, []);
    renderHistory();
    renderCards();
  });

  renderCards();
  loadHealth();
}

init();
