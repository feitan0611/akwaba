"""Configuration centralisée, lue depuis les variables d'environnement (préfixe LANGCI_) ou le fichier .env.

Aucun secret ne doit être écrit en dur dans le code : voir .env.example.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="LANGCI_", extra="ignore")

    app_name: str = "API Langues Ivoiriennes (Baoulé / Dioula)"
    environment: str = "dev"

    # Moteur IA utilisé derrière l'API. "mock" = implémentations factices pour développer
    # l'API et le frontend avant que les modèles soient prêts.
    engine: str = "mock"

    # Langue pivot utilisée par le LLM (le LLM ne comprend pas le Baoulé/Dioula directement).
    pivot_language: str = "fra"

    max_audio_mb: float = 10.0

    cors_origins: list[str] = ["*"]
    serve_demo: bool = True

    # Secrets éventuels (LLM hébergé, etc.) — uniquement via l'environnement.
    llm_api_key: str | None = None

    @property
    def max_audio_bytes(self) -> int:
        return int(self.max_audio_mb * 1024 * 1024)


@lru_cache
def get_settings() -> Settings:
    return Settings()
