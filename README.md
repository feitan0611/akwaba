# IA vocale Baoulé / Dioula

Prototype d'IA capable de **détecter**, **comprendre** et **répondre vocalement** à des requêtes
orales en **Baoulé** et en **Dioula**, exposé via une **API REST** (FastAPI) et testable grâce à
un **démonstrateur web**.

> **État actuel : v0.1 — squelette.** L'API complète fonctionne avec un **moteur factice
> (`mock`)** ; les vrais modèles seront intégrés après la collecte des données et le benchmark.

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
cd backend && uvicorn app.main:app --reload
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

## Flux principal

```
Audio (bci/dyu) → détection + transcription → traduction → français → LLM
               → traduction → langue détectée → synthèse vocale → Audio
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
