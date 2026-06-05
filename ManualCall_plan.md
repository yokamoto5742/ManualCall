仕様書：眼科業務マニュアル専用電話応対AIボットEyeManual開発計画

本仕様書は、院内スタッフが電話（VoIP回線）を通じて、眼科の院内業務マニュアルや電話応対手順をAIにリアルタイム音声で問い合わせできるバックエンドWebアプリケーションの最終実装仕様である。2026年6月時点の公開情報に基づき、Gemini 3.1 Flash Live を前提とした実装方式、技術スタック、運用方針、および実装ステップを定義する。

## 1. 概要・目的
* **目的:** 眼科スタッフが受付・検査・急患・手術説明などの院内業務マニュアルを即時に確認できる電話応対AIを実現し、現場の判断支援を安全に行う。
* **コア原則:** マニュアル外の推測回答（ハルシネーション）を徹底的に排除し、医療安全を最優先とする。

---

## 2. システムアーキテクチャ・技術スタック

### 2.1 採用技術一覧
* **電話回線・音声中継:** Twilio Programmable Voice + Media Streams (双方向 WebSocket 中継)
* **音声会話AIモデル:** Gemini 3.1 Flash Live (`models/gemini-3.1-flash-live-preview`)
* **バックエンドサーバー:** Node.js + TypeScript + Fastify (WebSocket/リアルタイムI/O制御)
* **RAG基盤:** Vertex AI RAG Engine
* **ホスティング・インフラ:** Google Cloud Run (または GKE) + Secret Manager + Cloud Logging

### 2.2 音声プロトコル・変換要件
バックエンドサーバーは、Twilio と Gemini Live API 間の仲介者として、以下のフォーマット変換をリアルタイムに双方向で行う。
* **ユーザー発話（Twilio 入力）:** `audio/x-mulaw` (8,000Hz, 8-bit, モノラル) 
    ➡️ **[変換]** ➡️ `audio/pcm` (16,000Hz, 16-bit, Little-Endian, モノラル) として Gemini へ送信。
* **AI応答（Gemini 出力）:** `audio/pcm` (16,000Hz, 16-bit) 
    ➡️ **[変換]** ➡️ `audio/x-mulaw` (8,000Hz, 8-bit) として Twilio へ返送。

---

## 3. 通信プロトコル・ペイロード仕様

### 3.1 Twilio 着信時エントリポイント (TwiML)
* **Method:** `POST`
* **Endpoint:** `/twiml/connect`
* **Response:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="ja-JP">眼科業務マニュアル応対ボットに接続します。少々お待ちください。</Say>
    <Connect>
        <Stream url="wss://YOUR_DOMAIN.a.run.app/media-stream" />
    </Connect>
</Response>

```

### 3.2 Gemini Live API 初期化セッション (SessionInit)

WebSocket 接続確立直後にバックエンドから Gemini へ送信する初期化 JSON ペイロード。

```json
{
  "setup": {
    "model": "models/gemini-3.1-flash-live-preview",
    "generationConfig": {
      "responseModalities": ["AUDIO"],
      "speechConfig": {
        "voiceConfig": {
          "prebuiltVoiceConfig": {
            "voiceName": "Aoede"
          }
        }
      }
    },
    "systemInstruction": {
      "parts": [
        {
          "text": "あなたは「◯◯眼科」のスタッフ専用・業務マニュアル応答AIアシスタントです。電話口の相手は当院の受付・検査スタッフです。丁寧、迅速、聞き取りやすい日本語で応対してください。1回の応答は2〜3文、15秒以内を目安に短くしてください。回答は必ず提供された【マニュアル検索結果】に基づいてください。検索結果に記載がない場合は、推測せず、「その件についてはマニュアルに記載がありません。管理者に直接確認してください」と伝えてください。自分の一般医療知識だけで補完してはいけません。"
        }
      ]
    },
    "tools": [
      {
        "functionDeclarations": [
          {
            "name": "search_ophthalmology_manual",
            "description": "眼科の院内業務マニュアル（受付、検査、手術、会計、急患対応など）を検索します。",
            "parameters": {
              "type": "OBJECT",
              "properties": {
                "query": {
                  "type": "STRING",
                  "description": "スタッフからの質問キーワードや文章"
                },
                "category": {
                  "type": "STRING",
                  "enum": ["受付", "検査", "手術", "会計", "急患", "共通"],
                  "description": "検索対象のカテゴリ分類"
                }
              },
              "required": ["query"]
            }
          }
        ]
      }
    ]
  }
}

