# 03 — Contrat de l'API REST (v1)

> La documentation interactive fait foi : **`http://127.0.0.1:8000/docs`** (générée depuis le code).
> Ce document résume le contrat et les décisions.

Base : `/api/v1` — Codes de langue **ISO 639-3** : `bci` (Baoulé), `dyu` (Dioula), `fra`, `eng`.

## 1. Endpoints

| Endpoint | Méthode | Entrée | Sortie | Brique | Cahier des charges |
|----------|---------|--------|--------|--------|--------------------|
| `/health` | GET | — | `{status, version, engine}` | Système | `/health` |
| `/languages` | GET | — | Liste des langues | Système | (ajout) |
| `/detect` | POST | Audio (multipart **ou** JSON Base64) | `{text, language, confidence, engine}` | STT + LID | `/detect` (+ `/stt` du §7) |
| `/translate` | POST | `{text, source, target}` | `{text, source, target, engine}` | Traduction | `/translate1` + `/translate2` |
| `/ask` | POST | `{text, language}` | `{text, language, engine}` | LLM | `/ask` |
| `/speech` | POST | `{text, language, voice_id?}` | JSON Base64 ou `audio/wav` | TTS | `/speech` |
| `/pipeline` | POST | Audio (multipart **ou** JSON Base64) | Tout le détail + audio de réponse | Chaîne complète | (ajout — flux §8) |

Le champ `engine` indique **quel moteur a produit la réponse** (`mock-*` = factice) : on ne peut
jamais confondre un résultat factice avec un vrai résultat.

## 2. Envoi de l'audio

Formats acceptés : **`.wav` et `.mp3`**, vérifiés sur le **contenu** (signature binaire), pas sur
l'extension. Taille max : 10 Mo (configurable).

**Multipart :**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/detect -F "audio=@question.wav"
```

**JSON Base64 :**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/detect \
  -H "Content-Type: application/json" \
  -d '{"audio_base64": "UklGRi..."}'
```

Champs optionnels (dans les deux modes) : `language_hint` (`bci`|`dyu`), `voice_id` (pipeline).

## 3. Exemples

`POST /translate`
```json
// requête
{"text": "Bonjour, comment allez-vous ?", "source": "fra", "target": "dyu"}
// réponse 200
{"text": "...", "source": "fra", "target": "dyu", "engine": "mock-translator"}
```

`POST /speech?response_format=binary` → corps de réponse = fichier WAV (`Content-Type: audio/wav`).

## 4. Erreurs

Format **unique** pour toutes les erreurs :

```json
{"error": {"code": "unsupported_audio_format", "message": "Format audio non supporté : ...", "details": []}}
```

| HTTP | `code` | Cause |
|------|--------|-------|
| 400 | `missing_audio` | Champ `audio` / `audio_base64` absent |
| 400 | `empty_audio` | Fichier vide |
| 400 | `invalid_base64` | Base64 invalide |
| 400 | `invalid_json` | Corps JSON illisible |
| 413 | `audio_too_large` | Audio > taille max |
| 415 | `unsupported_audio_format` | Ni WAV ni MP3 |
| 415 | `unsupported_content_type` | Ni multipart ni JSON |
| 422 | `invalid_language_hint` | `language_hint` hors `bci`/`dyu` |
| 422 | `validation_error` | Champ invalide (langue inconnue, texte vide, source = target…) |
| 500 | `internal_error` | Erreur serveur (détail uniquement dans les logs) |

## 5. Évolutions prévues (hors MVP)

Authentification par clé API et quotas, historique des requêtes, journalisation pour la
traçabilité du LLM (§18). La version `/api/v1` permet de faire évoluer le contrat sans casser les
clients existants.
