"""Telegram chat id ayrıştırma testleri."""

from src.notify import _parse_chat_ids


def test_single_id():
    assert _parse_chat_ids("123456") == ["123456"]


def test_multiple_comma():
    assert _parse_chat_ids("111, 222 , 333") == ["111", "222", "333"]


def test_negative_group_id():
    assert _parse_chat_ids("-1001234567890") == ["-1001234567890"]
