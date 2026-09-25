# ADR 0001 — Interfaces IA et moteur « mock »

- **Statut** : accepté
- **Date** : 2026-09-25

## Contexte

Les modèles (STT, traduction, LLM, TTS) ne seront pas prêts avant plusieurs sprints, car ils dépendent de la
collecte des données. Si le backend et le frontend attendent les modèles, l'intégration n'aura lieu
qu'en fin de projet, avec un risque élevé.

## Décision

1. Définir dans `backend/app/services/base.py` une **interface abstraite par brique IA**.
2. Fournir un **moteur `mock`** qui implémente ces interfaces sans traitement réel et dont les
   réponses sont explicitement marquées `[mock]`.
3. Choisir le moteur par configuration (`LANGCI_ENGINE`).

## Conséquences

- ➕ Backend, frontend et IA travaillent en parallèle dès le premier sprint.
- ➕ Le contrat backend ↔ IA est explicite et testé.
- ➕ Comparaison facile de plusieurs moteurs.
- ➖ Les interfaces peuvent devoir évoluer quand les vrais modèles arriveront (ex. streaming,
  plusieurs hypothèses de transcription) : toute évolution passe par un nouvel ADR.
- ⚠️ Le démonstrateur et le champ `engine` signalent clairement le mode mock pour ne jamais présenter
  un résultat factice comme réel.
