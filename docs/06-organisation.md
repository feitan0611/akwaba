# 06 — Organisation de l'équipe

## 1. Rôles et zones de responsabilité dans le dépôt

| Membre | Pôle | Dossiers principaux | Premier livrable |
|--------|------|---------------------|------------------|
| M1 | Data — Baoulé | `data/`, `ml/dataset.py` | Convention de transcription Baoulé + 1ʳᵉˢ sources |
| M2 | Data — Dioula | `data/`, `ml/dataset.py` | Convention de transcription Dioula + 1ʳᵉˢ sources |
| M3 | LLM / Évaluation | `ml/metrics.py`, `ml/notebooks/` | Benchmark traduction + choix du LLM |
| M4 | IA — STT | `ml/notebooks/`, `services/` (STT) | Benchmark LID + STT |
| M5 | IA — TTS | `ml/notebooks/`, `services/` (TTS) | Benchmark TTS |
| M6 | Frontend / Intégration | `frontend/` | Démonstrateur branché sur l'API mock |
| M7 | Backend / API | `backend/` | API v1 (mock) stabilisée + documentation |

Chaque pôle a un **binôme de relecture** (une PR est relue par quelqu'un d'un autre pôle).

## 2. Planning proposé (sprints d'une semaine — dates à fixer avec le formateur)

| Sprint | Objectif | Livrables | Jalon |
|--------|----------|-----------|-------|
| S0 | **Cadrage** | Cahier des charges validé (points P1–P11 de [01-cadrage.md](01-cadrage.md)), dépôt GitHub en place | ✅ Validation formateur |
| S1 | **Données + benchmark** | Conventions de transcription, `SOURCES.md`, 1ᵉʳ lot annoté ; benchmark des modèles existants | Go / No-go par brique |
| S2 | **Dataset V1 + baselines** | Dataset V1 découpé et gelé ; baselines mesurées | Dataset V1 |
| S3 | **Modèles V1** | Modèles candidats évalués vs baselines | Modèle V1 |
| S4 | **Intégration** | Vrais moteurs branchés dans l'API ; démo de bout en bout | Démo V1 |
| S5 | **Stabilisation** | Tests fonctionnels, gestion d'erreurs, rapport d'évaluation | Version stable |
| S6 | **Présentation** | README final, rapport, slides, répétition de la démo | Projet final |

Le backend (M7) et le frontend (M6) avancent **dès S1** grâce au moteur `mock`.

**Chemin critique : les données.** Si le volume collecté en fin de S1 est insuffisant, on réduit
le périmètre (une seule langue en STT, domaine de questions plus étroit) **plutôt que** de décaler
l'intégration.

## 3. Rituels

- **Point quotidien** (10 min) : fait hier / prévu aujourd'hui / blocages.
- **Revue de sprint** (fin de semaine) : démo de ce qui fonctionne, mise à jour du planning.
- **Tableau des tâches** (GitHub Projects) : colonnes À faire / En cours / En revue / Terminé.

## 4. Workflow Git

- `main` est **protégée** : pas de push direct, uniquement des Pull Requests.
- Une branche par tâche : `feat/api-detect`, `data/bci-convention`, `fix/audio-validation`…
- Messages de commit clairs, au format `type(portée): description`
  (ex. `feat(api): ajout de /speech`, `data(bci): lot 1 annoté`).
- Une PR = **1 relecture approuvée + CI verte** (tests + lint) avant fusion.
- Jamais de secret, d'audio ou de modèle dans Git (voir `.gitignore`).

## 5. Définition de « Terminé »

Une tâche est terminée quand :
1. le code est fusionné dans `main` via une PR relue ;
2. les tests passent (et de nouveaux tests couvrent la fonctionnalité) ;
3. la documentation concernée est à jour (`docs/`, `/docs` de l'API, README) ;
4. pour une tâche ML : les résultats sont mesurés sur le jeu de **validation**, avec la version du
   dataset indiquée.

## 6. Décisions

Toute décision structurante (choix de modèle, changement de contrat d'API, changement de
périmètre) est consignée dans un **ADR** (`docs/adr/`), avec contexte, options et justification.
