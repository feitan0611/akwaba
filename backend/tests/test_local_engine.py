"""Tests du moteur local SANS charger de modèle (rapides, exécutables en CI).

On vérifie que les limites de couverture sont respectées et signalées clairement :
les vérifications de langue ont lieu AVANT tout chargement de modèle.
"""

import base64

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

API = "/api/v1"


@pytest.fixture
def local_app():
    return create_app(Settings(_env_file=None, engine="local", serve_demo=False))


@pytest.fixture
def local_client(local_app) -> TestClient:
    return TestClient(local_app)


def assert_error(response, status: int, code: str) -> str:
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code
    return response.json()["error"]["message"]


def test_building_the_local_engine_loads_no_model(local_app):
    engines = local_app.state.engines
    assert not engines.recognizer._model.loaded
    assert not engines.translator._model.loaded
    assert not any(m.loaded for m in engines.synthesizer._models.values())


def test_health_reports_real_capabilities(local_client):
    body = local_client.get(f"{API}/health").json()
    capabilities = body["capabilities"]
    assert body["engine"] == "local"
    assert body["models"]["stt"] == "mms-1b-all"
    assert capabilities["language_detection"] is False
    assert capabilities["languages"]["dyu"]["full"] is True
    # Aucun modèle public pour le Baoulé : ni STT, ni traduction, ni TTS. (Le LLM, lui,
    # travaille en langue pivot et reste disponible quelle que soit la langue locale.)
    bci = capabilities["languages"]["bci"]
    assert (bci["stt"], bci["translate"], bci["tts"], bci["full"]) == (False, False, False, False)


def test_health_mock_supports_everything(client):
    capabilities = client.get(f"{API}/health").json()["capabilities"]
    assert capabilities["language_detection"] is True
    assert all(lang["full"] for lang in capabilities["languages"].values())


def test_detect_requires_language_without_detection(local_client, wav_bytes):
    response = local_client.post(f"{API}/detect", files={"audio": ("q.wav", wav_bytes, "audio/wav")})
    assert_error(response, 422, "language_required")


def test_detect_refuses_baoule(local_client, wav_bytes):
    response = local_client.post(
        f"{API}/detect", files={"audio": ("q.wav", wav_bytes, "audio/wav")}, data={"language_hint": "bci"}
    )
    message = assert_error(response, 422, "language_not_supported")
    assert "Baoulé" in message


def test_pipeline_refuses_baoule(local_client, wav_bytes):
    payload = {"audio_base64": base64.b64encode(wav_bytes).decode(), "language_hint": "bci"}
    assert_error(local_client.post(f"{API}/pipeline", json=payload), 422, "language_not_supported")


def test_translate_refuses_baoule(local_client):
    response = local_client.post(f"{API}/translate", json={"text": "bonjour", "source": "fra", "target": "bci"})
    assert_error(response, 422, "language_not_supported")


def test_speech_refuses_baoule(local_client):
    response = local_client.post(f"{API}/speech", json={"text": "akwaba", "language": "bci"})
    assert_error(response, 422, "language_not_supported")


def test_ask_reports_unreachable_llm(wav_bytes):
    settings = Settings(_env_file=None, engine="local", serve_demo=False, ollama_url="http://127.0.0.1:9")
    response = TestClient(create_app(settings)).post(f"{API}/ask", json={"text": "Bonjour"})
    message = assert_error(response, 503, "engine_unavailable")
    assert "ollama pull" in message


def test_unknown_engine_is_rejected_at_startup():
    with pytest.raises(ValueError):
        Settings(_env_file=None, engine="inexistant")
