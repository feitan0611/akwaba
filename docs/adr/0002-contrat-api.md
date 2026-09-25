# ADR 0002 — Ajustements du contrat d'API par rapport au cahier des charges

- **Statut** : proposé — **à valider avec le formateur** (le cahier §9 prévoit que les endpoints
  soient ajustés après validation du périmètre)
- **Date** : 2026-09-25

## Contexte

Le cahier des charges (§9) propose `/health`, `/detect`, `/translate1`, `/ask`, `/translate2`,
`/speech`, avec des réponses audio au format « Multipart-FormData ou Base64 ».

## Décisions

| # | Décision | Justification |
|---|----------|---------------|
| 1 | Préfixe `/api/v1` | Permet de faire évoluer l'API sans casser les clients existants |
| 2 | `/translate1` + `/translate2` → **`/translate`** avec `source` et `target` | Même opération, seules les langues changent ; un endpoint unique est plus simple à documenter, tester et consommer |
| 3 | Ajout de **`/pipeline`** (audio → audio) | Le flux principal §8 exige 5 appels successifs ; un endpoint unique simplifie le démonstrateur et les applications tierces, et mesure la latence de chaque étape |
| 4 | Entrée audio : **multipart ou JSON Base64** sur le même endpoint | Conforme au cahier |
| 5 | Sortie audio : **JSON Base64** (défaut) ou **`audio/wav` brut** (`?response_format=binary`) au lieu de multipart | Une réponse multipart n'est pas un usage standard et est mal prise en charge par les clients HTTP |
| 6 | Langues identifiées par codes **ISO 639-3** (`bci`, `dyu`, `fra`, `eng`) | Norme internationale, utilisée par les modèles multilingues |
| 7 | Format d'erreur unique `{"error": {"code", "message", "details"}}` | « Gestion claire des erreurs » (§12) |
| 8 | Champ `engine` dans chaque réponse | Transparence sur le moteur ayant produit le résultat |

## Conséquences

Les endpoints élémentaires (`/detect`, `/translate`, `/ask`, `/speech`) restent disponibles pour
les applications qui veulent composer leur propre chaîne ; `/pipeline` sert le cas nominal.
