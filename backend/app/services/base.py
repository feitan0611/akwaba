"""Interfaces des briques IA — CONTRAT entre l'équipe backend et les équipes IA.

Chaque brique (STT/LID, traduction, LLM, TTS) est une classe abstraite. L'API ne dépend
que de ces interfaces : on peut remplacer une implémentation (mock → vrai modèle) sans
toucher aux endpoints. Toute nouvelle implémentation doit respecter ces signatures.

Chaque brique DÉCLARE les langues qu'elle prend en charge (`languages`). Une demande dans
une autre langue lève `LanguageNotSupportedError`, que l'API transforme en erreur claire :
on ne renvoie jamais un résultat inventé pour une langue non couverte.

Les méthodes sont synchrones (les modèles sont CPU/GPU-bound) : l'API les exécute
dans un pool de threads.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from app.audio import AudioInput
from app.languages import ALL_LANGUAGES

if TYPE_CHECKING:
    from app.rag.index import Passage

TASK_NAMES = {
    "stt": "la reconnaissance vocale",
    "translate": "la traduction",
    "ask": "la génération de réponse",
    "tts": "la synthèse vocale",
}


# --- Erreurs métier (converties en réponses HTTP dans app/errors.py) --------------------


class EngineError(Exception):
    """Erreur d'une brique IA."""


class LanguageNotSupportedError(EngineError):
    def __init__(self, task: str, language: str) -> None:
        self.task = task
        self.language = language
        name = ALL_LANGUAGES.get(language, language)
        super().__init__(
            f"Le {name} n'est pas encore pris en charge pour {TASK_NAMES.get(task, task)} : "
            "aucun modèle disponible pour cette langue."
        )


class LanguageRequiredError(EngineError):
    def __init__(self) -> None:
        super().__init__(
            "La détection automatique de la langue n'est pas activée sur ce serveur : "
            "précisez la langue (champ language_hint)."
        )


class EngineUnavailableError(EngineError):
    """Un service dont dépend la brique (ex. serveur Ollama) ne répond pas."""


class InvalidInputError(EngineError):
    """Entrée techniquement valide mais inexploitable (audio illisible, trop court, sans parole…)."""


# --- Interfaces -------------------------------------------------------------------------


class Brick(ABC):
    name: str
    task: str
    languages: frozenset[str]

    def check_language(self, language: str) -> None:
        if language not in self.languages:
            raise LanguageNotSupportedError(self.task, language)

    def warmup(self) -> None:  # noqa: B027 — no-op volontaire, surchargé par les moteurs à modèles
        """Charge les modèles à l'avance (optionnel). Par défaut : rien à charger."""


@dataclass
class Transcription:
    text: str
    language: str  # code ISO 639-3 : "bci" | "dyu"
    confidence: float  # entre 0 et 1 : confiance de la détection de langue
    language_source: Literal["detected", "provided"] = "detected"


class SpeechRecognizer(Brick):
    """STT/ASR + détection de langue (endpoint /detect)."""

    task = "stt"
    detects_language: bool = True

    @abstractmethod
    def transcribe(self, audio: AudioInput) -> Transcription: ...


class Translator(Brick):
    """Traduction automatique texte → texte (endpoint /translate)."""

    task = "translate"

    @abstractmethod
    def translate(self, text: str, source: str, target: str) -> str: ...


class Responder(Brick):
    """Génération de la réponse à une requête, en langue pivot (endpoint /ask).

    `passages` : extraits de la base de connaissances retrouvés par le RAG (éventuellement
    aucun). La réponse doit s'appuyer dessus quand ils sont pertinents.
    """

    task = "ask"

    @abstractmethod
    def answer(self, question: str, language: str, passages: Sequence["Passage"] = ()) -> str: ...


class SpeechSynthesizer(Brick):
    """TTS : texte → audio WAV (endpoint /speech)."""

    task = "tts"

    @abstractmethod
    def synthesize(self, text: str, language: str, voice_id: str | None = None) -> bytes:
        """Retourne le contenu d'un fichier WAV."""
