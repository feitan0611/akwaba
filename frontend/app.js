// Démonstrateur : enregistre ou charge un audio, l'envoie à /api/v1/pipeline et affiche la réponse.
// Servi par l'API sur /demo/ : l'API est donc sur la même origine.
const API_BASE = window.API_BASE || "/api/v1";
const LANG_NAMES = { bci: "Baoulé", dyu: "Dioula" };
const TARGET_SAMPLE_RATE = 16000;

const $ = (id) => document.getElementById(id);
let audioBlob = null;
let recorder = null;

function setStatus(message) {
  $("status").textContent = message;
}

function setInput(blob) {
  audioBlob = blob;
  $("input-audio").src = URL.createObjectURL(blob);
  $("input-audio").hidden = false;
  $("send-btn").disabled = false;
}

// Les navigateurs enregistrent en WebM/Ogg ; l'API n'accepte que WAV/MP3.
// On décode donc l'enregistrement puis on le ré-encode en WAV PCM 16 bits mono 16 kHz.
async function toWav(blob) {
  const decoded = await new AudioContext().decodeAudioData(await blob.arrayBuffer());
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
  view.setUint32(16, 16, true);                      // taille du bloc fmt
  view.setUint16(20, 1, true);                       // PCM
  view.setUint16(22, 1, true);                       // mono
  view.setUint32(24, TARGET_SAMPLE_RATE, true);
  view.setUint32(28, TARGET_SAMPLE_RATE * 2, true);  // octets par seconde
  view.setUint16(32, 2, true);                       // octets par échantillon
  view.setUint16(34, 16, true);                      // bits par échantillon
  writeString(36, "data");
  view.setUint32(40, samples.length * 2, true);
  samples.forEach((s, i) => {
    const clamped = Math.max(-1, Math.min(1, s));
    view.setInt16(44 + i * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
  });
  return new Blob([buffer], { type: "audio/wav" });
}

async function toggleRecording() {
  const button = $("record-btn");
  if (recorder && recorder.state === "recording") {
    recorder.stop();
    return;
  }
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    setStatus("Accès au micro refusé ou indisponible.");
    return;
  }
  const chunks = [];
  recorder = new MediaRecorder(stream);
  recorder.ondataavailable = (e) => chunks.push(e.data);
  recorder.onstop = async () => {
    stream.getTracks().forEach((t) => t.stop());
    button.textContent = "🎙️ Enregistrer";
    button.classList.remove("recording");
    setStatus("Conversion en WAV…");
    try {
      setInput(await toWav(new Blob(chunks, { type: recorder.mimeType })));
      setStatus("Enregistrement prêt.");
    } catch {
      setStatus("Impossible de convertir l'enregistrement.");
    }
  };
  recorder.start();
  button.textContent = "⏹️ Arrêter";
  button.classList.add("recording");
  setStatus("Enregistrement en cours…");
}

async function send() {
  const form = new FormData();
  form.append("audio", audioBlob, audioBlob.name || "question.wav");
  if ($("hint").value) form.append("language_hint", $("hint").value);

  $("send-btn").disabled = true;
  setStatus("Traitement…");
  try {
    const response = await fetch(`${API_BASE}/pipeline`, { method: "POST", body: form });
    const body = await response.json();
    if (!response.ok) {
      setStatus(`Erreur : ${body.error?.message ?? response.status}`);
      return;
    }
    showResult(body);
    setStatus("");
  } catch {
    setStatus("API injoignable.");
  } finally {
    $("send-btn").disabled = false;
  }
}

function showResult(r) {
  const d = r.detection;
  $("r-lang").textContent = `${LANG_NAMES[d.language] ?? d.language} (confiance ${Math.round(d.confidence * 100)} %)`;
  $("r-text").textContent = d.text;
  $("r-qpivot").textContent = r.question_pivot;
  $("r-apivot").textContent = r.answer_pivot;
  $("r-answer").textContent = r.answer_text;
  $("output-audio").src = `data:audio/wav;base64,${r.answer_audio_base64}`;
  const total = Object.values(r.timings_ms).reduce((a, b) => a + b, 0);
  $("r-timings").textContent =
    `Temps de traitement : ${total.toFixed(0)} ms — ` +
    Object.entries(r.timings_ms).map(([k, v]) => `${k} ${v.toFixed(0)} ms`).join(", ");
  $("result").hidden = false;
}

async function showEngine() {
  try {
    const health = await (await fetch(`${API_BASE}/health`)).json();
    if (health.engine === "mock") {
      $("engine-banner").textContent =
        "⚠️ Moteur de test (mock) : les réponses sont factices, aucun modèle réel n'est chargé.";
      $("engine-banner").hidden = false;
    }
  } catch {
    setStatus("API injoignable.");
  }
}

$("record-btn").addEventListener("click", toggleRecording);
$("file-input").addEventListener("change", (e) => {
  if (e.target.files[0]) setInput(e.target.files[0]);
});
$("send-btn").addEventListener("click", send);
showEngine();
