# ADR 0003 — Choix des premiers modèles réels (moteur « local »)

- **Statut** : accepté (version allégée) — à présenter au formateur
- **Date** : 2026-09-28

## Contexte

Il faut remplacer le moteur factice (`mock`) par de vrais modèles. La stratégie ML
([05-strategie-ml.md](../05-strategie-ml.md)) imposait de **vérifier la couverture réelle** du
Baoulé (`bci`) et du Dioula (`dyu`) avant tout engagement.

Contraintes matérielles : portable sans GPU dédié (Intel i7-1255U, 16 Go de RAM).

## Vérification de couverture (28/09/2026, sur les fiches Hugging Face)

| Brique | Modèle vérifié | Dioula | Baoulé | Taille | Licence |
|--------|----------------|:------:|:------:|-------:|---------|
| Détection de langue | `facebook/mms-lid-256` | ✅ | ✅ | 3,7 Go | CC-BY-NC-4.0 |
| Reconnaissance vocale | `facebook/mms-1b-all` (adaptateurs par langue) | ✅ | ❌ pas d'adaptateur | 3,7 Go | CC-BY-NC-4.0 |
| Traduction | `facebook/nllb-200-distilled-600M` | ✅ `dyu_Latn` | ❌ absent | 2,3 Go | CC-BY-NC-4.0 |
| Synthèse vocale | `facebook/mms-tts-dyu` / `mms-tts-bci` | ✅ | ❌ inexistant | 0,14 Go | CC-BY-NC-4.0 |
| LLM (langue pivot) | `qwen2.5:3b` via Ollama | — (français) | — (français) | 1,9 Go | Apache-2.0 |

**Constat majeur : aucun modèle public ne couvre le Baoulé en reconnaissance vocale, traduction
ou synthèse vocale.** Seule la détection de langue le reconnaît.

## Décision

1. Moteur `local` pour le **Dioula de bout en bout** : MMS-1B-all (STT) → NLLB-600M (dyu → fra)
   → qwen2.5:3b (réponse en français) → NLLB-600M (fra → dyu) → MMS-TTS-dyu.
2. **Version allégée, sans modèle de détection de langue** (choix de l'équipe, pour économiser
   3,7 Go de RAM) : la langue est choisie par l'utilisateur (`language_hint`). L'API l'indique via
   `language_source: "provided"` et `/health` annonce `language_detection: false`.
3. **Baoulé : refus explicite**, jamais de résultat inventé. Toute demande renvoie
   `422 language_not_supported` avec un message clair ; l'interface affiche « Baoulé — bientôt ».
4. Modèles chargés **à la première utilisation** (ou au démarrage avec `LANGCI_PRELOAD_MODELS`),
   inférences exécutées une à la fois par modèle (RAM limitée).
5. Le moteur `mock` reste le moteur par défaut pour le développement et la CI.

## Conséquences

- ➕ Première chaîne audio → audio réelle, en Dioula.
- ➕ L'API expose honnêtement ses capacités par langue (`/health` → `capabilities`).
- ➖ **Le Baoulé devient le cœur du travail de recherche** : il faudra adapter (fine-tuning) un
  modèle MMS sur le corpus Baoulé collecté par l'équipe (pôles Data M1 et IA M4/M5).
- ➖ **Licence non commerciale (CC-BY-NC-4.0)** : acceptable pour ce projet de formation, mais
  incompatible avec un usage par des entreprises sans autre modèle. À signaler dans le rapport.
- ➖ Qualité **non évaluée** à ce stade : les modèles NLLB et MMS sont entraînés sur des
  données limitées (souvent religieuses) pour le Dioula. L'évaluation sur le jeu de test de
  l'équipe reste à faire (WER/CER, chrF, évaluation humaine par des locuteurs natifs).
- ➖ Latence élevée sur CPU (plusieurs dizaines de secondes par échange).
- ⚠️ La détection automatique pourra être réactivée avec `mms-lid-256` sur une machine disposant
  de plus de mémoire (nouvel ADR).
