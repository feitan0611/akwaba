"""Lecture et validation de l'audio entrant.

Deux formats d'envoi sont acceptés sur le même endpoint (exigence du cahier des charges) :
  - multipart/form-data : champ fichier `audio` (+ champs texte optionnels)
  - application/json    : {"audio_base64": "...", ...champs optionnels}

Seuls les formats WAV et MP3 sont acceptés ; le format est vérifié sur le contenu
(signature binaire), pas seulement sur l'extension du fichier.
"""

import base64
import binascii
import io
import wave
from dataclasses import dataclass, field
from typing import Literal

from fastapi import Request

from app.errors import APIError

AudioFormat = Literal["wav", "mp3"]

# Documentation OpenAPI du corps de requête (FastAPI ne sait pas le déduire seul
# puisque l'endpoint lit la requête brute pour accepter deux content-types).
_OPTIONAL_FIELDS = {
    "language_hint": {
        "type": "string",
        "enum": ["bci", "dyu"],
        "description": "Optionnel. Indice de langue (utilisé par le moteur mock).",
    },
    "voice_id": {"type": "string", "description": "Optionnel. Voix de synthèse (pipeline)."},
}
AUDIO_REQUEST_BODY = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["audio"],
                    "properties": {
                        "audio": {"type": "string", "format": "binary", "description": ".wav ou .mp3"},
                        **_OPTIONAL_FIELDS,
                    },
                }
            },
            "application/json": {
                "schema": {
                    "type": "object",
                    "required": ["audio_base64"],
                    "properties": {
                        "audio_base64": {"type": "string", "description": "Audio .wav ou .mp3 encodé en Base64"},
                        **_OPTIONAL_FIELDS,
                    },
                }
            },
        },
    }
}


@dataclass
class AudioInput:
    data: bytes
    format: AudioFormat
    options: dict[str, str] = field(default_factory=dict)


def detect_audio_format(data: bytes) -> AudioFormat | None:
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "wav"
    # MP3 : balise ID3 en tête, ou directement une trame MPEG (11 bits de synchro à 1).
    if data[:3] == b"ID3" or (len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
        return "mp3"
    return None


def validate_audio(data: bytes, max_bytes: int) -> AudioFormat:
    if not data:
        raise APIError(400, "empty_audio", "Le fichier audio est vide.")
    if len(data) > max_bytes:
        raise APIError(413, "audio_too_large", f"Audio trop volumineux (max {max_bytes // (1024 * 1024)} Mo).")
    audio_format = detect_audio_format(data)
    if audio_format is None:
        raise APIError(415, "unsupported_audio_format", "Format audio non supporté : seuls .wav et .mp3 sont acceptés.")
    return audio_format


async def read_audio_input(request: Request, max_bytes: int) -> AudioInput:
    content_type = request.headers.get("content-type", "")
    options: dict[str, str] = {}

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("audio")
        if upload is None or isinstance(upload, str):
            raise APIError(400, "missing_audio", "Champ fichier 'audio' manquant.")
        data = await upload.read()
        options = {k: v for k, v in form.items() if k != "audio" and isinstance(v, str)}

    elif content_type.startswith("application/json"):
        try:
            body = await request.json()
        except ValueError as exc:
            raise APIError(400, "invalid_json", "Corps JSON invalide.") from exc
        if not isinstance(body, dict) or not isinstance(body.get("audio_base64"), str):
            raise APIError(400, "missing_audio", "Champ 'audio_base64' manquant.")
        encoded = body["audio_base64"]
        # Vérification de taille avant décodage (Base64 ≈ 4/3 de la taille binaire).
        if len(encoded) > max_bytes * 4 // 3 + 4:
            raise APIError(413, "audio_too_large", f"Audio trop volumineux (max {max_bytes // (1024 * 1024)} Mo).")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise APIError(400, "invalid_base64", "Le champ 'audio_base64' n'est pas du Base64 valide.") from exc
        options = {k: v for k, v in body.items() if k != "audio_base64" and isinstance(v, str)}

    else:
        raise APIError(
            415,
            "unsupported_content_type",
            "Content-Type attendu : multipart/form-data ou application/json.",
        )

    hint = options.get("language_hint")
    if hint is not None and hint not in ("bci", "dyu"):
        raise APIError(422, "invalid_language_hint", "language_hint doit valoir 'bci' ou 'dyu'.")

    return AudioInput(data=data, format=validate_audio(data, max_bytes), options=options)


def pcm16_to_wav(frames: bytes, sample_rate: int) -> bytes:
    """Emballe des échantillons PCM 16 bits mono dans un fichier WAV."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(frames)
    return buffer.getvalue()
