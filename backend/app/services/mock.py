"""Implémentations factices (moteur "mock").

But : permettre de développer et tester l'API et le démonstrateur AVANT que les modèles
existent. Elles ne font AUCUN traitement linguistique réel ; toutes les réponses portent
la mention "mock" pour ne jamais être confondues avec de vrais résultats.
"""

import hashlib
import math
import struct

from app.audio import AudioInput, pcm16_to_wav
from app.languages import ALL_LANGUAGES, LOCAL_LANGUAGES
from app.services.base import Responder, SpeechRecognizer, SpeechSynthesizer, Transcription, Translator


class MockSpeechRecognizer(SpeechRecognizer):
    name = "mock-stt"
    languages = frozenset(LOCAL_LANGUAGES)

    def transcribe(self, audio: AudioInput) -> Transcription:
        hint = audio.options.get("language_hint")
        if hint:
            language = hint
        else:
            # Choix déterministe (même audio → même résultat) mais arbitraire.
            language = "bci" if hashlib.sha256(audio.data).digest()[0] % 2 == 0 else "dyu"
        return Transcription(
            text=f"[mock] transcription indisponible ({len(audio.data)} octets, {audio.format})",
            language=language,
            confidence=0.0,
            language_source="provided" if hint else "detected",
        )


class MockTranslator(Translator):
    name = "mock-translator"
    languages = frozenset(ALL_LANGUAGES)

    def translate(self, text: str, source: str, target: str) -> str:
        return f"[mock {source}→{target}] {text}"


class MockResponder(Responder):
    name = "mock-llm"
    languages = frozenset(ALL_LANGUAGES)

    def answer(self, question: str, language: str) -> str:
        return f"[mock réponse en {language}] Vous avez demandé : {question}"


class MockSpeechSynthesizer(SpeechSynthesizer):
    name = "mock-tts"
    languages = frozenset(LOCAL_LANGUAGES)
    sample_rate = 16_000

    def synthesize(self, text: str, language: str, voice_id: str | None = None) -> bytes:
        # Simple bip dont la durée dépend de la longueur du texte (0,5 s à 3 s).
        duration_s = min(3.0, 0.5 + 0.02 * len(text))
        frequency = 440.0 if language == "bci" else 660.0
        n_samples = int(self.sample_rate * duration_s)
        frames = b"".join(
            struct.pack("<h", int(8000 * math.sin(2 * math.pi * frequency * i / self.sample_rate)))
            for i in range(n_samples)
        )
        return pcm16_to_wav(frames, self.sample_rate)
