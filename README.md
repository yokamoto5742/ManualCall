# EyeManual（ManualCall）

眼科クリニックスタッフが電話（VoIP）で院内業務マニュアルをAIにリアルタイム問い合わせできるバックエンドWebアプリケーション。

詳細仕様は `ManualCall_plan.md` を参照。

## アーキテクチャ

Twilio Media Streams（μ-law 8kHz）と Gemini 3.1 Flash Live（PCM16 16kHz）を
FastAPIのWebSocketで双方向中継し、Vertex AI RAG Engine で院内マニュアルを検索する。

```
Twilio ──WS──> /media-stream ──> Gemini Live API
                    │                   │ toolCall
                    │                   ▼
                    └────────── Vertex AI RAG Engine（800msタイムアウト）
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
    rag_service.py         RAG検索＋800msタイムアウト＋300字要約
    audit_logger.py        構造化JSON監査ログ
tests/                     単体テスト
```

## 医療安全上の制約

- **ハルシネーション厳禁**: RAGで取得したマニュアル内容のみを回答する。
- **RAGタイムアウト**: 検索は800ms以内。超過時は固定文言を返却する（`constants.RAG_TIMEOUT_MESSAGE`）。
- マニュアル外はエスカレーション文言を音声案内する（回線転送は行わない）。

## セットアップ

```bash
python -m pip install -e ".[dev]"
```

### 環境変数

| 変数 | 説明 | 既定値 |
|---|---|---|
| `GCP_PROJECT` | Google Cloud プロジェクトID | （必須） |
| `GCP_LOCATION` | Vertex AI リージョン | `us-central1` |
| `RAG_CORPUS` | RAG Engine コーパスのリソース名 | （必須） |
| `GEMINI_MODEL` | Gemini Liveモデル | `models/gemini-3.1-flash-live-preview` |
| `GEMINI_VOICE` | 音声名 | `Aoede` |
| `RAG_TIMEOUT_SECONDS` | RAGタイムアウト秒 | `0.8` |
| `RAG_TOP_K` | RAG取得件数 | `3` |
| `RAG_SUMMARY_MAX_CHARS` | 要約最大文字数 | `300` |
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
Phase 1（Twilio番号取得・RAGコーパスへのマニュアル登録）は別途実施。
「超緊急ワード検知」（仕様書 Phase 3 / 監査の `BYPASS_EMERGENCY`）は未実装。
