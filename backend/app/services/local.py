"""Moteur "local" : vrais modèles open source exécutés sur la machine (CPU).

| Brique      | Modèle                               | Langues         | Licence      |
|-------------|--------------------------------------|-----------------|--------------|
| STT         | facebook/mms-1b-all (adaptateur dyu) | dyu             | CC-BY-NC-4.0 |
| Traduction  | facebook/nllb-200-distilled-600M     | dyu, fra, eng   | CC-BY-NC-4.0 |
| LLM         | Ollama (qwen2.5:3b par défaut)       | fra, eng        | selon modèle |
| TTS         | facebook/mms-tts-dyu                 | dyu             | CC-BY-NC-4.0 |

Couverture vérifiée le 28/09/2026 (voir docs/adr/0003-choix-des-modeles.md) : AUCUN modèle
public ne couvre le Baoulé pour le STT, la traduction ou la TTS. Toute demande en Baoulé lève
donc LanguageNotSupportedError plutôt que de produire un résultat inventé.

Pas de détection automatique de langue dans cette version allégée : la langue est fournie
par le client (language_hint).

Les bibliothèques lourdes (torch, transformers…) sont importées à la première utilisation :
le serveur démarre vite et ce module s'importe même sans elles (tests, moteur mock).
Les licences CC-BY-NC-4.0 interdisent tout usage commercial.
"""

import io
import logging
import threading
from collections.abc import Callable
from math import gcd
from typing import Any

from app.audio import AudioInput, pcm16_to_wav
from app.languages import ALL_LANGUAGES
from app.services.base import (
    EngineUnavailableError,
    InvalidInputError,
    LanguageRequiredError,
    Responder,
    SpeechRecognizer,
    SpeechSynthesizer,
    Transcription,
    Translator,
)

logger = logging.getLogger(__name__)


def use_system_certificates() -> None:
    """Fait valider le HTTPS par le magasin de certificats du système (Windows, macOS).

    Nécessaire quand un antivirus (Avast, Kaspersky…) ou un proxy d'entreprise inspecte le
    trafic HTTPS : son certificat racine est connu du système mais pas de Python, et les
    téléchargements de modèles échouent avec CERTIFICATE_VERIFY_FAILED. La vérification des
    certificats reste active : on change seulement la liste des autorités de confiance.
    """
    try:
        import truststore
    except ImportError:
        return
    truststore.inject_into_ssl()


use_system_certificates()

SAMPLE_RATE = 16_000
MIN_AUDIO_S = 0.3
MAX_AUDIO_S = 60.0


class LazyModel:
    """Charge un modèle une seule fois, au premier besoin, de façon thread-safe.

    Le verrou sert aussi à exécuter l'inférence un appel à la fois : sur un portable sans GPU,
    des inférences parallèles sur un même modèle saturent la RAM et le CPU sans rien gagner.
    """

    def __init__(self, label: str, loader: Callable[[], Any]) -> None:
        self.label = label
        self._loader = loader
        self._value: Any = None
        self.lock = threading.RLock()

    @property
    def loaded(self) -> bool:
        return self._value is not None

    def get(self) -> Any:
        with self.lock:
            if self._value is None:
                logger.info("Chargement du modèle %s…", self.label)
                self._value = self._loader()
                logger.info("Modèle %s chargé.", self.label)
            return self._value


