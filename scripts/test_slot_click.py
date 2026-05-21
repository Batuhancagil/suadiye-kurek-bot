#!/usr/bin/env python3
"""Adim 4: Takvimde hedef slota tiklama + modal inceleme."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")

from playwright.sync_api import sync_playwright

from src.booker import (
    _click_new_participation,
    _find_slot_element,
    _navigate_to_date,
    _open_slot_dialog,
    login_if_needed,
)
from src.slots import SlotId, TARGET_SLOTS, lesson_datetime


def main() -> int:
    out = ROOT / "screenshots"
    out.mkdir(exist_ok=True)
    slot = TARGET_SLOTS[SlotId.TUESDAY]
    lesson = lesson_datetime(slot)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        if not login_if_needed(page):
            print("Login basarisiz")
            return 1
        print("Login OK")
        col = _navigate_to_date(page, lesson, slot)
        if col is None:
            print("Hedef gun bulunamadi:", lesson.date())
            browser.close()
            return 1
        cell = _find_slot_element(page, slot, lesson, col)
        if cell is None:
            print("Slot bulunamadi:", slot.label_tr, lesson.date(), "col", col)
            page.screenshot(path=str(out / "slot_not_found.png"), full_page=True)
            (out / "slot_not_found.html").write_text(page.content(), encoding="utf-8")
            browser.close()
            return 1
        print("Slot bulundu col=%s, bbox aciliyor..." % col)
        _open_slot_dialog(page, cell)
        page.wait_for_timeout(1200)
        (out / "after_slot_click.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(out / "after_slot_click.png"), full_page=True)
        has_new = _click_new_participation(page)
        print("Yeni katilim butonu:", "VAR" if has_new else "YOK")
        if has_new:
            page.wait_for_timeout(800)
            (out / "after_new_katilim.html").write_text(page.content(), encoding="utf-8")
            page.screenshot(path=str(out / "after_new_katilim.png"), full_page=True)
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
