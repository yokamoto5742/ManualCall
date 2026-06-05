"""Gemini Liveセッションの確立・設定（§3.2）

google-genaiの非同期Liveクライアント（client.aio.live.connect）を用いる。
SDK固有の型に依存する処理は本モジュールに集約し、外部から隔離する。
"""

from typing import Any

from app.config import settings
from app.constants import MANUAL_CATEGORIES, SYSTEM_INSTRUCTION

TOOL_NAME = "search_ophthalmology_manual"


def function_declaration() -> dict[str, Any]:
    """search_ophthalmology_manual の関数宣言（§3.2）

    SDKの型に変換する前段のプレーンな辞書表現。仕様書との一致を検証しやすくする。
    """
    return {
        "name": TOOL_NAME,
        "description": "眼科の院内業務マニュアル（受付、検査、手術、会計、急患対応など）を検索します。",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "スタッフからの質問キーワードや文章",
                },
                "category": {
                    "type": "STRING",
                    "enum": MANUAL_CATEGORIES,
                    "description": "検索対象のカテゴリ分類",
                },
            },
            "required": ["query"],
        },
    }


def create_client() -> Any:
    """Vertex AI経由のGeminiクライアントを生成する"""
    from google import genai

    return genai.Client(
        vertexai=True,
        project=settings.gcp_project,
        location=settings.gcp_location,
    )


def build_live_config() -> Any:
    """LiveConnectConfig を構築する（§3.2のsetupに対応）"""
    from google.genai import types

    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=settings.gemini_voice
                )
            )
        ),
        system_instruction=types.Content(
            parts=[types.Part(text=SYSTEM_INSTRUCTION)]
        ),
        tools=[
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(**function_declaration())
                ]
            )
        ],
    )


def connect(client: Any) -> Any:
    """Gemini Liveセッションへの接続（async context manager）を返す"""
    return client.aio.live.connect(
        model=settings.gemini_model,
        config=build_live_config(),
    )
