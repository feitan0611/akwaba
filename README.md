# IA vocale Baoulé / Dioula

Prototype d'IA capable de **détecter**, **comprendre** et **répondre vocalement** à des requêtes
orales en **Baoulé** et en **Dioula**, exposé via une **API REST** (FastAPI) et testable grâce à
un **démonstrateur web**.

> **État actuel : prototype.** Deux moteurs IA :
> - **`mock`** (par défaut) : réponses factices, sans téléchargement — pour développer et tester ;
> - **`local`** : vrais modèles open source, **Dioula de bout en bout** ; le Baoulé n'est
>   couvert par aucun modèle public (voir [ADR 0003](docs/adr/0003-choix-des-modeles.md)).
>
> Les réponses s'appuient sur une **base de connaissances** (RAG, dossier [`knowledge/`](knowledge/README.md)).

## Démarrage rapide

Prérequis : Python ≥ 3.11.

```bash
python -m venv .venv
```
```bash
.venv\Scripts\activate
```
(sous Linux/macOS : `source .venv/bin/activate`)
```bash
pip install -r requirements-dev.txt
```
```bash
cp .env.example .env
```
```bash
uvicorn app.main:app --reload --app-dir backend
```

| URL | Contenu |
|-----|---------|
| http://127.0.0.1:8000/docs | Documentation interactive de l'API |
| http://127.0.0.1:8000/demo/ | Démonstrateur web |
| http://127.0.0.1:8000/api/v1/health | État du service |

Tests et qualité (depuis la racine) :

```bash
pytest
```
```bash
ruff check . && ruff format --check .
```

### Activer les vrais modèles (moteur `local`)

Nécessite [Ollama](https://ollama.com) et ≈ 9 Go de téléchargements (licence non commerciale
pour MMS et NLLB).

```bash
pip install -r backend/requirements-ml.txt
```
```bash
ollama pull qwen2.5:3b
```
```bash
ollama pull bge-m3
```
```bash
cd backend && python -m app.download_models
```

Puis dans `.env` : `LANGCI_ENGINE=local`, et redémarrer le serveur.

## Flux principal

```
Audio (dyu) → transcription → traduction vers le français → recherche dans la base de
connaissances (RAG) → LLM → traduction vers le dioula → synthèse vocale → Audio
```

## Documentation

| Document | Contenu |
|----------|---------|
| [01 — Cadrage](docs/01-cadrage.md) | Périmètre MVP, **points à valider avec le formateur**, critères de réussite |
| [02 — Architecture](docs/02-architecture.md) | Composants, arborescence, interfaces IA |
| [03 — API](docs/03-api.md) | Endpoints, formats, erreurs |
| [04 — Données](docs/04-donnees.md) | Protocole de collecte, consentement, métadonnées, découpage |
| [05 — Stratégie ML](docs/05-strategie-ml.md) | Benchmark, baselines, métriques |
| [06 — Organisation](docs/06-organisation.md) | Rôles, planning, workflow Git, définition de « Terminé » |
| [ADR](docs/adr/README.md) | Registre des décisions |

## Structure

```
backend/    API FastAPI (+ tests)
ml/         Outils data/ML : validation du corpus, découpage, métriques (+ tests)
data/       Corpus — métadonnées versionnées, audio hors Git
frontend/   Démonstrateur web (servi sur /demo/)
docs/       Documentation du projet
```

## Équipe

Projet réalisé par un groupe de 7 apprenants — répartition dans [docs/06-organisation.md](docs/06-organisation.md).

## Limites

Ce prototype traite des langues **peu dotées** en ressources numériques. Les performances
dépendront directement du volume et de la qualité des données collectées ; les limites observées
seront documentées dans le rapport d'évaluation.
