# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

**EyeManual** — 眼科クリニックスタッフが電話（VoIP）で院内業務マニュアルをAIにリアルタイム問い合わせできるバックエンドWebアプリケーション。

詳細仕様: `ManualCall_plan.md`

## 医療安全上の制約

- **ハルシネーション厳禁**: AIはRAGで取得したマニュアル内容のみを回答する。推測・補完をしない。回答有無の最終防御はモデルのシステムプロンプト（記載がなければ「記載がありません」と答える）が担う。
- **スコア足切りはノイズフロア**: In-Memory RAG（BM25）で関連スコアが `rag_min_score` 未満のチャンクは捨てる。これは話題が全く無関係なクエリを弾くノイズ除去であり、「回答が記載されているか」の判定ではない（カテゴリのキーワードを含むが回答できない質問はヒットし得る）。検索はオンメモリのため低遅延（数ミリ秒〜数十ミリ秒）。
- 不明な問い合わせは担当者へのエスカレーションを促す。

## 実装言語・フェーズ

- **実装言語**: Python（仕様書記載のNode.js/TypeScriptは採用しない）
- **現在のフェーズ**: Phase 1（環境構築中。ソースコードはまだ存在しない）

## 専門エージェント

以下のサブエージェントを適切な場面でproactiveに活用する:

| エージェント | 用途 |
|---|---|
| `pytest-test-creator` | テスト作成・実行 |
| `pyright-type-checker` | 型チェック（コード追加・修正後） |
| `japanese-comment-reviewer` | コメントスタイルのレビュー |
| `readme-generator` | README.md の作成・更新 |
| `changelog-updater` | CHANGELOG.md の更新 |
