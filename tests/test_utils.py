from __future__ import annotations

from toss_bot.utils import extract_items


def test_extract_items_handles_list_and_dict_payloads():
    assert extract_items([{"a": 1}], "candles") == [{"a": 1}]
    assert extract_items({"candles": [1, 2]}, "candles") == [1, 2]
    assert extract_items({"items": [3]}, "candles", "items") == [3]
    assert extract_items({"candles": "not-a-list"}, "candles") == []
    assert extract_items(None, "candles") == []
