#!/usr/bin/env python3
"""Adim 3: SuperSaaS giris testi (screenshot + URL, sifre yazdirilmaz)."""

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

from src.booker import login_if_needed
from src.slots import SCHEDULE_URL


def main() -> int:
    out = ROOT / "screenshots"
    out.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        ok = login_if_needed(page)
        page.screenshot(path=str(out / "after_login.png"), full_page=True)
        html_path = out / "schedule_after_login.html"
        html_path.write_text(page.content(), encoding="utf-8")
        print("Login:", "BASARILI" if ok else "BASARISIZ")
        print("URL:", page.url)
        print("Baslik:", page.title())
        print("Kayit:", html_path)
        print("Screenshot:", out / "after_login.png")
        if not ok:
            browser.close()
            return 1
        body = page.locator("body").inner_text()[:500]
        print("Sayfa onizleme (500 karakter):", body.replace("\n", " ")[:500])
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
