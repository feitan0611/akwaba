import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.mock import MockSpeechSynthesizer


@pytest.fixture
def client() -> TestClient:
    settings = Settings(_env_file=None, engine="mock", max_audio_mb=1, serve_demo=False)
    return TestClient(create_app(settings))


@pytest.fixture
def wav_bytes() -> bytes:
    return MockSpeechSynthesizer().synthesize("test", "bci")
