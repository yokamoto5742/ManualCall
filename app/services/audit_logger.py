"""構造化JSON監査ログ（§5.2 / Cloud Logging連携）"""

import json
import logging
import sys
from datetime import datetime, timezone

_logger = logging.getLogger("audit")


def _configure() -> None:
    if _logger.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


_configure()


def build_audit_entry(
    call_id: str,
    rag_query: str,
    rag_status: str,
    response_type: str,
) -> dict[str, str]:
    """監査ログの構造化JSONエントリを生成する（§5.2）

    rag_status: SUCCESS / TIMEOUT
    response_type: MANUAL_FOUND / NO_MANUAL_DESCRIPTION
    """
    return {
        "severity": "INFO",
        "call_id": call_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rag_query": rag_query,
        "rag_status": rag_status,
        "response_type": response_type,
    }


def log_rag_event(
    call_id: str,
    rag_query: str,
    rag_status: str,
    response_type: str,
) -> None:
    """RAG検索1件分の監査ログを構造化JSONで出力する"""
    entry = build_audit_entry(call_id, rag_query, rag_status, response_type)
    _logger.info(json.dumps(entry, ensure_ascii=False))
