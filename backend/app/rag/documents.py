"""Chargement des documents de la base de connaissances et découpage en passages.

Format d'un document (fichier Markdown dans knowledge/) :

    ---
    title: Titre du document
    source: D'où vient l'information (organisme, URL, personne interrogée…)
    updated: 2026-09-28
    ---
    # Section
    Texte…

`title` et `source` sont obligatoires : comme pour le corpus audio, aucune information sans
source. Les fichiers dont le nom commence par « _ » (modèles) et les README sont ignorés.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from app.services.base import EngineError

REQUIRED_FIELDS = ("title", "source")
MAX_CHUNK_CHARS = 800


class KnowledgeBaseError(EngineError):
    """Document mal formé dans la base de connaissances."""


@dataclass(frozen=True)
class Document:
    doc_id: str  # chemin relatif au dossier knowledge/, ex. "sante/paludisme.md"
    title: str
    source: str
    body: str
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Chunk:
    chunk_id: str  # "<doc_id>#<n>"
    doc_id: str
    title: str
    source: str
    section: str
    text: str


def iter_document_paths(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        path for path in directory.rglob("*.md") if not path.name.startswith("_") and path.name.lower() != "readme.md"
    )


def parse_front_matter(raw: str) -> tuple[dict, str]:
    """Sépare l'en-tête `---` (clé: valeur) du corps du document. Pas de YAML complet :
    une clé par ligne suffit, et évite une dépendance."""
    raw = raw.lstrip("﻿")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", raw, flags=re.DOTALL)
    if not match:
        return {}, raw
    metadata = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            key, value = line.split(":", 1)
            metadata[key.strip().lower()] = value.strip()
    return metadata, match.group(2)


def load_documents(directory: Path) -> list[Document]:
    documents = []
    for path in iter_document_paths(directory):
        doc_id = path.relative_to(directory).as_posix()
        metadata, body = parse_front_matter(path.read_text(encoding="utf-8"))
        missing = [name for name in REQUIRED_FIELDS if not metadata.get(name)]
        if missing:
            raise KnowledgeBaseError(
                f"Document « {doc_id} » invalide : champ(s) obligatoire(s) manquant(s) dans l'en-tête : "
                f"{', '.join(missing)}. Voir knowledge/_modele.md."
            )
        if not body.strip():
            raise KnowledgeBaseError(f"Document « {doc_id} » vide.")
        documents.append(
            Document(doc_id=doc_id, title=metadata["title"], source=metadata["source"], body=body, metadata=metadata)
        )
    return documents


def _sections(body: str) -> list[tuple[str, str]]:
    """Découpe le corps selon les titres Markdown : [(titre de section, texte), …]."""
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in body.splitlines():
        heading = re.match(r"^#{1,6}\s+(.*)", line)
        if heading:
            sections.append((heading.group(1).strip(), []))
        else:
            sections[-1][1].append(line)
    return [(title, "\n".join(lines).strip()) for title, lines in sections if "\n".join(lines).strip()]


def split_into_chunks(document: Document, max_chars: int = MAX_CHUNK_CHARS) -> list[Chunk]:
    """Un passage = un ou plusieurs paragraphes d'une même section, sans dépasser max_chars.

    Le titre du document et de la section sont répétés en tête de chaque passage : un passage
    isolé reste compréhensible, pour l'embedding comme pour le LLM.
    """
    chunks: list[Chunk] = []

    def add(section: str, paragraphs: list[str]) -> None:
        header = document.title + (f" — {section}" if section else "")
        chunks.append(
            Chunk(
                chunk_id=f"{document.doc_id}#{len(chunks)}",
                doc_id=document.doc_id,
                title=document.title,
                source=document.source,
                section=section,
                text=f"{header}\n" + "\n\n".join(paragraphs),
            )
        )

    for section, text in _sections(document.body):
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        current: list[str] = []
        for paragraph in paragraphs:
            # Un paragraphe trop long est coupé à la phrase près.
            pieces = [paragraph] if len(paragraph) <= max_chars else re.split(r"(?<=[.!?])\s+", paragraph)
            for piece in pieces:
                if current and len("\n\n".join([*current, piece])) > max_chars:
                    add(section, current)
                    current = []
                current.append(piece)
        if current:
            add(section, current)
    return chunks
