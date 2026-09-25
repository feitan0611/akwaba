# 04 — Protocole de constitution du corpus

> La qualité des données est **l'élément critique** du projet (cahier §10). Ce protocole est
> **obligatoire** pour toute donnée intégrée au corpus.

## 1. Règles non négociables

1. **Aucune donnée fabriquée présentée comme réelle.** Toute donnée synthétique ou augmentée est
   marquée comme telle (`source` = `synthetique:<méthode>`).
2. **Source et licence documentées** pour chaque enregistrement. Pas de licence claire → pas de
   donnée.
3. **Consentement écrit** de chaque locuteur (enregistrements de l'équipe). La voix est une donnée
   personnelle.
4. **Pseudonymisation** : `speaker_id` est un code (`bci-spk007`), jamais un nom. La table de
   correspondance nom ↔ code reste hors du dépôt, accès restreint.
5. **L'audio n'est pas versionné dans Git** (taille + données personnelles). Il est stocké sur un
   espace partagé à accès restreint ; Git ne contient que les métadonnées.

## 2. Sources à investiguer (à documenter dans `data/SOURCES.md`)

| Type | Exemples de pistes | Point de vigilance |
|------|--------------------|---------------------|
| Enregistrements propres | Locuteurs natifs de l'entourage, avec consentement | Diversité (âge, genre, région) |
| Corpus ouverts | Jeux de données de recherche sur les langues africaines | Vérifier la couverture réelle du Baoulé/Dioula et la licence |
| Textes religieux / éducatifs | Traductions bibliques, manuels d'alphabétisation | **Droits d'auteur souvent restrictifs** — licence à vérifier avant usage |
| Radio / médias locaux | Émissions en langues locales | Accord explicite du diffuseur nécessaire |

Chaque source retenue est inscrite dans `data/SOURCES.md` : nom, URL, licence, date d'accès,
volume, langue, remarques.

## 3. Convention de transcription

À fixer **avant** l'annotation, par langue, par les pôles Data (M1, M2) :

- Orthographe de référence retenue (et variantes connues à normaliser).
- Traitement des **tons** (notés ou non ?) et des voyelles ouvertes (ɛ, ɔ) : même règle pour tous.
- Encodage : **UTF-8, normalisation Unicode NFC**.
- Nombres, emprunts au français, hésitations, bruits : règle écrite (ex. `[bruit]`, `[rire]`).

Sans convention commune, le WER mesure les désaccords entre annotateurs plutôt que la qualité du modèle.

## 4. Format audio de référence

WAV, PCM 16 bits, **mono, 16 kHz** (format attendu par la plupart des modèles vocaux). Les fichiers
d'autres formats sont convertis lors du prétraitement (`data/interim/` → `data/processed/`).

## 5. Schéma des métadonnées (`data/metadata/metadata.csv`)

Un enregistrement = une ligne. Exemple : [`data/metadata/metadata.example.csv`](../data/metadata/metadata.example.csv).

| Colonne | Obligatoire | Valeurs | Description |
|---------|-------------|---------|-------------|
| `id` | oui | unique | Identifiant de l'énoncé |
| `audio_path` | oui | `.wav` / `.mp3` | Chemin relatif depuis la racine du projet |
| `language` | oui | `bci` / `dyu` | Langue de l'énoncé |
| `transcription` | oui | texte | Transcription selon la convention §3 |
| `translation_fr` | recommandé | texte | Traduction française (données parallèles pour F3) |
| `speaker_id` | oui | code | Locuteur pseudonymisé |
| `speaker_gender` | oui | `F` / `M` / `NR` | NR = non renseigné |
| `speaker_age_range` | recommandé | `18-30`… | Tranche d'âge |
| `dialect_variant` | recommandé | texte | Variante régionale (ex. région d'origine) |
| `duration_s` | oui | > 0 | Durée en secondes |
| `source` | oui | texte | Origine de la donnée (voir `SOURCES.md`) |
| `license` | oui | texte | Licence d'usage (ex. `CC-BY-4.0`, `accord-locuteur`) |
| `consent` | oui | `oui` | Consentement obtenu (toute autre valeur est rejetée) |
| `annotator` | oui | code membre | Qui a transcrit |
| `validated` | oui | `oui` / `non` | Transcription relue par une 2ᵉ personne |
| `split` | généré | `train` / `validation` / `test` | Ajouté par l'outil de découpage |

Validation automatique :
```bash
python -m ml.dataset validate data/metadata/metadata.csv --check-audio
```

## 6. Découpage entraînement / validation / test

```bash
python -m ml.dataset split data/metadata/metadata.csv data/metadata/metadata_split.csv
```

- Découpage **par locuteur** : un même locuteur n'apparaît **jamais** dans deux splits. Sinon le
  modèle reconnaît la voix plutôt que la langue, et les scores sont surestimés.
- Stratifié par langue, ratios 80 / 10 / 10 en **durée**, graine fixe (reproductible).
- **Le jeu de test est gelé** dès sa création : on ne l'utilise que pour l'évaluation finale, jamais
  pour régler les hyperparamètres (on utilise `validation` pour cela).

## 7. Versionnement du dataset

Chaque version livrée (`Dataset V1`, `V2`…) est figée : copie des métadonnées dans
`data/metadata/releases/vX/`, note de version (volume par langue et par split, sources ajoutées,
limites connues). Une « datasheet » (fiche descriptive) accompagne la version finale.
