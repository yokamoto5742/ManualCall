"""twimlルーターの単体テスト（TwiML生成・エンドポイント応答）"""

from fastapi.testclient import TestClient

from app.constants import GREETING_MESSAGE
from app.main import app
from app.routers.twiml import build_twiml

client = TestClient(app)


def test_build_twiml_contains_greeting_and_stream():
    twiml = build_twiml("wss://example.a.run.app/media-stream")

    assert GREETING_MESSAGE in twiml
    assert '<Stream url="wss://example.a.run.app/media-stream" />' in twiml
    assert twiml.startswith("<?xml")


def test_twiml_connect_endpoint_returns_xml():
    response = client.post("/twiml/connect")

    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "<Connect>" in response.text
    assert "/media-stream" in response.text


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
