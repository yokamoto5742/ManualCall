"""rag_serviceの単体テスト（800msタイムアウト・300字要約・記載なし応答）"""

import asyncio
import time

import pytest

from app.constants import RAG_TIMEOUT_MESSAGE
from app.services import rag_service


@pytest.mark.asyncio
async def test_search_success_returns_summary(monkeypatch):
    monkeypatch.setattr(
        rag_service, "_retrieve", lambda q, c: ["受付は8時半に開錠する。"]
    )

    result = await rag_service.search("開錠時刻は？", "受付")

    assert result.status == rag_service.STATUS_SUCCESS
    assert result.response_type == rag_service.RESPONSE_MANUAL_FOUND
    assert "8時半" in result.text


@pytest.mark.asyncio
async def test_search_timeout_returns_fixed_message(monkeypatch):
    """800msを超過したら固定文言を即座に返す（§4.1）"""

    def slow_retrieve(query, category):
        time.sleep(1.0)
        return ["遅延した結果"]

    monkeypatch.setattr(rag_service, "_retrieve", slow_retrieve)

    start = time.monotonic()
    result = await rag_service.search("質問", None)
    elapsed = time.monotonic() - start

    assert result.text == RAG_TIMEOUT_MESSAGE
    assert result.status == rag_service.STATUS_TIMEOUT
    assert elapsed < 0.95  # 0.8秒前後でタイムアウトすること


@pytest.mark.asyncio
async def test_summary_capped_at_300_chars(monkeypatch):
    long_text = "あ" * 1000
    monkeypatch.setattr(rag_service, "_retrieve", lambda q, c: [long_text])

    result = await rag_service.search("質問", None)

    assert len(result.text) == 300


@pytest.mark.asyncio
async def test_empty_result_returns_no_manual(monkeypatch):
    monkeypatch.setattr(rag_service, "_retrieve", lambda q, c: [])

    result = await rag_service.search("該当なしの質問", None)

    assert result.response_type == rag_service.RESPONSE_NO_MANUAL
    assert result.status == rag_service.STATUS_SUCCESS


@pytest.mark.asyncio
async def test_timeout_message_matches_plan_verbatim():
    """医療安全上クリティカルな固定文言が仕様書と完全一致すること（§4.1）"""
    expected = (
        "エラー：マニュアル検索がタイムアウトしました。"
        "管理者または先輩スタッフに通常通りの手順を直接確認してください。"
    )
    assert RAG_TIMEOUT_MESSAGE == expected
