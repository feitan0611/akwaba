# 01 — Cadrage du projet

> Source : `Cahier_de_charge_v1.docx` (v1.0, 25/09/2026, statut « À valider avec le formateur »).
> Ce document reformule le besoin, fixe le périmètre du MVP et **liste les points à faire valider**.

## 1. Besoin en une phrase

Un utilisateur **parle en Baoulé ou en Dioula** ; le système **détecte la langue**, **comprend la
requête** et **répond vocalement dans la même langue**. Ces capacités sont exposées via une
**API REST documentée** et testables via un **démonstrateur web**.

## 2. Périmètre du MVP (engagement)

| # | Fonctionnalité | Endpoint | Critère d'acceptation |
|---|----------------|----------|------------------------|
| F1 | Détection de langue (Baoulé / Dioula) sur audio | `POST /detect` | Langue + score de confiance retournés ; exactitude mesurée sur le jeu de test |
| F2 | Transcription de l'audio (STT) | `POST /detect` | Texte retourné ; WER/CER mesurés sur le jeu de test |
| F3 | Traduction langue locale ↔ langue pivot | `POST /translate` | Qualité mesurée (chrF) + évaluation humaine sur un échantillon |
| F4 | Réponse à une requête simple | `POST /ask` | Réponse pertinente sur les cas d'usage définis (évaluation humaine) |
| F5 | Synthèse vocale de la réponse (TTS) | `POST /speech` | Audio intelligible pour un locuteur natif (évaluation humaine) |
| F6 | Chaîne complète audio → audio | `POST /pipeline` | Démo de bout en bout fonctionnelle |
| F7 | Documentation de l'API | `/docs` | Tous les endpoints, paramètres, exemples et erreurs documentés |
| F8 | Démonstrateur web | `/demo/` | Enregistrer / charger un audio et écouter la réponse sans outil technique |

**Hors MVP** (section 5.2 du cahier des charges) : traduction ↔ anglais, Baoulé ↔ Dioula,
historique, autres langues, détection d'intentions (NLU). Aucun travail avant validation du MVP.

## 3. Analyse critique du cahier des charges — points à valider avec le formateur

Relecture ligne à ligne. Chaque point est accompagné d'une **proposition** (appliquée par défaut
dans le code, réversible).

| # | Constat | Proposition |
|---|---------|-------------|
| P1 | **Contradiction de périmètre** : la traduction est « optionnelle » (§5.2) mais le flux API (§9 : `/translate1` → `/ask` → `/translate2`) impose une traduction langue locale ↔ langue pivot **dans le MVP**. Un LLM ne comprend pas le Baoulé/Dioula directement. | Considérer la traduction **langue locale ↔ français** comme faisant partie du MVP. Seules les autres paires (anglais, Baoulé ↔ Dioula) restent optionnelles. |
| P2 | La **langue pivot** de `/translate1` n'est pas précisée. | **Français** (langue officielle, plus de ressources parallèles avec le Dioula/Baoulé que l'anglais). Configurable : `LANGCI_PIVOT_LANGUAGE`. |
| P3 | `/translate1` et `/translate2` font la même opération avec des langues différentes. | **Un seul endpoint `/translate`** avec `source` et `target` (voir [ADR 0002](adr/0002-contrat-api.md)). |
| P4 | Réponse audio au format « Multipart-FormData » : ce format est prévu pour les **requêtes**, il est très inhabituel en réponse et mal géré par les clients HTTP. | Entrée : multipart **ou** JSON Base64 (conforme). Sortie : JSON avec audio **Base64** (par défaut) ou fichier **`audio/wav` brut** (`?response_format=binary`). |
| P5 | Le cas d'usage §7 cite `POST /stt`, absent de la liste des endpoints §9. | Le rôle de `/stt` est couvert par `/detect` (transcription + langue). |
| P6 | Les **critères de réussite (§15) ne sont pas chiffrés** (« correctement », « compréhensibles »). Impossible de dire objectivement si le projet est réussi. | Fixer des **seuils cibles après la baseline** (voir §4 ci-dessous). |
| P7 | Le **planning (§14) n'a pas de dates** ni de durée. | Découpage en sprints proposé dans [06-organisation.md](06-organisation.md) — dates à fixer avec le formateur. |
| P8 | **Données vocales = données personnelles** (la voix identifie une personne). Le cahier mentionne les droits d'usage mais pas le consentement des locuteurs. | Formulaire de consentement obligatoire, métadonnée `consent` vérifiée automatiquement, audio brut hors Git. Se référer à la loi ivoirienne sur la protection des données personnelles (loi n° 2013-450 — à vérifier avec le formateur). |
| P9 | Le Baoulé et le Dioula ont des **variantes dialectales et orthographiques** ; la transcription de référence doit suivre une norme. | Choisir et documenter **une convention orthographique** par langue avant l'annotation (voir [04-donnees.md](04-donnees.md)). |
| P10 | Coquilles techniques : « Skip » (→ probablement **SciPy** / **scikit-learn**), « fine-turning » (→ fine-tuning). | Corrigé dans la documentation. |
| P11 | Le périmètre des « requêtes simples » (§5.1) n'est pas défini : quel domaine ? quelles questions ? | Définir **un domaine restreint** (ex. salutations, santé de base, agriculture, horaires/prix) et une liste fermée de 20–50 questions types. Condition nécessaire pour évaluer F4. |

## 4. Proposition de critères de réussite mesurables (à valider)

Les seuils définitifs seront fixés **après la baseline** (on ne peut pas promettre un chiffre sans
connaître les données). Proposition de départ :

| Brique | Métrique | Cible indicative MVP |
|--------|----------|----------------------|
| Détection de langue | Exactitude sur le jeu de test | ≥ 90 % |
| STT | CER / WER sur le jeu de test | À fixer après baseline ; objectif : amélioration nette vs baseline |
| Traduction | chrF + note humaine (1–5) sur 50 phrases | Note humaine moyenne ≥ 3/5 |
| TTS | Intelligibilité jugée par des locuteurs natifs (1–5) | ≥ 3/5 |
| API | Tests automatisés verts ; temps de réponse `/pipeline` | < 10 s sur CPU pour un audio de 10 s |

## 5. Hypothèses de travail

- Le prototype tourne **en local sur CPU** ; un GPU (Colab/Kaggle) peut servir à l'entraînement.
- Les données sont **rares** : on privilégie les **modèles pré-entraînés multilingues** puis l'adaptation.
- Les limites et erreurs du système seront **présentées honnêtement** (exigence §15).
