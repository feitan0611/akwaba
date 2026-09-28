"""Configuration centralisée, lue depuis les variables d'environnement (préfixe LANGCI_) ou le fichier .env.

Aucun secret ne doit être écrit en dur dans le code : voir .env.example.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="LANGCI_", extra="ignore")

    app_name: str = "API Langues Ivoiriennes (Baoulé / Dioula)"
    environment: str = "dev"

    # Moteur IA utilisé derrière l'API :
    #   "mock"  = implémentations factices (développement, tests, CI)
    #   "local" = vrais modèles sur la machine (voir app/services/local.py)
    engine: Literal["mock", "local"] = "mock"

    # Moteur local : charger les modèles dès le démarrage (en tâche de fond) plutôt qu'à la
    # première requête. Le premier chargement peut prendre plusieurs minutes.
    preload_models: bool = False

    # LLM servi par Ollama (moteur local)
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"

    # Langue pivot utilisée par le LLM (le LLM ne comprend pas le Baoulé/Dioula directement).
    pivot_language: Literal["fra", "eng"] = "fra"

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
