"""Interfaces des briques IA — CONTRAT entre l'équipe backend et les équipes IA.

Chaque brique (STT/LID, traduction, LLM, TTS) est une classe abstraite. L'API ne dépend
que de ces interfaces : on peut remplacer une implémentation (mock → vrai modèle) sans
toucher aux endpoints. Toute nouvelle implémentation doit respecter ces signatures.

Les méthodes sont synchrones (les modèles sont CPU/GPU-bound) : l'API les exécute
dans un pool de threads.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.audio import AudioInput


@dataclass
class Transcription:
    text: str
    language: str  # code ISO 639-3 : "bci" | "dyu"
    confidence: float  # entre 0 et 1 : confiance de la détection de langue


class SpeechRecognizer(ABC):
    """STT/ASR + détection de langue (endpoint /detect)."""

    name: str

    @abstractmethod
    def transcribe(self, audio: AudioInput) -> Transcription: ...


class Translator(ABC):
    """Traduction automatique texte → texte (endpoint /translate)."""

    name: str

    @abstractmethod
    def translate(self, text: str, source: str, target: str) -> str: ...


class Responder(ABC):
    """Génération de la réponse à une requête, en langue pivot (endpoint /ask)."""

    name: str

    @abstractmethod
    def answer(self, question: str, language: str) -> str: ...


class SpeechSynthesizer(ABC):
    """TTS : texte → audio WAV (endpoint /speech)."""

    name: str

    @abstractmethod
    def synthesize(self, text: str, language: str, voice_id: str | None = None) -> bytes:
        """Retourne le contenu d'un fichier WAV."""
