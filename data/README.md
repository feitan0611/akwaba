# Données

> Protocole complet : [docs/04-donnees.md](../docs/04-donnees.md). **À lire avant toute collecte.**

```
data/
├── raw/          # audio brut tel que collecté          (HORS Git)
├── interim/      # audio converti / segmenté            (HORS Git)
├── processed/    # audio final WAV 16 kHz mono          (HORS Git)
├── metadata/     # métadonnées CSV                       (versionnées)
└── SOURCES.md    # registre des sources et licences      (versionné)
```

L'audio n'est **jamais** commité (taille + données personnelles). Il est partagé via un espace de
stockage à accès restreint, dont le lien est communiqué en interne à l'équipe.

Commandes :

```bash
python -m ml.dataset validate data/metadata/metadata.csv --check-audio
python -m ml.dataset split data/metadata/metadata.csv data/metadata/metadata_split.csv
```

`metadata/metadata.example.csv` illustre **uniquement le format** : ses lignes sont des
exemples fictifs et ne doivent pas être intégrées au corpus.
