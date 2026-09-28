"""Configuration centralisée, lue depuis les variables d'environnement (préfixe LANGCI_) ou le fichier .env.

Aucun secret ne doit être écrit en dur dans le code : voir .env.example.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # .env à la racine du projet, quel que soit le dossier d'où le serveur est lancé.
    # env_ignore_empty : « LANGCI_X= » (valeur vide) signifie « valeur par défaut », pas une chaîne vide.
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_prefix="LANGCI_", extra="ignore", env_ignore_empty=True
    )

    app_name: str = "API Langues Ivoiriennes (Baoulé / Dioula)"
    environment: str = "dev"

    # Moteur IA utilisé derrière l'API :
    #   "mock"  = implémentations factices (développement, tests, CI)
    #   "local" = vrais modèles sur la machine (voir app/services/local.py)
    engine: Literal["mock", "local"] = "mock"

    # Moteur local : charger les modèles dès le démarrage (en tâche de fond) plutôt qu'à la
    # première requête. Le premier chargement peut prendre plusieurs minutes.
    preload_models: bool = False

    # Moteur local : charger les modèles depuis le cache local, sans contacter Hugging Face.
    # Plus rapide et plus fiable (certains antivirus bloquent ces requêtes, ce qui figeait le
    # chargement). Les modèles doivent alors être téléchargés avant : python -m app.download_models
    models_offline: bool = True

    # LLM servi par Ollama (moteur local)
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"

    # RAG : base de connaissances interrogée avant chaque réponse du LLM (voir knowledge/README.md)
    rag_enabled: bool = True
    knowledge_dir: Path = PROJECT_ROOT / "knowledge"
    rag_index_dir: Path = PROJECT_ROOT / "data" / "rag_index"
    # Modèle d'embedding servi par Ollama (moteur local). Le moteur mock utilise un embedding lexical.
    embedding_model: str = "bge-m3"
    rag_top_k: int = 3
    # Score de similarité minimal d'un passage ; vide = valeur par défaut du modèle d'embedding.
    rag_min_score: float | None = None

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
