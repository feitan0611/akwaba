"""Outil en ligne de commande pour la base de connaissances (depuis le dossier backend/) :

    python -m app.rag build                 # (re)construire l'index
    python -m app.rag search "ma question"  # tester la recherche, avec les scores
    python -m app.rag list                  # lister les documents indexés

Le moteur d'embedding suit la configuration (.env) : LANGCI_ENGINE=local → Ollama (bge-m3),
LANGCI_ENGINE=mock → embedding lexical simple.
"""

import argparse
import sys

from app.config import get_settings
from app.services.registry import build_retriever


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="python -m app.rag", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="(Re)construire l'index")
    sub.add_parser("list", help="Lister les documents indexés")
    search = sub.add_parser("search", help="Chercher les passages proches d'une question")
    search.add_argument("query")
    search.add_argument("-k", type=int, default=5)
    args = parser.parse_args(argv)

    retriever = build_retriever(get_settings())
    if retriever is None:
        print("Le RAG est désactivé (LANGCI_RAG_ENABLED=false).")
        return 1
    print(f"Embedding : {retriever.embedder.name} — seuil de pertinence : {retriever.min_score}")

    if args.command == "build":
        index = retriever.index(force_rebuild=True)
        print(f"Index construit : {len(index.chunks)} passage(s) → {retriever.index_path}")
    elif args.command == "list":
        index = retriever.index()
        counts: dict[str, int] = {}
        for chunk in index.chunks:
            label = f"{chunk.doc_id} — {chunk.title} (source : {chunk.source})"
            counts[label] = counts.get(label, 0) + 1
        for label, count in counts.items():
            print(f"  {count:>3} passage(s)  {label}")
    else:
        # min_score=-1 : on affiche aussi les passages sous le seuil, pour aider à le régler.
        for passage in retriever.retrieve(args.query, top_k=args.k, min_score=-1):
            flag = "✓" if passage.score >= retriever.min_score else "·"
            print(f"\n{flag} {passage.score:.3f}  {passage.doc_id} › {passage.section or '(début)'}")
            print("   " + passage.text.replace("\n", "\n   ")[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
