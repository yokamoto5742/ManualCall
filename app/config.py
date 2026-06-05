"""環境変数・設定（Secret Manager由来の値を含む）"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Google Cloud / Vertex AI
    gcp_project: str
    gcp_location: str
    rag_corpus: str

    # Gemini Live API
    gemini_model: str
    gemini_voice: str

    # RAG検索パラメータ（§4.1）
    rag_timeout_seconds: float
    rag_top_k: int
    rag_summary_max_chars: int

    # サーバー
    host: str
    port: int


def load_settings() -> Settings:
    return Settings(
        gcp_project=os.environ.get("GCP_PROJECT", ""),
        gcp_location=os.environ.get("GCP_LOCATION", "us-central1"),
        rag_corpus=os.environ.get("RAG_CORPUS", ""),
        gemini_model=os.environ.get(
            "GEMINI_MODEL", "models/gemini-3.1-flash-live-preview"
        ),
        gemini_voice=os.environ.get("GEMINI_VOICE", "Aoede"),
        rag_timeout_seconds=float(os.environ.get("RAG_TIMEOUT_SECONDS", "0.8")),
        rag_top_k=int(os.environ.get("RAG_TOP_K", "3")),
        rag_summary_max_chars=int(os.environ.get("RAG_SUMMARY_MAX_CHARS", "300")),
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8080")),
    )


settings = load_settings()
