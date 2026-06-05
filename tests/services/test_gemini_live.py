"""gemini_liveの単体テスト（関数宣言の形状が仕様書§3.2と一致すること）"""

from app.constants import MANUAL_CATEGORIES
from app.services import gemini_live


def test_function_declaration_matches_spec():
    decl = gemini_live.function_declaration()

    assert decl["name"] == "search_ophthalmology_manual"
    params = decl["parameters"]
    assert params["type"] == "OBJECT"
    assert set(params["properties"].keys()) == {"query", "category"}
    assert params["properties"]["category"]["enum"] == MANUAL_CATEGORIES
    assert params["required"] == ["query"]
