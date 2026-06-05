"""WS /media-stream — Twilio⇔Gemini双方向中継エンドポイント（§2.3）

1通話につき、Twilio受信→Gemini送信（上り）と、Gemini受信→Twilio送信（下り）を
2つのasyncioタスクとして並行実行する。いずれかが終了・例外時に両方を終了させる。
"""

import asyncio
import base64
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services import gemini_live, rag_service
from app.services.audio_converter import AudioConverter
from app.services.audit_logger import log_rag_event

router = APIRouter()


class CallBridge:
    """1通話分のTwilio⇔Gemini中継状態を保持する"""

    def __init__(self, websocket: WebSocket, session: Any) -> None:
        self._ws = websocket
        self._session = session
        self._converter = AudioConverter()
        self._stream_sid = ""
        self._call_id = ""

    async def pump_twilio_to_gemini(self) -> None:
        """上り: Twilio受信 → μ-law→PCM16・8k→16k → Geminiへ送信"""
        from google.genai import types

        async for message in self._ws.iter_text():
            event = json.loads(message)
            kind = event.get("event")

            if kind == "start":
                start = event.get("start", {})
                self._stream_sid = start.get("streamSid", "")
                self._call_id = start.get("callSid") or self._stream_sid
            elif kind == "media":
                payload = event["media"]["payload"]
                mulaw = base64.b64decode(payload)
                pcm_16k = self._converter.twilio_to_gemini(mulaw)
                await self._session.send_realtime_input(
                    audio=types.Blob(data=pcm_16k, mime_type="audio/pcm;rate=16000")
                )
            elif kind == "stop":
                break

    async def pump_gemini_to_twilio(self) -> None:
        """下り: Gemini受信 → PCM16・16k→8k→μ-law → Twilioへ送信。toolCallはRAGで応答。"""
        async for response in self._session.receive():
            if response.data:
                await self._send_audio_to_twilio(response.data)

            tool_call = getattr(response, "tool_call", None)
            if tool_call:
                await self._handle_tool_call(tool_call)

            if self._is_interrupted(response):
                await self._clear_twilio_buffer()

    async def _send_audio_to_twilio(self, pcm_16k: bytes) -> None:
        mulaw = self._converter.gemini_to_twilio(pcm_16k)
        await self._ws.send_text(
            json.dumps(
                {
                    "event": "media",
                    "streamSid": self._stream_sid,
                    "media": {"payload": base64.b64encode(mulaw).decode("ascii")},
                }
            )
        )

    async def _handle_tool_call(self, tool_call: Any) -> None:
        """GeminiのtoolCallをRAG検索で処理しtoolResponseを返す（§4）

        本モデルは非同期関数呼び出しに未対応のため、受信ループ内で同期的に処理する。
        """
        from google.genai import types

        responses = []
        for fc in tool_call.function_calls:
            args = fc.args or {}
            query = args.get("query", "")
            category = args.get("category")
            result = await rag_service.search(query, category)
            log_rag_event(
                call_id=self._call_id,
                rag_query=query,
                rag_status=result.status,
                response_type=result.response_type,
            )
            responses.append(
                types.FunctionResponse(
                    id=fc.id,
                    name=fc.name,
                    response={"result": result.text},
                )
            )
        await self._session.send_tool_response(function_responses=responses)

    async def _clear_twilio_buffer(self) -> None:
        """発話割り込み（Barge-in）時にTwilio側の再生バッファをクリアする"""
        await self._ws.send_text(
            json.dumps({"event": "clear", "streamSid": self._stream_sid})
        )

    @staticmethod
    def _is_interrupted(response: Any) -> bool:
        content = getattr(response, "server_content", None)
        return bool(content and getattr(content, "interrupted", False))


@router.websocket("/media-stream")
async def media_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    client = gemini_live.create_client()
    async with gemini_live.connect(client) as session:
        bridge = CallBridge(websocket, session)
        upstream = asyncio.create_task(bridge.pump_twilio_to_gemini())
        downstream = asyncio.create_task(bridge.pump_gemini_to_twilio())

        # 一方が終了（stop受信・切断・例外）したら他方もキャンセルして協調終了する（§2.3）
        done, pending = await asyncio.wait(
            {upstream, downstream}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

        for task in done:
            exc = task.exception()
            # 通話切断は正常終了として扱い、それ以外の例外は伝播させる
            if exc is not None and not isinstance(exc, WebSocketDisconnect):
                raise exc
