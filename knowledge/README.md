# Base de connaissances (RAG)

Les documents de ce dossier sont **découpés en passages**, transformés en **vecteurs**
(embeddings), puis **consultés avant chaque réponse** : le LLM s'appuie sur les passages
les plus proches de la question, et l'API renvoie les **sources** utilisées.

## Ajouter un document

1. Copier [`_modele.md`](_modele.md) (les fichiers commençant par `_` ne sont pas indexés).
2. Remplir l'en-tête — **`title` et `source` sont obligatoires**.
3. Écrire en **français** (langue pivot), en phrases simples, avec des titres `#` par sujet.
4. Enregistrer : **l'index se reconstruit automatiquement** à la question suivante.

Les sous-dossiers sont permis (ex. `sante/`, `agriculture/`, `demarches/`).

## Règles de qualité — mêmes principes que le corpus audio

- **Aucune information sans source vérifiable** (organisme officiel, document public, personne
  interrogée avec son accord). Pas de source → pas de document.
- **Ne rien inventer** : un chiffre, une adresse ou un horaire faux sera répété avec assurance
  par l'assistant. Mieux vaut un document court et juste.
- **Dater** les informations qui changent (prix, horaires) avec `updated:` et les tenir à jour.
- Informations médicales : rester sur de la prévention et de l'orientation (« consultez un
  agent de santé »), jamais de diagnostic ni de posologie.
- Un sujet par section : les passages sont découpés selon les titres `#`.

## Tester

Depuis `backend/` :

```bash
python -m app.rag list                        # documents indexés
python -m app.rag search "quelles langues ?"  # passages retrouvés, avec leur score
python -m app.rag build                       # forcer la reconstruction de l'index
```

Ou dans la documentation interactive (`/docs`) : `GET /api/v1/knowledge` et
`POST /api/v1/knowledge/search`.

Le **score** est la similarité cosinus entre la question et le passage. Seuls les passages
au-dessus du seuil (`min_score`) sont transmis au LLM ; `search` affiche aussi les autres
(marqués `·`) pour aider à régler ce seuil (`LANGCI_RAG_MIN_SCORE`).

## Embeddings

| Moteur (`LANGCI_ENGINE`) | Embedding | Remarque |
|--------------------------|-----------|----------|
| `local` | `bge-m3` via Ollama (`ollama pull bge-m3`) | Multilingue, compare le **sens** |
| `mock`  | Sac de mots haché | Sans téléchargement ; ne compare que les **mots communs** |

Changer de modèle : `LANGCI_EMBEDDING_MODEL=...` (un index séparé est construit par modèle).
