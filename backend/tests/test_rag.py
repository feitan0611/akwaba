"""Tests du RAG : documents, découpage, embeddings, index, recherche et API."""

import time

import pytest

from app.config import PROJECT_ROOT, Settings
from app.rag.documents import Document, KnowledgeBaseError, load_documents, parse_front_matter, split_into_chunks
from app.rag.embeddings import HashEmbedder, OllamaEmbedder
from app.rag.index import Retriever, VectorIndex
from app.services.base import EngineUnavailableError

API = "/api/v1"


# --- Documents ------------------------------------------------------------------------------


def test_front_matter():
    meta, body = parse_front_matter("---\ntitle: Titre\nsource: Moi\n---\n# A\ntexte")
    assert meta == {"title": "Titre", "source": "Moi"}
    assert body.startswith("# A")


def test_documents_without_source_are_rejected(tmp_path):
    (tmp_path / "doc.md").write_text("---\ntitle: Sans source\n---\ntexte", encoding="utf-8")
    with pytest.raises(KnowledgeBaseError, match="source"):
        load_documents(tmp_path)


def test_templates_and_readme_are_ignored(tmp_path):
    (tmp_path / "_modele.md").write_text("pas d'en-tête", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Aide", encoding="utf-8")
    assert load_documents(tmp_path) == []


def test_chunks_follow_sections_and_keep_context():
    doc = Document("d.md", "Titre", "src", "# Partie A\nun\n\ndeux\n# Partie B\ntrois")
    chunks = split_into_chunks(doc)
    assert [c.section for c in chunks] == ["Partie A", "Partie B"]
    assert chunks[0].text.startswith("Titre — Partie A\n")  # contexte répété dans chaque passage


def test_long_sections_are_split_under_the_limit():
    body = "# S\n" + "\n\n".join(f"Phrase numéro {i} assez longue pour remplir le passage." for i in range(60))
    chunks = split_into_chunks(Document("d.md", "T", "src", body), max_chars=300)
    assert len(chunks) > 1
    assert all(len(c.text) <= 300 + len("T — S\n") for c in chunks)


def test_project_knowledge_base_is_valid():
    """Les documents réels de knowledge/ doivent toujours respecter le format."""
    documents = load_documents(PROJECT_ROOT / "knowledge")
    assert documents, "la base de connaissances du projet est vide"


# --- Embeddings et recherche ------------------------------------------------------------------


def test_hash_embedder_is_normalized_and_deterministic():
    [a], [b] = HashEmbedder().embed(["Santé et paludisme"]), HashEmbedder().embed(["Santé et paludisme"])
    assert a == b
    assert abs(sum(v * v for v in a) - 1) < 1e-9


def test_retriever_finds_the_relevant_document(knowledge_dir, tmp_path):
    retriever = Retriever(knowledge_dir, tmp_path / "idx", HashEmbedder())
    passages = retriever.retrieve("Comment se protéger des moustiques la nuit ?")
    assert passages and passages[0].doc_id == "paludisme.md"
    assert passages[0].section == "Moustiquaire"
    assert all(p.doc_id != "riz.md" for p in passages)


def test_irrelevant_question_returns_nothing(knowledge_dir, tmp_path):
    retriever = Retriever(knowledge_dir, tmp_path / "idx", HashEmbedder())
    assert retriever.retrieve("Quel est le score du match de football ?") == []


def test_index_is_saved_and_rebuilt_when_documents_change(knowledge_dir, tmp_path):
    retriever = Retriever(knowledge_dir, tmp_path / "idx", HashEmbedder())
    first = retriever.index()
    assert retriever.index_path.is_file()
    assert VectorIndex.load(retriever.index_path).fingerprint == first.fingerprint
    assert retriever.index() is first  # rien n'a changé : pas de reconstruction

    time.sleep(0.01)
    (knowledge_dir / "eau.md").write_text("---\ntitle: Eau potable\nsource: test\n---\nFaire bouillir l'eau.")
    rebuilt = retriever.index()
    assert rebuilt is not first
    assert any(c.doc_id == "eau.md" for c in rebuilt.chunks)


def test_empty_knowledge_base(tmp_path):
    retriever = Retriever(tmp_path / "vide", tmp_path / "idx", HashEmbedder())
    assert retriever.retrieve("n'importe quoi") == []


def test_ollama_embedder_reports_unavailable_service():
    with pytest.raises(EngineUnavailableError, match="ollama pull bge-m3"):
        OllamaEmbedder("http://127.0.0.1:9", "bge-m3").embed(["test"])


# --- API ------------------------------------------------------------------------------------


def test_ask_returns_sources(client):
    response = client.post(f"{API}/ask", json={"text": "Faut-il dormir sous une moustiquaire ?"})
    body = response.json()
    assert response.status_code == 200, body
    assert body["sources"][0]["title"] == "Prévention du paludisme"
    assert "Prévention du paludisme" in body["text"]  # le mock cite les passages reçus


def test_pipeline_includes_retrieval_step(client, wav_bytes):
    body = client.post(f"{API}/pipeline", files={"audio": ("q.wav", wav_bytes, "audio/wav")}).json()
    assert "retrieve" in body["timings_ms"]
    assert "sources" in body


def test_knowledge_status(client):
    body = client.get(f"{API}/knowledge").json()
    assert body["embedder"] == "hash-bow-512"
    assert {d["doc_id"] for d in body["documents"]} == {"paludisme.md", "riz.md"}


def test_knowledge_search_with_scores(client):
    body = client.post(f"{API}/knowledge/search", json={"query": "semer le riz", "min_score": -1}).json()
    assert body["results"][0]["doc_id"] == "riz.md"
    scores = [r["score"] for r in body["results"]]
    assert scores == sorted(scores, reverse=True)


def test_knowledge_reindex(client):
    assert client.post(f"{API}/knowledge/reindex").json()["chunks"] == 3


def test_invalid_document_gives_clear_error(client, knowledge_dir):
    (knowledge_dir / "casse.md").write_text("---\ntitle: Sans source\n---\ntexte", encoding="utf-8")
    response = client.get(f"{API}/knowledge")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "knowledge_base_error"
    assert "casse.md" in response.json()["error"]["message"]


def test_rag_can_be_disabled(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app

    app = create_app(Settings(_env_file=None, serve_demo=False, rag_enabled=False))
    client = TestClient(app)
    assert client.get(f"{API}/knowledge").json()["error"]["code"] == "rag_disabled"
    assert client.post(f"{API}/ask", json={"text": "Bonjour"}).json()["sources"] == []


def test_env_example_is_loadable():
    """Le fichier .env.example fourni à l'équipe doit toujours être valide tel quel."""
    settings = Settings(_env_file=PROJECT_ROOT / ".env.example")
    assert settings.rag_min_score is None


def test_env_file_is_found_from_any_directory():
    """Le .env est cherché à la racine du projet, pas dans le dossier courant."""
    assert Settings.model_config["env_file"] == PROJECT_ROOT / ".env"
