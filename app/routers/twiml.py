"""POST /twiml/connect — Twilio着信時のTwiML応答（§3.1）"""

from fastapi import APIRouter, Request, Response

from app.constants import GREETING_MESSAGE

router = APIRouter()


def build_twiml(ws_url: str) -> str:
    """Media Streams接続用のTwiMLを生成する"""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Say language="ja-JP">{GREETING_MESSAGE}</Say>'
        "<Connect>"
        f'<Stream url="{ws_url}" />'
        "</Connect>"
        "</Response>"
    )


def _media_stream_url(request: Request) -> str:
    """リクエストのホストからMedia StreamのWebSocket URLを組み立てる"""
    host = request.url.hostname or ""
    if request.url.port:
        host = f"{host}:{request.url.port}"
    return f"wss://{host}/media-stream"


@router.post("/twiml/connect")
async def twiml_connect(request: Request) -> Response:
    twiml = build_twiml(_media_stream_url(request))
    return Response(content=twiml, media_type="application/xml")
