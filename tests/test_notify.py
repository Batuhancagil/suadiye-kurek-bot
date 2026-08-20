"""Telegram chat id ayrıştırma ve kill-switch testleri."""

from unittest.mock import patch

from src.notify import _parse_chat_ids, notify_error, send_telegram, telegram_enabled


def test_single_id():
    assert _parse_chat_ids("123456") == ["123456"]


def test_multiple_comma():
    assert _parse_chat_ids("111, 222 , 333") == ["111", "222", "333"]


def test_negative_group_id():
    assert _parse_chat_ids("-1001234567890") == ["-1001234567890"]


def test_telegram_disabled_by_default(monkeypatch):
    monkeypatch.delenv("TELEGRAM_ENABLED", raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    assert telegram_enabled() is False
    with patch("src.notify.requests.post") as post:
        assert send_telegram("merhaba") is False
        post.assert_not_called()


def test_telegram_enabled_sends(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ENABLED", "1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    with patch("src.notify.requests.post") as post:
        post.return_value.raise_for_status = lambda: None
        assert send_telegram("merhaba") is True
        post.assert_called_once()


def test_notify_error_off_even_when_telegram_on(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ENABLED", "1")
    monkeypatch.delenv("TELEGRAM_NOTIFY_ERRORS", raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    with patch("src.notify.requests.post") as post:
        notify_error("slot", "Giriş başarısız")
        post.assert_not_called()


def test_notify_error_on_when_flag_set(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ENABLED", "1")
    monkeypatch.setenv("TELEGRAM_NOTIFY_ERRORS", "1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    with patch("src.notify.requests.post") as post:
        post.return_value.raise_for_status = lambda: None
        notify_error("slot", "Giriş başarısız")
        post.assert_called_once()
