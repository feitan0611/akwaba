"""Assemblage des briques IA selon la configuration (LANGCI_ENGINE)."""

import logging
from dataclasses import dataclass

from app.config import Settings
from app.languages import LOCAL_LANGUAGES
from app.rag.embeddings import HashEmbedder, OllamaEmbedder
from app.rag.index import Retriever
from app.services.base import Responder, SpeechRecognizer, SpeechSynthesizer, Translator
from app.services.mock import MockResponder, MockSpeechRecognizer, MockSpeechSynthesizer, MockTranslator

logger = logging.getLogger(__name__)


@dataclass
class Engines:
    recognizer: SpeechRecognizer
    translator: Translator
    responder: Responder
    synthesizer: SpeechSynthesizer
    pivot_language: str
    retriever: Retriever | None = None

    @property
    def bricks(self) -> tuple:
        return (self.recognizer, self.translator, self.responder, self.synthesizer)

    def capabilities(self) -> dict:
        """Ce que le moteur sait réellement faire, langue par langue (exposé par /health)."""
        pivot = self.pivot_language
        languages = {}
        for code in LOCAL_LANGUAGES:
            support = {
                "stt": code in self.recognizer.languages,
                "translate": code in self.translator.languages and pivot in self.translator.languages,
                "ask": pivot in self.responder.languages,
                "tts": code in self.synthesizer.languages,
            }
            languages[code] = {**support, "full": all(support.values())}
        return {"language_detection": self.recognizer.detects_language, "languages": languages}

    def warmup(self) -> None:
        """Charge tous les modèles (appelé en tâche de fond au démarrage si demandé)."""
        for brick in self.bricks:
            try:
                brick.warmup()
            except Exception:  # un échec ici ne doit pas empêcher le serveur de tourner
                logger.exception("Échec du préchargement de %s", brick.name)
        if self.retriever is not None:
            try:
                self.retriever.index()
            except Exception:
                logger.exception("Échec de la construction de l'index RAG")

    def retrieve(self, question: str) -> list:
        """Passages de la base de connaissances pertinents pour la question (vide sans RAG)."""
        return self.retriever.retrieve(question) if self.retriever is not None else []


def build_retriever(settings: Settings) -> Retriever | None:
    """RAG : embedding réel (Ollama) avec le moteur local, lexical avec le moteur mock."""
    if not settings.rag_enabled:
        return None
    if settings.engine == "local":
        embedder = OllamaEmbedder(settings.ollama_url, settings.embedding_model)
    else:
        embedder = HashEmbedder()
    return Retriever(
        settings.knowledge_dir,
        settings.rag_index_dir,
        embedder,
        top_k=settings.rag_top_k,
        min_score=settings.rag_min_score,
    )


def build_engines(settings: Settings) -> Engines:
    retriever = build_retriever(settings)
    if settings.engine == "mock":
        return Engines(
            recognizer=MockSpeechRecognizer(),
            translator=MockTranslator(),
            responder=MockResponder(),
            synthesizer=MockSpeechSynthesizer(),
            pivot_language=settings.pivot_language,
            retriever=retriever,
        )
    if settings.engine == "local":
        # Import ici : le module ne charge aucun modèle, mais inutile de l'importer en mode mock.
        from app.services.local import (
            MMSSpeechRecognizer,
            MMSSpeechSynthesizer,
            NLLBTranslator,
            OllamaResponder,
            configure_model_hub,
        )

        configure_model_hub(settings.models_offline)

        return Engines(
            recognizer=MMSSpeechRecognizer(),
            translator=NLLBTranslator(),
            responder=OllamaResponder(settings.ollama_url, settings.ollama_model),
            synthesizer=MMSSpeechSynthesizer(),
            pivot_language=settings.pivot_language,
            retriever=retriever,
        )
    raise ValueError(f"Moteur IA inconnu : {settings.engine!r} (valeurs possibles : mock, local)")