def decode_audio(audio: AudioInput):
    """WAV/MP3 → tableau numpy float32 mono à 16 kHz (format attendu par les modèles MMS)."""
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    try:
        data, rate = sf.read(io.BytesIO(audio.data), dtype="float32", always_2d=True)
    except Exception as exc:  # soundfile lève des erreurs variées selon le format
        raise InvalidInputError("Impossible de lire le fichier audio (fichier corrompu ?).") from exc

    samples = data.mean(axis=1)
    if rate != SAMPLE_RATE:
        factor = gcd(SAMPLE_RATE, rate)
        samples = resample_poly(samples, SAMPLE_RATE // factor, rate // factor)

    duration = len(samples) / SAMPLE_RATE
    if duration < MIN_AUDIO_S:
        raise InvalidInputError("Audio trop court : parlez au moins une demi-seconde.")
    if duration > MAX_AUDIO_S:
        raise InvalidInputError(f"Audio trop long ({duration:.0f} s) : maximum {MAX_AUDIO_S:.0f} secondes.")
    return samples.astype(np.float32)


# --- STT ----------------------------------------------------------------------------------


class MMSSpeechRecognizer(SpeechRecognizer):
    model_id = "facebook/mms-1b-all"
    name = "mms-1b-all"
    detects_language = False
    languages = frozenset({"dyu"})

    def __init__(self) -> None:
        self._model = LazyModel(self.model_id, self._load)

    def _load(self):
        from transformers import AutoProcessor, Wav2Vec2ForCTC

        # target_lang ne télécharge que l'adaptateur de la langue (quelques Mo) en plus du modèle de base.
        processor = AutoProcessor.from_pretrained(self.model_id, target_lang="dyu")
        model = Wav2Vec2ForCTC.from_pretrained(self.model_id, target_lang="dyu", ignore_mismatched_sizes=True)
        return processor, model.eval()

    def warmup(self) -> None:
        self._model.get()

    def transcribe(self, audio: AudioInput) -> Transcription:
        language = audio.options.get("language_hint")
        if not language:
            raise LanguageRequiredError()
        self.check_language(language)
        samples = decode_audio(audio)

        import torch

        processor, model = self._model.get()
        with self._model.lock, torch.inference_mode():
            inputs = processor(samples, sampling_rate=SAMPLE_RATE, return_tensors="pt")
            ids = torch.argmax(model(**inputs).logits, dim=-1)[0]
            text = processor.decode(ids).strip()

        if not text:
            raise InvalidInputError("Aucune parole n'a été reconnue dans l'audio.")
        # Langue fournie par le client, pas détectée : la confiance porte sur la langue déclarée.
        return Transcription(text=text, language=language, confidence=1.0, language_source="provided")


# --- Traduction ---------------------------------------------------------------------------

NLLB_CODES = {"dyu": "dyu_Latn", "fra": "fra_Latn", "eng": "eng_Latn"}


class NLLBTranslator(Translator):
    model_id = "facebook/nllb-200-distilled-600M"
    name = "nllb-200-distilled-600M"
    languages = frozenset(NLLB_CODES)

    def __init__(self) -> None:
        self._model = LazyModel(self.model_id, self._load)

    def _load(self):
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        # Ce dépôt ne publie que pytorch_model.bin : use_safetensors=False évite que transformers
        # ne tente de récupérer en plus une conversion safetensors (2,3 Go de téléchargement inutile).
        model = AutoModelForSeq2SeqLM.from_pretrained(self.model_id, use_safetensors=False)
        return tokenizer, model.eval()

    def warmup(self) -> None:
        self._model.get()

    def translate(self, text: str, source: str, target: str) -> str:
        self.check_language(source)
        self.check_language(target)

        import torch

        tokenizer, model = self._model.get()
        with self._model.lock, torch.inference_mode():
            tokenizer.src_lang = NLLB_CODES[source]  # état partagé : modifié sous verrou
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            output = model.generate(
                **inputs,
                forced_bos_token_id=tokenizer.convert_tokens_to_ids(NLLB_CODES[target]),
                max_new_tokens=256,
                num_beams=4,
            )
        return tokenizer.batch_decode(output, skip_special_tokens=True)[0].strip()


# --- LLM ----------------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "Tu es Akwaba, un assistant vocal destiné aux habitants de Côte d'Ivoire, "
    "y compris des personnes peu à l'aise avec l'écrit. Réponds en {language}, "
    "en une à trois phrases courtes et simples, sans liste, sans emoji ni mise en forme : "
    "ta réponse sera traduite automatiquement dans une langue locale puis lue à voix haute. "
    "Si tu ne connais pas une information locale précise (prix, lieux, horaires), "
    "dis-le honnêtement et donne un conseil utile."
)


class OllamaResponder(Responder):
    languages = frozenset({"fra", "eng"})

    def __init__(self, base_url: str, model: str, timeout_s: float = 180.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self.name = f"ollama:{model}"

    def answer(self, question: str, language: str) -> str:
        self.check_language(language)
        import httpx

        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT.format(language=ALL_LANGUAGES[language].lower())},
                {"role": "user", "content": question},
            ],
            "options": {"temperature": 0.3, "num_predict": 160},
        }
        try:
            response = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout_s)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise EngineUnavailableError(
                f"Le LLM ne répond pas (Ollama, modèle {self.model}). Vérifiez qu'Ollama est lancé "
                f"et que le modèle est téléchargé : ollama pull {self.model}"
            ) from exc
        return response.json()["message"]["content"].strip()


# --- TTS ----------------------------------------------------------------------------------

TTS_MODELS = {"dyu": "facebook/mms-tts-dyu"}


class MMSSpeechSynthesizer(SpeechSynthesizer):
    name = "mms-tts"
    languages = frozenset(TTS_MODELS)

    def __init__(self) -> None:
        self._models = {
            language: LazyModel(model_id, lambda model_id=model_id: self._load(model_id))
            for language, model_id in TTS_MODELS.items()
        }

    @staticmethod
    def _load(model_id: str):
        from transformers import AutoTokenizer, VitsModel

        return AutoTokenizer.from_pretrained(model_id), VitsModel.from_pretrained(model_id).eval()

    def warmup(self) -> None:
        for model in self._models.values():
            model.get()

    def synthesize(self, text: str, language: str, voice_id: str | None = None) -> bytes:
        self.check_language(language)

        import numpy as np
        import torch

        lazy = self._models[language]
        tokenizer, model = lazy.get()
        with lazy.lock, torch.inference_mode():
            inputs = tokenizer(text, return_tensors="pt")
            if inputs["input_ids"].shape[-1] == 0:
                raise InvalidInputError("Le texte ne contient aucun caractère prononçable par la synthèse vocale.")
            torch.manual_seed(0)  # VITS est stochastique : même texte → même audio
            waveform = model(**inputs).waveform[0].numpy()

        pcm = (np.clip(waveform, -1.0, 1.0) * 32767).astype("<i2").tobytes()
        return pcm16_to_wav(pcm, model.config.sampling_rate)