```

---

## 4. RAG（検索拡張生成）仕様と低遅延対策

Gemini 3.1 Flash Live は**非同期関数呼び出しに未対応**であるため、ツール実行完了までモデルの音声生成がブロックされる。これを踏まえ、以下の低遅延制約を実装する。

### 4.1 RAG制約・運用方針

1. **無音許容とフィラーの不採用:** RAG検索中の無音時間が1秒未満である実態を想定し、「少々お待ちください」等のフィラー音声はバックエンドから動的挿入せず、無音のまま検索処理を最速で完了させる。
2. **検索エンジンの制限:** Vertex AI RAG Engine への問い合わせは、最大件数 `Top-3`、チャンクサイズ `300〜600文字` に設定する。
3. **バックエンド側でのタイムアウト制御:** 検索処理には最大 `800ms` の厳格なタイムアウトを設け、超過した場合は以下の固定テキストをツールレスポンスとして即座に返却する。
* *タイムアウト時返却メッセージ:* `"エラー：マニュアル検索がタイムアウトしました。管理者または先輩スタッフに通常通りの手順を直接確認してください。"`


4. **要約の軽量化:** 検索されたマニュアル生テキストは Live API にそのまま投入せず、バックエンド側で「最大300文字程度のプレーンテキスト」に要約・整形した上で `search_ophthalmology_manual` の戻り値としてモデルへ返却する。

---

## 5. 医療安全・エラーハンドリング運用方針

### 5.1 マニュアル外・対応不可時のエスカレーション

マニュアルに該当記載がない、あるいはAIが意図を認識できない等のケースにおいては、Twilio 側での電話回線強制転送（`<Dial>` 等）は行わない。システムプロンプトの指示に従い、音声で一貫して **「その件についてはマニュアルに記載がありません。管理者に直接確認してください」** とアナウンスし、スタッフ自身による対人エスカレーションを促す。

### 5.3 監査ログ (Audit Log)

Cloud Logging を用い、以下の構造化 JSON ログを出力する。

```json
{
  "severity": "INFO",
  "call_id": "TwilioのStreamSidまたはCallSid",
  "timestamp": "2026-06-XXTXX:XX:XXZ",
  "rag_query": "スタッフの質問内容",
  "rag_status": "SUCCESS / TIMEOUT / BYPASS_EMERGENCY",
  "response_type": "MANUAL_FOUND / NO_MANUAL_DESCRIPTION"
}

```

---

## 6. データ運用・メンテナンス方針

* **更新頻度:** 導入初期フェーズにおけるマニュアル（PDF、Word、テキスト等）の更新頻度は **「月1回程度」** とする。
* **運用方法:** 管理者が更新されたマニュアルドキュメントを Vertex AI RAG Engine の対象データストアへ手動で再アップロード、またはコンソール経由でインデックスの再パース・同期を行う。運用が安定するまでは自動同期パイプライン（Google Drive 等との自動連携）の構築は見送り、構成のシンプルさを維持する。

---

## 7. 実装・デプロイステップ

* **Phase 1：環境構築とデータ準備（1〜2週）**
* Twilio 番号の取得、Vertex AI RAG Engine への初期マニュアル（PDF）のインデックス登録。


* **Phase 2：リアルタイム音声ブリッジ構築（3〜4週）**
* Fastify を用いた WebSocket サーバー実装、μ-law ⇔ PCM16 の音声相互変換ロジックの実装。
* Gemini Live API セッションとの双方向音声ストリーミングの安定化および発話割り込み（Barge-in）制御の確認。


*  Phase 3：RAGとセーフティ統合（5〜6週）
* `search_ophthalmology_manual` ツールの実装、800ms タイムアウト処理、超緊急ワード検知ロジックの実装。


* **Phase 4：本番導入と評価（7〜8週）**
* Cloud Run へのデプロイ、実機（電話機）を用いた認識率・応答速度（1.5〜2.5秒以内）のテスト、および運用マニュアルの整備。



```