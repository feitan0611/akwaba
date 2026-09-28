import base64

API = "/api/v1"


def assert_error(response, status: int, code: str) -> None:
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code


# --- Système -----------------------------------------------------------------


def test_health(client):
    response = client.get(f"{API}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["engine"] == "mock"
    assert response.json()["pivot_language"] == "fra"


def test_languages(client):
    codes = {lang["code"] for lang in client.get(f"{API}/languages").json()}
    assert {"bci", "dyu", "fra", "eng"} == codes


# --- /detect : entrée audio --------------------------------------------------


def test_detect_multipart(client, wav_bytes):
    response = client.post(
        f"{API}/detect",
        files={"audio": ("q.wav", wav_bytes, "audio/wav")},
        data={"language_hint": "dyu"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["language"] == "dyu"
    assert 0 <= body["confidence"] <= 1


def test_detect_base64(client, wav_bytes):
    payload = {"audio_base64": base64.b64encode(wav_bytes).decode(), "language_hint": "bci"}
    response = client.post(f"{API}/detect", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["language"] == "bci"


def test_detect_accepts_mp3_signature(client):
    fake_mp3 = b"ID3" + b"\x00" * 100
    response = client.post(f"{API}/detect", files={"audio": ("q.mp3", fake_mp3, "audio/mpeg")})
    assert response.status_code == 200, response.text


def test_detect_rejects_unsupported_format(client):
    response = client.post(f"{API}/detect", files={"audio": ("q.ogg", b"OggS" + b"\x00" * 100, "audio/ogg")})
    assert_error(response, 415, "unsupported_audio_format")


def test_detect_rejects_extension_spoofing(client):
    # Extension .wav mais contenu texte : le format est vérifié sur le contenu.
    response = client.post(f"{API}/detect", files={"audio": ("q.wav", b"not audio at all", "audio/wav")})
    assert_error(response, 415, "unsupported_audio_format")


def test_detect_rejects_empty_audio(client):
    response = client.post(f"{API}/detect", files={"audio": ("q.wav", b"", "audio/wav")})
    assert_error(response, 400, "empty_audio")


def test_detect_rejects_too_large_audio(client, wav_bytes):
    big = wav_bytes + b"\x00" * (2 * 1024 * 1024)  # limite de test : 1 Mo
    response = client.post(f"{API}/detect", files={"audio": ("q.wav", big, "audio/wav")})
    assert_error(response, 413, "audio_too_large")


def test_detect_rejects_missing_audio(client):
    response = client.post(f"{API}/detect", data={"language_hint": "bci"}, files={"other": ("x", b"x")})
    assert_error(response, 400, "missing_audio")


def test_detect_rejects_invalid_base64(client):
    response = client.post(f"{API}/detect", json={"audio_base64": "@@@ pas du base64 @@@"})
    assert_error(response, 400, "invalid_base64")


def test_detect_rejects_bad_content_type(client):
    response = client.post(f"{API}/detect", content=b"abc", headers={"content-type": "text/plain"})
    assert_error(response, 415, "unsupported_content_type")


def test_detect_rejects_bad_language_hint(client, wav_bytes):
    response = client.post(
        f"{API}/detect", files={"audio": ("q.wav", wav_bytes, "audio/wav")}, data={"language_hint": "xx"}
    )
    assert_error(response, 422, "invalid_language_hint")


# --- Briques texte -----------------------------------------------------------


def test_translate(client):
    response = client.post(f"{API}/translate", json={"text": "bonjour", "source": "fra", "target": "bci"})
    assert response.status_code == 200
    assert response.json()["target"] == "bci"


def test_translate_rejects_same_language(client):
    response = client.post(f"{API}/translate", json={"text": "bonjour", "source": "fra", "target": "fra"})
    assert_error(response, 422, "validation_error")


def test_translate_rejects_blank_text(client):
    response = client.post(f"{API}/translate", json={"text": "   ", "source": "fra", "target": "bci"})
    assert_error(response, 422, "validation_error")


def test_translate_rejects_unknown_language(client):
    response = client.post(f"{API}/translate", json={"text": "a", "source": "xyz", "target": "bci"})
    assert_error(response, 422, "validation_error")


def test_ask(client):
    response = client.post(f"{API}/ask", json={"text": "Quelle heure est-il ?"})
    assert response.status_code == 200
    assert response.json()["language"] == "fra"


def test_speech_base64(client):
    response = client.post(f"{API}/speech", json={"text": "akwaba", "language": "bci"})
    assert response.status_code == 200
    audio = base64.b64decode(response.json()["audio_base64"])
    assert audio[:4] == b"RIFF"


def test_speech_binary(client):
    response = client.post(f"{API}/speech?response_format=binary", json={"text": "i ni ce", "language": "dyu"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content[:4] == b"RIFF"


def test_speech_rejects_pivot_language(client):
    response = client.post(f"{API}/speech", json={"text": "bonjour", "language": "fra"})
    assert_error(response, 422, "validation_error")


# --- Pipeline de bout en bout -----------------------------------------------


def test_pipeline(client, wav_bytes):
    response = client.post(
        f"{API}/pipeline",
        files={"audio": ("q.wav", wav_bytes, "audio/wav")},
        data={"language_hint": "dyu"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["detection"]["language"] == "dyu"
    assert body["pivot_language"] == "fra"
    assert base64.b64decode(body["answer_audio_base64"])[:4] == b"RIFF"
    assert set(body["timings_ms"]) == {"detect", "translate_in", "ask", "translate_out", "speech"}


def test_openapi_documents_both_audio_content_types(client):
    spec = client.get("/openapi.json").json()
    content = spec["paths"][f"{API}/detect"]["post"]["requestBody"]["content"]
    assert {"multipart/form-data", "application/json"} <= set(content)


def test_demo_is_served_without_stale_cache():
    from fastapi.testclient import TestClient

    from app.config import Settings
    from app.main import create_app

    demo_client = TestClient(create_app(Settings(_env_file=None, serve_demo=True)))
    response = demo_client.get("/demo/")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache"
