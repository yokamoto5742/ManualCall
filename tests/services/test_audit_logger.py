"""audit_loggerの単体テスト（構造化JSONエントリの形状）"""

import json

from app.services import audit_logger


def test_build_audit_entry_shape():
    entry = audit_logger.build_audit_entry(
        call_id="CA123",
        rag_query="受付の開錠時刻",
        rag_status="SUCCESS",
        response_type="MANUAL_FOUND",
    )

    assert entry["severity"] == "INFO"
    assert entry["call_id"] == "CA123"
    assert entry["rag_query"] == "受付の開錠時刻"
    assert entry["rag_status"] == "SUCCESS"
    assert entry["response_type"] == "MANUAL_FOUND"
    assert "timestamp" in entry


def test_entry_is_json_serializable_with_japanese():
    entry = audit_logger.build_audit_entry(
        "CA1", "急患対応", "TIMEOUT", "NO_MANUAL_DESCRIPTION"
    )
    dumped = json.dumps(entry, ensure_ascii=False)

    # 日本語がそのまま保持され、再パース可能であること
    assert "急患対応" in dumped
    assert json.loads(dumped) == entry
