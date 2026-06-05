"""In-Memory RAG検索＋関連スコア足切り＋300字要約（§4）

外部のVertex AIに依存せず、起動時にdata/manual_chunks.jsonをメモリへロードし、
文字2-gramベースのBM25で検索する。低遅延のためタイムアウトは設けない。

医療安全上、関連スコアがrag_min_score未満のチャンクは「該当なし」として捨てる。
無関係な質問に対して無理に検索結果を返すとハルシネーションの原因になるためである。
"""

import json
import os
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from app.config import settings

# RAGステータス（§5.2）
STATUS_SUCCESS = "SUCCESS"

# 応答種別（§5.2）
RESPONSE_MANUAL_FOUND = "MANUAL_FOUND"
RESPONSE_NO_MANUAL = "NO_MANUAL_DESCRIPTION"

# 該当記載がない場合にモデルへ返す文言（システムプロンプトのエスカレーションを誘発する）
_NO_MANUAL_TEXT = "該当するマニュアルの記載が見つかりませんでした。"

_MANUAL_FILE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "manual_chunks.json"
)


@dataclass(frozen=True)
class RagResult:
    text: str  # ツールレスポンスとしてモデルへ返す文字列
    status: str  # SUCCESS
    response_type: str  # MANUAL_FOUND / NO_MANUAL_DESCRIPTION


def _tokenize(text: str) -> list[str]:
    """日本語向けの文字2-gramトークナイザ（形態素解析器に依存しない）"""
    return [text[i : i + 2] for i in range(len(text) - 1)]


def _load_index() -> tuple[list[dict], BM25Okapi | None]:
    """マニュアルをメモリへロードし、BM25インデックスを構築する"""
    if not os.path.exists(_MANUAL_FILE_PATH):
        return [], None
    with open(_MANUAL_FILE_PATH, "r", encoding="utf-8") as f:
        docs = json.load(f)
    if not docs:
        return [], None
    bm25 = BM25Okapi([_tokenize(doc["text"]) for doc in docs])
    return docs, bm25


_MANUAL_DATA, _BM25 = _load_index()


def _retrieve(query: str, category: str | None) -> list[str]:
    """メモリ内のマニュアルからBM25スコア上位を抽出する

    カテゴリ指定時は該当カテゴリに絞り、rag_min_score未満は除外する。
    """
    if _BM25 is None:
        return []

    scores = _BM25.get_scores(_tokenize(query))
    candidates = [
        (score, doc["text"])
        for doc, score in zip(_MANUAL_DATA, scores)
        if score >= settings.rag_min_score
        and (category is None or doc.get("category") == category)
    ]
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [text for _, text in candidates[: settings.rag_top_k]]


def _summarize(chunks: list[str]) -> str:
    """検索結果を最大300文字程度のプレーンテキストに整形する（§4.4）"""
    joined = " ".join(chunk.strip() for chunk in chunks if chunk.strip())
    plain = " ".join(joined.split())
    limit = settings.rag_summary_max_chars
    return plain[:limit]


async def search(query: str, category: str | None = None) -> RagResult:
    """RAG検索を実行し、要約済みのツールレスポンスを返す

    オンメモリ検索のためタイムアウトは発生しない。
    """
    summary = _summarize(_retrieve(query, category))
    if not summary:
        return RagResult(_NO_MANUAL_TEXT, STATUS_SUCCESS, RESPONSE_NO_MANUAL)
    return RagResult(summary, STATUS_SUCCESS, RESPONSE_MANUAL_FOUND)
