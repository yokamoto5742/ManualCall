# EyeManual（ManualCall）

眼科クリニックスタッフが電話（VoIP）で院内業務マニュアルをAIにリアルタイム問い合わせできるバックエンドWebアプリケーション。

詳細仕様は `ManualCall_plan.md` を参照。

## アーキテクチャ

Twilio Media Streams（μ-law 8kHz）と Gemini 3.1 Flash Live（PCM16 16kHz）を
FastAPIのWebSocketで双方向中継し、In-Memory RAG（BM25）で院内マニュアルを検索する。

```
Twilio ──WS──> /media-stream ──> Gemini Live API
                    │                   │ toolCall
                    │                   ▼
                    └────────── In-Memory RAG（data/manual_chunks.json + BM25）
```

## モジュール構成

```
app/
  main.py                  FastAPIアプリ初期化・ルーター登録
  config.py                環境変数・設定
  constants.py             UIメッセージ・固定文言
  routers/
    twiml.py               POST /twiml/connect（TwiML応答）
    media_stream.py        WS /media-stream（双方向中継）
  services/
    gemini_live.py         Gemini Liveセッション設定・接続
    audio_converter.py     μ-law⇔PCM16変換・リサンプル（ratecv state管理）
    rag_service.py         In-Memory RAG検索（BM25）＋関連スコア足切り＋300字要約
    audit_logger.py        構造化JSON監査ログ
tests/                     単体テスト
```

## 医療安全上の制約

- **ハルシネーション厳禁**: RAGで取得したマニュアル内容のみを回答する。回答有無の最終防御はモデルのシステムプロンプトが担う。
- **スコア足切り（ノイズフロア）**: BM25スコアが `RAG_MIN_SCORE` 未満のチャンクは捨てる。話題が無関係なクエリを弾くノイズ除去であり、回答記載の有無判定ではない。オンメモリ検索のため低遅延。
- マニュアル外はエスカレーション文言を音声案内する（回線転送は行わない）。

## セットアップ

```bash
python -m pip install -e ".[dev]"
```

### 環境変数

| 変数 | 説明 | 既定値 |
|---|---|---|
| `GCP_PROJECT` | Google Cloud プロジェクトID（Gemini Liveが使用） | （必須） |
| `GCP_LOCATION` | Vertex AI リージョン | `us-central1` |
| `GEMINI_MODEL` | Gemini Liveモデル | `models/gemini-3.1-flash-live-preview` |
| `GEMINI_VOICE` | 音声名 | `Aoede` |
| `RAG_TOP_K` | RAG取得件数 | `3` |
| `RAG_SUMMARY_MAX_CHARS` | 要約最大文字数 | `300` |
| `RAG_MIN_SCORE` | 関連スコア足切り閾値（BM25） | `1.0` |
| `PORT` | サーバーポート | `8080` |

## 起動

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Twilioの着信Webhookを `POST /twiml/connect` に向ける。

## テスト

```bash
python -m pytest tests/ -v --tb=short
```

## 実装状況

Phase 2〜4のアプリケーションコードを実装済み。
Phase 1（Twilio番号取得）は別途実施。
「超緊急ワード検知」（仕様書 Phase 3 / 監査の `BYPASS_EMERGENCY`）は未実装。

## マニュアルデータの更新

マニュアルは `data/manual_chunks.json` に `[{"text": "...", "category": "受付"}, ...]`
形式で格納する（300〜600字/チャンク、カテゴリは `constants.MANUAL_CATEGORIES` に準拠）。
更新時はこのファイルを編集してコミットし、再デプロイするとコンテナ起動時に
メモリへ自動ロードされる（Cloud Runイメージに同梱されるため `.gitignore` / `.dockerignore`
で除外しないこと）。BM25スコアはコーパスに依存するため、実マニュアルに差し替えた際は
`RAG_MIN_SCORE` を再調整すること。
