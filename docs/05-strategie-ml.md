# 05 — Stratégie IA / ML

## 1. Démarche

Pour chaque brique : **1. benchmark de l'existant → 2. baseline simple → 3. modèle candidat →
4. évaluation sur le jeu de test → 5. analyse d'erreurs**. Aucun entraînement lourd avant d'avoir
mesuré ce que donnent les modèles pré-entraînés existants.

## 2. Pistes de modèles pré-entraînés à évaluer

> ⚠️ **À vérifier par le benchmark** : la couverture réelle du Baoulé (`bci`) et du Dioula (`dyu`)
> doit être confirmée sur les fiches officielles de chaque modèle (model cards, listes de langues)
> **avant** tout engagement. Ne pas supposer qu'un modèle « multilingue » couvre ces langues.

| Brique | Pistes | Ce qu'il faut vérifier |
|--------|--------|------------------------|
| Détection de langue (LID) | Meta **MMS-LID** (modèles couvrant des milliers de langues) | Présence de `bci` et `dyu` dans la liste des langues ; exactitude sur nos données |
| STT / ASR | Meta **MMS** (ASR avec adaptateurs par langue) ; **Whisper** (ne couvre pas officiellement ces langues → fine-tuning nécessaire) | Disponibilité d'un adaptateur `bci`/`dyu` ; WER/CER sans adaptation |
| Traduction | Meta **NLLB-200** (le Dioula `dyu_Latn` figure dans sa liste de langues ; Baoulé probablement absent) | Couverture du Baoulé ; qualité fra ↔ dyu sur nos phrases |
| LLM | LLM généraliste en **français** (langue pivot) : modèle open-source local ou service hébergé | Coût, latence, possibilité d'exécution locale, conditions d'utilisation |
| TTS | Meta **MMS-TTS** (un modèle par langue) | Existence d'un modèle `bci`/`dyu` ; intelligibilité jugée par des locuteurs natifs |

Le benchmark est consigné dans `ml/notebooks/01_benchmark.ipynb` et résumé dans un ADR.

## 3. Baselines (point de comparaison obligatoire)

| Brique | Baseline proposée |
|--------|-------------------|
| LID | Caractéristiques MFCC (librosa) + régression logistique (scikit-learn), ou classe majoritaire |
| STT | Modèle pré-entraîné **sans** adaptation |
| Traduction | Modèle pré-entraîné sans adaptation ; à défaut, dictionnaire de phrases fréquentes |
| TTS | Modèle pré-entraîné sans adaptation |

Un modèle candidat n'est retenu que s'il **bat la baseline** sur le jeu de validation.

## 4. Métriques

| Brique | Métriques automatiques | Évaluation humaine |
|--------|------------------------|--------------------|
| LID | Exactitude, F1 par langue, matrice de confusion (`ml/metrics.py`) | — |
| STT | WER, CER agrégés sur le corpus (`ml/metrics.py`) | Analyse qualitative des erreurs |
| Traduction | chrF (préféré au BLEU pour les langues peu dotées), BLEU (`sacrebleu`) | Note 1–5 par ≥ 2 locuteurs natifs sur 50 phrases |
| LLM | — | Pertinence des réponses sur la liste de questions types |
| TTS | — | Intelligibilité et naturel (1–5) par locuteurs natifs |
| Pipeline | Latence de bout en bout (`timings_ms`) | Démo sur scénarios définis |

Le CER est souvent plus informatif que le WER pour ces langues (segmentation des mots
variable d'un transcripteur à l'autre).

## 5. Rapport d'évaluation (livrable)

Pour chaque brique : données utilisées (version du dataset), modèle et paramètres, scores
baseline vs candidat **sur le jeu de test**, exemples d'erreurs typiques, **limites connues**.

## 6. Intégration dans l'API

Un modèle retenu est intégré en créant une classe qui implémente l'interface correspondante de
`backend/app/services/base.py`, puis en l'enregistrant dans `registry.py` sous un nouveau nom de
moteur. Le modèle est chargé **une seule fois** au démarrage.
