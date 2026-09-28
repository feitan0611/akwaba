"""Modèles d'embedding : texte → vecteur, pour comparer le sens des textes.

- OllamaEmbedder : vrai modèle d'embedding (bge-m3 par défaut, multilingue) servi par Ollama.
- HashEmbedder   : embedding lexical très simple (sac de mots haché), sans dépendance ni
                   téléchargement. Utilisé par le moteur mock et les tests. Il ne capte que les
                   mots en commun, pas le sens : suffisant pour tester la mécanique du RAG.

Tous les vecteurs sont normalisés (norme 1) : le produit scalaire est la similarité cosinus.
"""

import hashlib
import math
import re
import unicodedata
from abc import ABC, abstractmethod

from app.services.base import EngineUnavailableError


def normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


class Embedder(ABC):
    name: str
    # Score cosinus minimal pour qu'un passage soit jugé pertinent. Il dépend du modèle
    # (les échelles de similarité varient) : à ajuster en testant avec /knowledge/search.
    default_min_score: float

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...


# Mots trop fréquents pour aider à distinguer les passages.
STOPWORDS = frozenset(
    "le la les un une des de du d l et ou a au aux en dans sur pour par avec sans ce cet cette ces "
    "est sont etre il elle ils elles on je tu nous vous me te se ne pas plus que qui quoi quel quelle "
    "quels quelles comment ou y son sa ses leur leurs mon ma mes ton ta tes notre votre".split()
)


class HashEmbedder(Embedder):
    name = "hash-bow-512"
    default_min_score = 0.1
    dimensions = 512

    @staticmethod
    def tokens(text: str) -> list[str]:
        text = unicodedata.normalize("NFKD", text.lower())
        text = "".join(c for c in text if not unicodedata.combining(c))  # « santé » ≈ « sante »
        return [t for t in re.findall(r"[a-z0-9]{2,}", text) if t not in STOPWORDS]

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for token in self.tokens(text):
                # md5 plutôt que hash() : même résultat d'une exécution à l'autre.
                bucket = int(hashlib.md5(token.encode()).hexdigest(), 16) % self.dimensions
                vector[bucket] += 1.0
            vectors.append(normalize(vector))
        return vectors


class OllamaEmbedder(Embedder):
    default_min_score = 0.45
    batch_size = 16

    def __init__(self, base_url: str, model: str, timeout_s: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self.name = f"ollama:{model}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx

        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            try:
                response = httpx.post(
                    f"{self.base_url}/api/embed", json={"model": self.model, "input": batch}, timeout=self.timeout_s
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise EngineUnavailableError(
                    f"Le modèle d'embedding ne répond pas (Ollama, modèle {self.model}). Vérifiez qu'Ollama "
                    f"est lancé et que le modèle est téléchargé : ollama pull {self.model}"
                ) from exc
            vectors.extend(normalize(v) for v in response.json()["embeddings"])
        return vectors
