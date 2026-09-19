from creative_tools import _extract_json, _safe_filename


def test_extract_json_from_plain_text():
    data = _extract_json('{"title":"Demo","slides":[]}')
    assert data["title"] == "Demo"


def test_extract_json_from_code_fence():
    fence = chr(96) * 3
    text = fence + "json\n" + '{"title":"Demo","slides":[]}' + "\n" + fence
    data = _extract_json(text)
    assert data["title"] == "Demo"


def test_safe_filename():
    assert _safe_filename("Demo: deck / 2026", "fallback").startswith("Demo")
