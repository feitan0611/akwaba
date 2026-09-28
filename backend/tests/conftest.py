import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.mock import MockSpeechSynthesizer

HEALTH_DOC = """---
title: Prévention du paludisme
source: Document de test
---
# Moustiquaire

Dormir sous une moustiquaire imprégnée protège des piqûres de moustiques la nuit.

# Consultation

En cas de fièvre, il faut consulter rapidement un agent de santé.
"""

FARM_DOC = """---
title: Culture du riz
source: Document de test
---
# Semis

Le riz se sème au début de la saison des pluies, dans une rizière bien préparée.
"""


@pytest.fixture
def knowledge_dir(tmp_path):
    """Base de connaissances de test, isolée du contenu réel de knowledge/."""
    directory = tmp_path / "knowledge"
    directory.mkdir()
    (directory / "paludisme.md").write_text(HEALTH_DOC, encoding="utf-8")
    (directory / "riz.md").write_text(FARM_DOC, encoding="utf-8")
    return directory


@pytest.fixture
def settings(tmp_path, knowledge_dir) -> Settings:
    return Settings(
        _env_file=None,
        engine="mock",
        max_audio_mb=1,
        serve_demo=False,
        knowledge_dir=knowledge_dir,
        rag_index_dir=tmp_path / "rag_index",
    )


@pytest.fixture
def client(settings) -> TestClient:
    return TestClient(create_app(settings))


@pytest.fixture
def wav_bytes() -> bytes:
    return MockSpeechSynthesizer().synthesize("test", "bci")
