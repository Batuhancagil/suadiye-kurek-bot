"""Telegram bildirimleri (varsayılan kapalı; birden fazla chat id destekler)."""

from __future__ import annotations

import logging
import os
import re
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_TRUTHY = {"1", "true", "yes", "on"}


def _env_flag(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in _TRUTHY


def telegram_enabled() -> bool:
    """Telegram gönderimi yalnızca TELEGRAM_ENABLED=1 iken açılır."""
    return _env_flag("TELEGRAM_ENABLED", default=False)


def telegram_notify_errors_enabled() -> bool:
    """Hata mesajları ayrıca TELEGRAM_NOTIFY_ERRORS=1 ister (spam önleme)."""
    return telegram_enabled() and _env_flag("TELEGRAM_NOTIFY_ERRORS", default=False)


def _parse_chat_ids(raw: str) -> list[str]:
    """Virgül, boşluk veya noktalı virgülle ayrılmış chat id listesi."""
    if not raw.strip():
        return []
    parts = re.split(r"[,;\s]+", raw.strip())
    return [p.strip() for p in parts if p.strip()]


def _telegram_config() -> tuple[Optional[str], list[str]]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return None, []

    ids: list[str] = []
    for key in ("TELEGRAM_CHAT_IDS", "TELEGRAM_CHAT_ID"):
        val = os.environ.get(key, "").strip()
        if val:
            ids.extend(_parse_chat_ids(val))

    # Yinelenenleri koru, sırayı bozma
    seen: set[str] = set()
    unique: list[str] = []
    for cid in ids:
        if cid not in seen:
            seen.add(cid)
            unique.append(cid)
    return token, unique


def send_telegram(message: str, *, dry_run: bool = False) -> bool:
    if not telegram_enabled():
        logger.info("Telegram kapalı (TELEGRAM_ENABLED değil); mesaj atlandı")
        return False

    token, chat_ids = _telegram_config()
    if not token or not chat_ids:
        logger.warning("Telegram yapılandırılmamış; mesaj: %s", message)
        return False
    if dry_run:
        logger.info("[dry-run] Telegram (%d alıcı): %s", len(chat_ids), message)
        return True

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    ok_any = False
    for chat_id in chat_ids:
        try:
            resp = requests.post(
                url,
                json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
                timeout=30,
            )
            resp.raise_for_status()
            ok_any = True
            logger.debug("Telegram gönderildi: chat_id=%s", chat_id)
        except requests.RequestException as e:
            logger.error("Telegram gönderilemedi (chat_id=%s): %s", chat_id, e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    desc = e.response.json().get("description", "")
                    if desc:
                        logger.error("Telegram API: %s", desc)
                except Exception:
                    pass
    return ok_any


def notify_burst_start(slot_name: str, *, dry_run: bool = False) -> None:
    send_telegram(
        f"[SALDIRI] {slot_name} — rezervasyon yakında açılacak, denemeler başladı",
        dry_run=dry_run,
    )


def notify_booked(slot_name: str, *, dry_run: bool = False) -> None:
    send_telegram(
        f"[OK] {slot_name} dersi rezerve edildi",
        dry_run=dry_run,
    )


def notify_error(context: str, detail: str, *, dry_run: bool = False) -> None:
    if not telegram_notify_errors_enabled():
        logger.info("Telegram hata bildirimi kapalı: %s — %s", context, detail)
        return
    send_telegram(
        f"[ERR] {context}\n{detail}",
        dry_run=dry_run,
    )
