#!/usr/bin/env python3
"""Tek seferlik rezervasyon testi: python scripts/test_booking.py 2026-05-24 18"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env = ROOT / ".env"
if _env.is_file():
    for line in _env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from playwright.sync_api import sync_playwright

from src.booker import BookResult, try_book_slot
from src.notify import notify_booked, notify_error
from src.slots import TRT, opening_datetime, slot_display_name, slot_for_datetime


def main() -> int:
    p = argparse.ArgumentParser(description="Tek ders rezervasyon testi")
    p.add_argument("date", help="YYYY-MM-DD")
    p.add_argument("hour", type=int, help="Başlangıç saati (ör. 18)")
    p.add_argument("--end-hour", type=int, default=None, help="Bitiş saati (varsayılan: hour+1)")
    p.add_argument("--headed", action="store_true")
    args = p.parse_args()

    y, m, d = map(int, args.date.split("-"))
    lesson_dt = datetime(y, m, d, args.hour, 0, tzinfo=TRT)
    end_h = args.end_hour if args.end_hour is not None else args.hour + 1
    slot = slot_for_datetime(lesson_dt, end_hour=end_h)
    display = slot_display_name(slot, lesson_dt)
    opens = opening_datetime(slot, lesson_dt=lesson_dt)

    print(f"Ders: {display}")
    print(f"Açılış: {opens.strftime('%d.%m.%Y %H:%M')} TRT")
    print(f"Şimdi:  {datetime.now(TRT).strftime('%d.%m.%Y %H:%M')} TRT")
    print("---")

    headless = not args.headed
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        page = browser.new_page()
        result = try_book_slot(page, slot, lesson_dt=lesson_dt)
        browser.close()

    print(f"Sonuç: {result.value}")

    if result == BookResult.BOOKED:
        notify_booked(display)
        print("Telegram [OK] gönderildi.")
        return 0
    if result == BookResult.ALREADY_BOOKED:
        print("Zaten kayıtlı — pipeline OK.")
        return 0
    if result in (BookResult.LOGIN_FAILED, BookResult.ERROR):
        notify_error(display, result.value)
    return 1


if __name__ == "__main__":
    sys.exit(main())
