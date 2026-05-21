#!/usr/bin/env python3
"""Site yapısını incelemek için headed Playwright (credentials .env'den)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

env_path = ROOT / ".env"
if env_path.is_file():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from playwright.sync_api import sync_playwright

from src.booker import login_if_needed
from src.slots import SCHEDULE_URL, TARGET_SLOTS, lesson_datetime


def main() -> None:
    headless = os.environ.get("HEADLESS", "0") == "1"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=200)
        page = browser.new_page()
        page.goto(SCHEDULE_URL, timeout=90_000)
        print("URL:", page.url)
        print("Title:", page.title())

        if not login_if_needed(page):
            print("LOGIN FAILED")
            page.screenshot(path=str(ROOT / "screenshots" / "inspect_login_fail.png"))
            browser.close()
            sys.exit(1)

        print("Login OK, URL:", page.url)
        out = ROOT / "screenshots" / "inspect_after_login.html"
        out.parent.mkdir(exist_ok=True)
        out.write_text(page.content(), encoding="utf-8")
        print("HTML saved:", out)

        slot = TARGET_SLOTS[list(TARGET_SLOTS.keys())[0]]
        lesson = lesson_datetime(slot)
        print("Sample lesson:", lesson)

        page.pause()
        browser.close()


if __name__ == "__main__":
    main()
