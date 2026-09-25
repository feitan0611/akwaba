"""Référentiel des langues (codes ISO 639-3), unique source de vérité pour tout le projet."""

from typing import Literal

LOCAL_LANGUAGES: dict[str, str] = {"bci": "Baoulé", "dyu": "Dioula"}
PIVOT_LANGUAGES: dict[str, str] = {"fra": "Français", "eng": "Anglais"}
ALL_LANGUAGES: dict[str, str] = {**LOCAL_LANGUAGES, **PIVOT_LANGUAGES}

LocalLanguage = Literal["bci", "dyu"]
Language = Literal["bci", "dyu", "fra", "eng"]
