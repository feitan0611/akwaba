"""Schémas Pydantic des requêtes/réponses — ils génèrent aussi la documentation /docs."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.languages import Language, LocalLanguage

# Texte non vide après suppression des espaces, longueur bornée (validation des entrées).
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    engine: str


class LanguageInfo(BaseModel):
    code: str
    name: str
    role: Literal["local", "pivot"]


class DetectResponse(BaseModel):
    text: str = Field(description="Texte transcrit")
    language: LocalLanguage = Field(description="Langue détectée (ISO 639-3)")
    confidence: float = Field(ge=0, le=1, description="Score de confiance de la détection")
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


class AskRequest(BaseModel):
    text: Text
    language: Language = Field(default="fra", description="Langue de la question (langue pivot)")


class AskResponse(BaseModel):
    text: str
    language: Language
    engine: str


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
    timings_ms: dict[str, float]
