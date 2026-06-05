# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

**EyeManual** — 眼科クリニックスタッフが電話（VoIP）で院内業務マニュアルをAIにリアルタイム問い合わせできるバックエンドWebアプリケーション。

詳細仕様: `ManualCall_plan.md`

## 医療安全上の制約

- **ハルシネーション厳禁**: AIはRAGで取得したマニュアル内容のみを回答する。推測・補完をしない。
- **RAGタイムアウト**: 検索は800ms以内に完了しなければならない（タイムアウト時は「確認できませんでした」と応答）。
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
