"""RAG (Retrieval-Augmented Generation) : le LLM s'appuie sur la base de connaissances du projet.

    knowledge/*.md ──découpage──▶ passages ──embedding──▶ index vectoriel (data/rag_index/)
    question ──embedding──▶ recherche des passages les plus proches ──▶ LLM (+ sources)

Voir knowledge/README.md pour ajouter des documents, et docs/adr/0004-rag.md pour les choix.
"""
