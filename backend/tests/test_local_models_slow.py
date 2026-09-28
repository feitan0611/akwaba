"""Tests d'intégration avec les VRAIS modèles (lents, ~6 Go de modèles à télécharger).

Désactivés par défaut (et en CI). Pour les lancer :
    LANGCI_RUN_SLOW=1 pytest backend/tests/test_local_models_slow.py -s

Test « aller-retour » : français → Dioula (NLLB) → audio (TTS) → texte (STT).
Si les trois briques fonctionnent, la transcription doit ressembler au texte synthétisé.
C'est un test de bon fonctionnement technique, PAS une évaluation de qualité : celle-ci
exige des enregistrements de locuteurs natifs et des traductions de référence
(voir docs/05-strategie-ml.md).
"""

import os

import pytest

from app.audio import AudioInput
from ml.metrics import cer

pytestmark = pytest.mark.skipif(
    os.environ.get("LANGCI_RUN_SLOW") != "1", reason="modèles réels : définir LANGCI_RUN_SLOW=1"
)


@pytest.fixture(scope="module")
def bricks():
    from app.services.local import MMSSpeechRecognizer, MMSSpeechSynthesizer, NLLBTranslator

    return NLLBTranslator(), MMSSpeechSynthesizer(), MMSSpeechRecognizer()


def test_dyula_roundtrip(bricks):
    translator, synthesizer, recognizer = bricks
    source = "Bonjour, comment allez-vous ?"

    dyula = translator.translate(source, "fra", "dyu")
    wav = synthesizer.synthesize(dyula, "dyu")
    transcription = recognizer.transcribe(AudioInput(wav, "wav", {"language_hint": "dyu"})).text
    back = translator.translate(transcription, "dyu", "fra")

    error_rate = cer([dyula], [transcription])
    print(f"\n  fra  : {source}\n  dyu  : {dyula}\n  STT  : {transcription}")
    print(f"  CER  : {error_rate:.2f}\n  → fra: {back}")
    assert dyula and transcription
    assert error_rate < 0.5
