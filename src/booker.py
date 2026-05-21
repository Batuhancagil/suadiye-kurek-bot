"""SuperSaaS Playwright rezervasyon akışı."""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .slots import (
    SCHEDULE_URL,
    TRT,
    TargetSlot,
    lesson_datetime,
    opening_datetime,
    slot_display_name,
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = BASE_DIR / "screenshots"

_PAGE_WAIT = "domcontentloaded"
_GOTO_TIMEOUT = 90_000


class BookResult(str, Enum):
    BOOKED = "booked"
    ALREADY_BOOKED = "already_booked"
    NOT_OPEN = "not_open"
    FULL = "full"
    NOT_FOUND = "not_found"
    LOGIN_FAILED = "login_failed"
    ERROR = "error"


def _credentials() -> tuple[str, str]:
    email = os.environ.get("SUPERSAAS_EMAIL", "").strip()
    password = os.environ.get("SUPERSAAS_PASSWORD", "").strip()
    if not email or not password:
        raise RuntimeError(
            "SUPERSAAS_EMAIL ve SUPERSAAS_PASSWORD ortam değişkenleri gerekli"
        )
    return email, password


def _save_screenshot(page: Page, name: str) -> None:
    try:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        path = SCREENSHOT_DIR / f"{name}.png"
        page.screenshot(path=str(path), full_page=True)
        logger.info("Ekran görüntüsü: %s", path)
    except Exception as e:
        logger.warning("Screenshot alınamadı: %s", e)


def login_if_needed(page: Page) -> bool:
    page.goto(SCHEDULE_URL, wait_until=_PAGE_WAIT, timeout=_GOTO_TIMEOUT)

    pwd = page.locator('input[type="password"]')
    try:
        pwd.wait_for(state="visible", timeout=8000)
    except PlaywrightTimeout:
        if "login" not in page.url.lower() and page.locator(
            "#schedule, .schedule, table, .fc-view"
        ).count() > 0:
            return True
        return True

    email, password = _credentials()
    name_input = page.locator("#name, input[name='name']").first
    if name_input.count() == 0:
        name_input = page.locator('input[type="email"], input[type="text"]').first
    name_input.fill(email)
    page.locator("#password, input[name='password']").first.fill(password)

    submit = page.get_by_role("button", name=re.compile(r"giriş|login", re.I))
    if submit.count() == 0:
        submit = page.locator('button[type="submit"], input[type="submit"]').first
    else:
        submit = submit.first
    submit.click()
    page.wait_for_load_state(_PAGE_WAIT, timeout=_GOTO_TIMEOUT)

    if page.locator('input[type="password"]').is_visible():
        return False
    return True


def _week_headers(page: Page) -> list[tuple[int, str, int]]:
    """Haftalık görünüm: (sütun_no, gün_kısaltması, ayın_günü)."""
    headers: list[tuple[int, str, int]] = []
    for th in page.locator("thead th:has(.big_weekday)").all():
        hid = th.get_attribute("id") or ""
        if not re.fullmatch(r"h\d+", hid):
            continue
        col = int(hid[1:])
        wd = th.locator(".big_weekday").inner_text().strip().upper()
        day_txt = th.locator(".big_day").inner_text().strip()
        if day_txt.isdigit():
            headers.append((col, wd, int(day_txt)))
    return headers


def _navigate_to_date(page: Page, target: datetime, slot: TargetSlot) -> Optional[int]:
    """Hedef ders gününün haftasına git; sütun indeksini döndür."""
    page.wait_for_selector("#viewholder", timeout=20_000)
    wd_abbr = slot.header_weekday
    target_day = target.day

    for _ in range(30):
        for col, wd, day in _week_headers(page):
            if wd == wd_abbr and day == target_day:
                return col

        day_cell = page.locator(
            f'#monthnav td span:text-is("{target_day}")'
        ).first
        if day_cell.count():
            day_cell.click()
            page.wait_for_timeout(900)
            continue

        page.locator('i[onclick="arrow_jump(1)"]').first.click()
        page.wait_for_timeout(900)

    return None


def _slot_time_pattern(slot: TargetSlot) -> re.Pattern[str]:
    return re.compile(
        rf"{slot.start_hour}:00\s*[−\-]\s*{slot.end_hour}:00",
        re.I,
    )


def _find_slot_element(page: Page, slot: TargetSlot, lesson_dt: datetime, col: int):
    """SuperSaaS chip (KÜREK DERS) öğesini bul."""
    day_sel = f"#d{col}"
    time_pat = _slot_time_pattern(slot)
    chips = page.locator(f"{day_sel} div.chip[onclick*='vs(event,']")
    for i in range(chips.count()):
        chip = chips.nth(i)
        try:
            head = chip.locator(".head").inner_text().replace("\xa0", " ")
            if time_pat.search(head):
                return chip
        except Exception:
            continue
    return None


def _chip_status(chip) -> Optional[BookResult]:
    classes = (chip.get_attribute("class") or "").split()
    if "my" in classes:
        return BookResult.ALREADY_BOOKED
    if any(c.startswith("full") for c in classes):
        return BookResult.FULL
    try:
        small = chip.locator("small").inner_text(timeout=500)
        if re.search(r"\(\d+/\d+\)", small):
            m = re.search(r"\((\d+)/(\d+)\)", small)
            if m and int(m.group(1)) >= int(m.group(2)):
                return BookResult.FULL
    except Exception:
        pass
    return None


def _open_slot_dialog(page: Page, chip) -> bool:
    chip.click(timeout=8000)
    try:
        page.locator("#bbox").wait_for(state="visible", timeout=6000)
        return True
    except PlaywrightTimeout:
        return False


def _click_new_participation(page: Page) -> bool:
    try:
        page.evaluate("typeof newbooking === 'function' && newbooking()")
        page.locator("#booking").wait_for(state="visible", timeout=6000)
        _hide_bbox_if_open(page)
        return True
    except PlaywrightTimeout:
        pass

    btn = page.locator("#bbox_new")
    if btn.count():
        try:
            btn.click(force=True, timeout=5000)
            page.locator("#booking").wait_for(state="visible", timeout=6000)
            _hide_bbox_if_open(page)
            return True
        except PlaywrightTimeout:
            pass
    return False


def _hide_bbox_if_open(page: Page) -> None:
    try:
        if page.locator("#bbox").is_visible():
            page.evaluate(
                "typeof hideDialog === 'function' && hideDialog('bbox')"
            )
            page.wait_for_timeout(400)
    except Exception:
        pass


def _select_experience_tecrubeli(page: Page) -> bool:
    sel = page.locator("#booking_field_1_r")
    if sel.count():
        sel.select_option(value="Tecrübeli")
        return True

    label_pat = re.compile(r"tecrübeli|tecrubeli", re.I)
    for s in page.locator("select").all():
        try:
            if any(label_pat.search(o) for o in s.locator("option").all_inner_texts()):
                s.select_option(value="Tecrübeli")
                return True
        except Exception:
            continue
    return False


def _submit_booking(page: Page) -> bool:
    _hide_bbox_if_open(page)
    btn = page.locator('#booking button.bttn[type="submit"]')
    if btn.count() == 0:
        btn = page.locator("#booking").get_by_role(
            "button", name=re.compile(r"Katılım Oluştur", re.I)
        )
    if btn.count():
        btn.first.click(force=True, timeout=8000)
        page.wait_for_timeout(2000)
        return True
    return False


def _detect_booking_error(page: Page) -> Optional[BookResult]:
    """Form gönderimi sonrası hata kutusu (çok erken, dolu vb.)."""
    error_pat = re.compile(
        r"sorun oluştu|sorun olustu|gerçekleşemedi|gerceklestirilemedi|"
        r"çok erken|cok erken|"
        r"kayıtlar.*açılıyor|kayitlar.*aciliyor|"
        r"4\s*gün.*önce|4\s*gun.*once",
        re.I,
    )
    try:
        if page.get_by_text(error_pat).first.is_visible(timeout=3000):
            return BookResult.NOT_OPEN
    except PlaywrightTimeout:
        pass
    flash = page.locator(".flash .flshr, .flash .flsh, [role='alert']")
    try:
        if flash.count() and flash.first.is_visible(timeout=1000):
            txt = flash.first.inner_text()
            if error_pat.search(txt):
                return BookResult.NOT_OPEN
    except Exception:
        pass
    return None


def _detect_success(page: Page) -> bool:
    """Yalnızca net başarı metinleri (kaydedilirken gibi hata metinlerini elesin)."""
    success_patterns = (
        re.compile(r"başarıyla", re.I),
        re.compile(r"basariyla", re.I),
        re.compile(r"katılımınız.*oluşturuldu", re.I),
        re.compile(r"katiliminiz.*olusturuldu", re.I),
        re.compile(r"confirmed", re.I),
    )
    for pat in success_patterns:
        try:
            if page.get_by_text(pat).first.is_visible(timeout=2000):
                return True
        except PlaywrightTimeout:
            continue
    return False


def _detect_already_booked(page: Page) -> bool:
    pat = re.compile(
        r"zaten.*kayıt|already.*book|mevcut.*katılım|katılımınız",
        re.I,
    )
    try:
        return page.get_by_text(pat).first.is_visible(timeout=1500)
    except PlaywrightTimeout:
        return False


def _detect_full_or_closed(page: Page) -> Optional[BookResult]:
    full_pat = re.compile(r"dolu|full|kapalı|closed|yer yok", re.I)
    not_open_pat = re.compile(
        r"henüz.*açılm|not.*open|4\s*gün|dört\s*gün|erişilemez",
        re.I,
    )
    try:
        if page.get_by_text(not_open_pat).first.is_visible(timeout=1000):
            return BookResult.NOT_OPEN
    except PlaywrightTimeout:
        pass
    try:
        if page.get_by_text(full_pat).first.is_visible(timeout=1000):
            return BookResult.FULL
    except PlaywrightTimeout:
        pass
    return None


def try_book_slot(
    page: Page,
    slot: TargetSlot,
    *,
    lesson_dt: Optional[datetime] = None,
    screenshot_on_error: bool = True,
) -> BookResult:
    lesson = lesson_dt or lesson_datetime(slot)
    display = slot_display_name(slot, lesson)
    now = datetime.now(TRT)
    opens = opening_datetime(slot, now, lesson_dt=lesson)
    if now < opens:
        logger.info(
            "[%s] Rezervasyon henüz açılmadı (açılış %s TRT)",
            display,
            opens.strftime("%d.%m.%Y %H:%M"),
        )
        return BookResult.NOT_OPEN

    try:
        if not login_if_needed(page):
            if screenshot_on_error:
                _save_screenshot(page, "login_failed")
            return BookResult.LOGIN_FAILED

        col = _navigate_to_date(page, lesson, slot)
        if col is None:
            logger.info("[%s] Takvimde hedef gün bulunamadı", display)
            return BookResult.NOT_FOUND

        cell = _find_slot_element(page, slot, lesson, col)
        if cell is None:
            logger.info("[%s] Slot chip bulunamadı (sütun %s)", display, col)
            return BookResult.NOT_FOUND

        chip_status = _chip_status(cell)
        if chip_status == BookResult.ALREADY_BOOKED:
            logger.info("[%s] Zaten kayıtlı (chip)", display)
            return BookResult.ALREADY_BOOKED
        if chip_status == BookResult.FULL:
            logger.info("[%s] Ders dolu", display)
            return BookResult.FULL

        if not _open_slot_dialog(page, cell):
            return BookResult.ERROR

        if _detect_already_booked(page):
            logger.info("[%s] Zaten kayıtlı", display)
            return BookResult.ALREADY_BOOKED

        status = _detect_full_or_closed(page)
        if status:
            return status

        if not _click_new_participation(page):
            if _detect_already_booked(page):
                return BookResult.ALREADY_BOOKED
            status = _detect_full_or_closed(page)
            if status:
                return status
            logger.info("[%s] 'Yeni katılım' bulunamadı", display)
            return BookResult.NOT_OPEN

        page.wait_for_timeout(500)

        if not _select_experience_tecrubeli(page):
            logger.warning("[%s] Tecrübeli seçilemedi, yine de kaydet deneniyor", display)

        if not _submit_booking(page):
            if screenshot_on_error:
                _save_screenshot(page, "submit_failed")
            return BookResult.ERROR

        page.wait_for_timeout(800)

        err = _detect_booking_error(page)
        if err:
            logger.info("[%s] Kayıt reddedildi (henüz açılmadı / site hatası)", display)
            if screenshot_on_error:
                _save_screenshot(page, "booking_rejected")
            return err

        if _detect_success(page):
            logger.info("[%s] Rezervasyon başarılı", display)
            return BookResult.BOOKED

        if _detect_already_booked(page):
            return BookResult.ALREADY_BOOKED

        status = _detect_full_or_closed(page)
        if status:
            return status

        if screenshot_on_error:
            _save_screenshot(page, "booking_unknown")
        logger.warning("[%s] Kayıt sonucu belirsiz — başarı sayılmadı", display)
        return BookResult.ERROR

    except Exception as e:
        logger.exception("[%s] Hata: %s", display, e)
        if screenshot_on_error:
            _save_screenshot(page, "exception")
        return BookResult.ERROR
