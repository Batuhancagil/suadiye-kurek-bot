#!/usr/bin/env python3
"""Giriş sayfası HTML yapısını kaydet (credentials gerekmez)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright

from src.slots import SCHEDULE_URL

OUT = ROOT / "screenshots"
OUT.mkdir(exist_ok=True)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(SCHEDULE_URL, wait_until="domcontentloaded", timeout=90_000)
        html_path = OUT / "login_page.html"
        html_path.write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(OUT / "login_page.png"), full_page=True)
        print("URL:", page.url)
        print("Saved:", html_path)
        inputs = page.locator("input").evaluate_all(
            "els => els.map(e => ({type: e.type, name: e.name, id: e.id, placeholder: e.placeholder}))"
        )
        print("Inputs:", inputs)
        buttons = page.locator("button, input[type=submit]").evaluate_all(
            "els => els.map(e => ({tag: e.tagName, type: e.type, text: e.innerText || e.value}))"
        )
        print("Buttons:", buttons)
        browser.close()


if __name__ == "__main__":
    main()
