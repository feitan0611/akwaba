"""Assemblage des briques IA selon la configuration (LANGCI_ENGINE)."""

from dataclasses import dataclass

from app.config import Settings
from app.services.base import Responder, SpeechRecognizer, SpeechSynthesizer, Translator
from app.services.mock import MockResponder, MockSpeechRecognizer, MockSpeechSynthesizer, MockTranslator


@dataclass
class Engines:
    recognizer: SpeechRecognizer
    translator: Translator
    responder: Responder
    synthesizer: SpeechSynthesizer


def build_engines(settings: Settings) -> Engines:
    if settings.engine == "mock":
        return Engines(
            recognizer=MockSpeechRecognizer(),
            translator=MockTranslator(),
            responder=MockResponder(),
            synthesizer=MockSpeechSynthesizer(),
        )
    # Les vrais moteurs seront ajoutés ici après le benchmark (voir docs/05-strategie-ml.md).
    raise ValueError(f"Moteur IA inconnu : {settings.engine!r}")
