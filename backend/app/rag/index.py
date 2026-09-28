"""Index vectoriel et recherche de passages (le « R » de RAG).

L'index est un simple fichier JSON (vecteurs + passages) : pour une base de quelques
centaines de passages, une recherche exhaustive en Python pur prend quelques millisecondes.
Une base vectorielle dédiée (FAISS, Chroma…) ne se justifierait qu'au-delà de dizaines de
milliers de passages.

L'index est reconstruit automatiquement quand un document est ajouté, modifié ou supprimé,
ou quand on change de modèle d'embedding (empreinte comparée à chaque recherche).
"""

import hashlib
import json
import logging
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

from app.rag.documents import Chunk, load_documents, split_into_chunks
from app.rag.embeddings import Embedder

logger = logging.getLogger(__name__)
INDEX_FORMAT = 1


@dataclass(frozen=True)
class Passage:
    chunk_id: str
    doc_id: str
    title: str
    source: str
    section: str
    text: str
    score: float


def knowledge_fingerprint(directory: Path, embedder_name: str) -> str:
    """Empreinte peu coûteuse (noms, tailles, dates des fichiers) : détecte tout changement."""
    digest = hashlib.sha256(f"{INDEX_FORMAT}|{embedder_name}".encode())
    if directory.is_dir():
        for path in sorted(directory.rglob("*.md")):
            stat = path.stat()
            digest.update(f"{path.relative_to(directory).as_posix()}|{stat.st_size}|{stat.st_mtime_ns}".encode())
    return digest.hexdigest()


class VectorIndex:
    def __init__(self, embedder_name: str, fingerprint: str, chunks: list[Chunk], vectors: list[list[float]]):
        self.embedder_name = embedder_name
        self.fingerprint = fingerprint
        self.chunks = chunks
        self.vectors = vectors

    @classmethod
    def build(cls, directory: Path, embedder: Embedder) -> "VectorIndex":
        fingerprint = knowledge_fingerprint(directory, embedder.name)
        chunks = [chunk for document in load_documents(directory) for chunk in split_into_chunks(document)]
        vectors = embedder.embed([chunk.text for chunk in chunks]) if chunks else []
        return cls(embedder.name, fingerprint, chunks, vectors)

    def search(self, query_vector: list[float], top_k: int, min_score: float) -> list[Passage]:
        scored = [
            (sum(q * v for q, v in zip(query_vector, vector, strict=True)), chunk)
            for chunk, vector in zip(self.chunks, self.vectors, strict=True)
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            Passage(**asdict(chunk), score=round(score, 4)) for score, chunk in scored[:top_k] if score >= min_score
        ]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": INDEX_FORMAT,
            "embedder": self.embedder_name,
            "fingerprint": self.fingerprint,
            "chunks": [asdict(chunk) for chunk in self.chunks],
            "vectors": self.vectors,
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(path)  # écriture atomique : jamais d'index à moitié écrit

    @classmethod
    def load(cls, path: Path) -> "VectorIndex | None":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("format") != INDEX_FORMAT:
                return None
            chunks = [Chunk(**chunk) for chunk in payload["chunks"]]
            return cls(payload["embedder"], payload["fingerprint"], chunks, payload["vectors"])
        except (OSError, ValueError, KeyError, TypeError):
            return None


class Retriever:
    def __init__(
        self,
        knowledge_dir: Path,
        index_dir: Path,
        embedder: Embedder,
        top_k: int = 3,
        min_score: float | None = None,
    ) -> None:
        self.knowledge_dir = knowledge_dir
        self.embedder = embedder
        self.top_k = top_k
        self.min_score = embedder.default_min_score if min_score is None else min_score
        safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in embedder.name)
        self.index_path = index_dir / f"{safe_name}.json"
        self._index: VectorIndex | None = None
        self._lock = threading.Lock()

    def index(self, force_rebuild: bool = False) -> VectorIndex:
        with self._lock:
            fingerprint = knowledge_fingerprint(self.knowledge_dir, self.embedder.name)
            if not force_rebuild:
                if self._index is not None and self._index.fingerprint == fingerprint:
                    return self._index
                stored = VectorIndex.load(self.index_path)
                if stored is not None and stored.fingerprint == fingerprint:
                    self._index = stored
                    return stored
            logger.info("Construction de l'index RAG (%s)…", self.embedder.name)
            self._index = VectorIndex.build(self.knowledge_dir, self.embedder)
            self._index.save(self.index_path)
            logger.info("Index RAG : %d passage(s).", len(self._index.chunks))
            return self._index

    def retrieve(self, query: str, top_k: int | None = None, min_score: float | None = None) -> list[Passage]:
        index = self.index()
        if not index.chunks:
            return []
        [query_vector] = self.embedder.embed([query])
        return index.search(
            query_vector,
            top_k=top_k or self.top_k,
            min_score=self.min_score if min_score is None else min_score,
        )
