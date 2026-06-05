"""rag_serviceの単体テスト（In-Memory BM25検索・関連スコア足切り・300字要約）"""

import pytest

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
async def test_real_search_finds_relevant_manual():
    """モックなしの実サンプルデータで関連質問がヒットすること"""
    result = await rag_service.search("散瞳薬を点眼したあと運転してよいか", None)

    assert result.status == rag_service.STATUS_SUCCESS
    assert result.response_type == rag_service.RESPONSE_MANUAL_FOUND
    assert "運転" in result.text


@pytest.mark.asyncio
async def test_topically_unrelated_query_returns_no_manual():
    """話題が全く無関係な質問はスコア足切り（ノイズフロア）で「記載なし」になること

    注: この閾値はノイズ除去であり、回答の有無の判定ではない。マニュアルの
    キーワードを含むが回答できない質問はヒットし得る。その最終防御はモデルの
    システムプロンプト（記載がなければ「記載がありません」と答える）が担う。
    """
    result = await rag_service.search("近所のおすすめラーメン屋を教えて", None)

    assert result.response_type == rag_service.RESPONSE_NO_MANUAL
    assert result.status == rag_service.STATUS_SUCCESS


@pytest.mark.asyncio
async def test_category_filter_excludes_other_categories():
    """別カテゴリで絞ると強くマッチするチャンクも対象外になること

    「白内障手術…」は手術カテゴリに強くヒット（スコア約11）するが、会計カテゴリ
    のチャンクはスコア0のため、会計で絞ると「記載なし」になる。
    """
    in_category = await rag_service.search("白内障手術の前日の準備", "手術")
    other_category = await rag_service.search("白内障手術の前日の準備", "会計")

    assert in_category.response_type == rag_service.RESPONSE_MANUAL_FOUND
    assert other_category.response_type == rag_service.RESPONSE_NO_MANUAL
