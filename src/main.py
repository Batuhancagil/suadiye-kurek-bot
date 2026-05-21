#!/usr/bin/env python3
"""Suadiye Kürek Kulübü SuperSaaS rezervasyon botu."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from .booker import BookResult, try_book_slot
from .config import apply_cli_overrides, load_config
from .notify import notify_booked, notify_burst_start, notify_error
from .slots import (
    TRT,
    TargetSlot,
    lesson_datetime,
    opening_datetime,
    slot_display_name,
    slots_for_run,
)

BASE_DIR = Path(__file__).resolve().parent.parent
POLL_STATE_FILE = BASE_DIR / ".poll_last_run"


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _load_env() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def _should_run_poll(interval_minutes: int, *, force: bool) -> bool:
    if force:
        return True
    now = time.time()
    if POLL_STATE_FILE.is_file():
        try:
            last = float(POLL_STATE_FILE.read_text(encoding="utf-8").strip())
            if now - last < interval_minutes * 60:
                logging.info(
                    "Poll atlandı (son çalışma %.0f sn önce, aralık %d dk)",
                    now - last,
                    interval_minutes,
                )
                return False
        except ValueError:
            pass
    return True


def _mark_poll_run() -> None:
    POLL_STATE_FILE.write_text(str(time.time()), encoding="utf-8")


def _process_slot(
    page,
    slot: TargetSlot,
    *,
    dry_run: bool,
    notify_on_book: bool = True,
) -> BookResult:
    lesson = lesson_datetime(slot)
    display = slot_display_name(slot, lesson)
    result = try_book_slot(page, slot, lesson_dt=lesson)

    if result == BookResult.BOOKED and notify_on_book:
        notify_booked(display, dry_run=dry_run)
    elif result == BookResult.LOGIN_FAILED:
        notify_error(display, "Giriş başarısız", dry_run=dry_run)
    elif result == BookResult.ERROR:
        notify_error(display, "Rezervasyon akışı hata verdi", dry_run=dry_run)

    logging.info("[%s] Sonuç: %s", display, result.value)
    return result


def run_burst(
    slots: list[TargetSlot],
    cfg: dict,
    *,
    dry_run: bool,
    headless: bool,
) -> int:
    duration_sec = int(cfg["burst_duration_minutes"]) * 60
    retry_sec = int(cfg["burst_retry_interval_seconds"])
    deadline = time.time() + duration_sec
    completed: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        for slot in slots:
            lesson = lesson_datetime(slot)
            display = slot_display_name(slot, lesson)
            opens = opening_datetime(slot)
            now = datetime.now(TRT)
            notify_burst_start(
                f"{display} (açılış ~{opens.strftime('%d.%m %H:%M')} TRT, şimdi {now.strftime('%H:%M')})",
                dry_run=dry_run,
            )

        while time.time() < deadline:
            for slot in slots:
                if slot.id.value in completed:
                    continue
                if dry_run:
                    logging.info("[dry-run] burst denemesi: %s", slot.label_tr)
                    continue

                result = _process_slot(page, slot, dry_run=dry_run)
                if result in (BookResult.BOOKED, BookResult.ALREADY_BOOKED):
                    completed.add(slot.id.value)

            if len(completed) >= len(slots):
                logging.info("Tüm hedef slotlar tamamlandı, burst erken bitiyor")
                break

            if dry_run:
                break

            remaining = deadline - time.time()
            if remaining <= 0:
                break
            time.sleep(min(retry_sec, remaining))

        browser.close()

    return 0


def run_poll(
    slots: list[TargetSlot],
    cfg: dict,
    *,
    dry_run: bool,
    headless: bool,
    force: bool,
) -> int:
    interval = int(cfg["poll_interval_minutes"])
    if not _should_run_poll(interval, force=force):
        return 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        for slot in slots:
            if dry_run:
                logging.info("[dry-run] poll kontrol: %s", slot.label_tr)
                continue
            _process_slot(page, slot, dry_run=dry_run)

        browser.close()

    if not dry_run:
        _mark_poll_run()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Suadiye Kürek rezervasyon botu")
    p.add_argument(
        "--mode",
        choices=("burst", "poll"),
        required=True,
        help="burst: açılış saldırısı; poll: periyodik kontrol",
    )
    p.add_argument(
        "--slot",
        default="all",
        help="tuesday | thursday | saturday | all",
    )
    p.add_argument("--config", type=Path, default=None, help="config.json yolu")
    p.add_argument("--poll-interval", type=int, default=None)
    p.add_argument("--burst-retry", type=int, default=None)
    p.add_argument("--burst-duration", type=int, default=None)
    p.add_argument("--burst-start-before", type=int, default=None)
    p.add_argument("--dry-run", action="store_true", help="Siteye dokunmadan / bildirim testi")
    p.add_argument("--force-poll", action="store_true", help="Poll aralığını yoksay")
    p.add_argument("--headed", action="store_true", help="Tarayıcı görünür mod")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    _load_env()
    args = build_parser().parse_args(argv)
    _setup_logging(args.verbose)

    cfg = load_config(args.config)
    cfg = apply_cli_overrides(
        cfg,
        poll_interval=args.poll_interval,
        burst_retry=args.burst_retry,
        burst_duration=args.burst_duration,
        burst_start_before=args.burst_start_before,
    )

    try:
        slots = slots_for_run(args.slot)
    except ValueError as e:
        logging.error("%s", e)
        return 2

    headless = not args.headed and os.environ.get("HEADLESS", "1") != "0"

    logging.info("Mod: %s, slotlar: %s, config: %s", args.mode, args.slot, cfg)

    if args.mode == "burst":
        return run_burst(slots, cfg, dry_run=args.dry_run, headless=headless)
    return run_poll(
        slots,
        cfg,
        dry_run=args.dry_run,
        headless=headless,
        force=args.force_poll,
    )


if __name__ == "__main__":
    sys.exit(main())
