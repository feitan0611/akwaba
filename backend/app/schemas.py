"""Schémas Pydantic des requêtes/réponses — ils génèrent aussi la documentation /docs."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.languages import Language, LocalLanguage

# Texte non vide après suppression des espaces, longueur bornée (validation des entrées).
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class LanguageSupport(BaseModel):
    stt: bool
    translate: bool
    ask: bool
    tts: bool
    full: bool = Field(description="Chaîne complète audio → audio disponible")


class Capabilities(BaseModel):
    language_detection: bool = Field(description="Détection automatique de la langue disponible")
    languages: dict[str, LanguageSupport]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    engine: str
    pivot_language: Language
    models: dict[str, str] = Field(description="Modèle utilisé par chaque brique")
    capabilities: Capabilities


class LanguageInfo(BaseModel):
    code: str
    name: str
    role: Literal["local", "pivot"]


class DetectResponse(BaseModel):
    text: str = Field(description="Texte transcrit")
    language: LocalLanguage = Field(description="Langue détectée (ISO 639-3)")
    confidence: float = Field(ge=0, le=1, description="Score de confiance de la détection")
    language_source: Literal["detected", "provided"] = Field(
        description="detected : langue détectée par le modèle ; provided : fournie par le client (language_hint)"
    )
    engine: str


class TranslateRequest(BaseModel):
    text: Text
    source: Language
    target: Language

    @model_validator(mode="after")
    def check_languages_differ(self) -> "TranslateRequest":
        if self.source == self.target:
            raise ValueError("source et target doivent être différentes")
        return self


class TranslateResponse(BaseModel):
    text: str
    source: Language
    target: Language
    engine: str


class SourceInfo(BaseModel):
    """Passage de la base de connaissances utilisé pour répondre."""

    doc_id: str = Field(description="Fichier de la base de connaissances (knowledge/)")
    title: str
    section: str
    source: str = Field(description="Origine de l'information")
    score: float = Field(description="Similarité avec la question (cosinus)")


class SearchResult(SourceInfo):
    text: str


class KnowledgeSearchRequest(BaseModel):
    query: Text
    top_k: int = Field(default=5, ge=1, le=20)
    min_score: float | None = Field(
        default=None, description="Seuil de pertinence ; vide = seuil du serveur ; -1 = tout afficher"
    )


class KnowledgeSearchResponse(BaseModel):
    embedder: str
    min_score: float
    results: list[SearchResult]


class KnowledgeDocumentInfo(BaseModel):
    doc_id: str
    title: str
    source: str
    chunks: int


class KnowledgeStatus(BaseModel):
    embedder: str
    min_score: float
    top_k: int
    chunks: int
    documents: list[KnowledgeDocumentInfo]


class AskRequest(BaseModel):
    text: Text
    language: Language = Field(default="fra", description="Langue de la question (langue pivot)")


class AskResponse(BaseModel):
    text: str
    language: Language
    engine: str
    sources: list[SourceInfo] = Field(default_factory=list, description="Passages utilisés (RAG)")


class SpeechRequest(BaseModel):
    text: Text
    language: LocalLanguage
    voice_id: str | None = None


class SpeechResponse(BaseModel):
    audio_base64: str
    format: Literal["wav"] = "wav"
    language: LocalLanguage
    voice_id: str | None
    engine: str


class PipelineResponse(BaseModel):
    detection: DetectResponse
    pivot_language: Language
    question_pivot: str = Field(description="Question traduite en langue pivot")
    answer_pivot: str = Field(description="Réponse du LLM en langue pivot")
    answer_text: str = Field(description="Réponse traduite dans la langue détectée")
    answer_audio_base64: str
    audio_format: Literal["wav"] = "wav"
    sources: list[SourceInfo] = Field(default_factory=list, description="Passages utilisés (RAG)")
    timings_ms: dict[str, float]
