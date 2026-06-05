"""Vertex AI RAG検索＋800msタイムアウト＋300字要約（§4）

Gemini 3.1 Flash Liveは非同期関数呼び出しに未対応であり、ツール実行完了まで
音声生成がブロックされる。そのため検索には厳格なタイムアウトを課す。
ブロッキングなVertex AI呼び出しはasyncio.to_threadでワーカースレッドに逃がし、
asyncio.wait_forで800msのタイムアウトを課す。
"""

import asyncio
from dataclasses import dataclass

from app.config import settings
from app.constants import RAG_TIMEOUT_MESSAGE

# RAGステータス（§5.2）
STATUS_SUCCESS = "SUCCESS"
STATUS_TIMEOUT = "TIMEOUT"

# 応答種別（§5.2）
RESPONSE_MANUAL_FOUND = "MANUAL_FOUND"
RESPONSE_NO_MANUAL = "NO_MANUAL_DESCRIPTION"

# 該当記載がない場合にモデルへ返す文言（システムプロンプトのエスカレーションを誘発する）
_NO_MANUAL_TEXT = "該当するマニュアルの記載が見つかりませんでした。"


@dataclass(frozen=True)
class RagResult:
    text: str  # ツールレスポンスとしてモデルへ返す文字列
    status: str  # SUCCESS / TIMEOUT
    response_type: str  # MANUAL_FOUND / NO_MANUAL_DESCRIPTION


def _retrieve(query: str, category: str | None) -> list[str]:
    """Vertex AI RAG Engineへの問い合わせ（ブロッキング）

    Top-3・チャンク300〜600文字で取得し、各チャンクのテキストを返す。
    """
    import vertexai
    from vertexai import rag

    vertexai.init(project=settings.gcp_project, location=settings.gcp_location)
    response = rag.retrieval_query(
        rag_resources=[rag.RagResource(rag_corpus=settings.rag_corpus)],
        text=query,
        rag_retrieval_config=rag.RagRetrievalConfig(top_k=settings.rag_top_k),
    )
    return [ctx.text for ctx in response.contexts.contexts]


def _summarize(chunks: list[str]) -> str:
    """検索結果を最大300文字程度のプレーンテキストに整形する（§4.4）"""
    joined = " ".join(chunk.strip() for chunk in chunks if chunk.strip())
    plain = " ".join(joined.split())
    limit = settings.rag_summary_max_chars
    return plain[:limit]


async def search(query: str, category: str | None = None) -> RagResult:
    """RAG検索を実行し、要約済みのツールレスポンスを返す

    800msを超過した場合はタイムアウト文言を即座に返却する。
    """
    try:
        chunks = await asyncio.wait_for(
            asyncio.to_thread(_retrieve, query, category),
            timeout=settings.rag_timeout_seconds,
        )
    except (asyncio.TimeoutError, TimeoutError):
        return RagResult(RAG_TIMEOUT_MESSAGE, STATUS_TIMEOUT, RESPONSE_NO_MANUAL)

    summary = _summarize(chunks)
    if not summary:
        return RagResult(_NO_MANUAL_TEXT, STATUS_SUCCESS, RESPONSE_NO_MANUAL)
    return RagResult(summary, STATUS_SUCCESS, RESPONSE_MANUAL_FOUND)
