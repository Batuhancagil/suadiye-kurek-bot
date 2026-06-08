#!/usr/bin/env python3
"""Suadiye Kürek botu izleme sağlık kontrolü (Playwright / rezervasyon yok)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent.parent
TRT = ZoneInfo("Europe/Istanbul")

sys.path.insert(0, str(BASE_DIR))

from src.config import load_config  # noqa: E402
from src.notify import send_telegram  # noqa: E402
from src.slots import TARGET_SLOTS, opening_datetime, lesson_datetime  # noqa: E402


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class HealthReport:
    mode: str
    checks: list[CheckResult] = field(default_factory=list)
    extra: str = ""

    @property
    def passed(self) -> bool:
        return all(c.ok for c in self.checks)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append(CheckResult(name, ok, detail))


def _run_pytest() -> CheckResult:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=line"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        tail = "\n".join(out.strip().splitlines()[-5:])
        return CheckResult(
            "pytest",
            proc.returncode == 0,
            tail or f"exit={proc.returncode}",
        )
    except FileNotFoundError:
        return CheckResult("pytest", False, "pytest modülü bulunamadı")
    except subprocess.TimeoutExpired:
        return CheckResult("pytest", False, "zaman aşımı (120s)")


def _check_imports() -> CheckResult:
    modules = ("src.config", "src.slots", "src.notify", "src.booker", "src.main")
    failed: list[str] = []
    for mod in modules:
        try:
            __import__(mod)
        except Exception as exc:
            failed.append(f"{mod}: {exc}")
    if failed:
        return CheckResult("imports", False, "; ".join(failed))
    return CheckResult("imports", True, f"{len(modules)} modül OK")


def _check_config() -> CheckResult:
    try:
        cfg = load_config()
        required = (
            "poll_interval_minutes",
            "burst_start_before_minutes",
            "burst_retry_interval_seconds",
            "burst_duration_minutes",
        )
        missing = [k for k in required if k not in cfg]
        if missing:
            return CheckResult("config", False, f"eksik alan: {', '.join(missing)}")
        return CheckResult("config", True, json.dumps(cfg, ensure_ascii=False))
    except Exception as exc:
        return CheckResult("config", False, str(exc))


def _check_workflows() -> CheckResult:
    expected = (
        ".github/workflows/schedule-poll.yml",
        ".github/workflows/schedule-burst.yml",
        ".github/workflows/production.yml",
    )
    missing = [p for p in expected if not (BASE_DIR / p).is_file()]
    if missing:
        return CheckResult("workflows", False, f"eksik: {', '.join(missing)}")
    return CheckResult("workflows", True, f"{len(expected)} workflow dosyası mevcut")


def _check_slots_logic() -> CheckResult:
    try:
        now = datetime.now(TRT)
        for slot in TARGET_SLOTS.values():
            lesson = lesson_datetime(slot, now)
            opening = opening_datetime(slot, now, lesson_dt=lesson)
            delta_days = (lesson.date() - opening.date()).days
            if delta_days != 4:
                return CheckResult(
                    "slots",
                    False,
                    f"{slot.id.value}: açılış-ders farkı {delta_days} gün (beklenen 4)",
                )
        return CheckResult("slots", True, f"{len(TARGET_SLOTS)} slot zamanı OK")
    except Exception as exc:
        return CheckResult("slots", False, str(exc))


def _check_telegram_env() -> CheckResult:
    import os

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip() or os.environ.get(
        "TELEGRAM_CHAT_IDS", ""
    ).strip()
    if not token:
        return CheckResult("telegram_env", False, "TELEGRAM_BOT_TOKEN yok")
    if not chat:
        return CheckResult("telegram_env", False, "TELEGRAM_CHAT_ID yok")
    return CheckResult("telegram_env", True, "token + chat_id mevcut")


def _check_required_files() -> CheckResult:
    required = (
        "requirements.txt",
        "config.example.json",
        "src/main.py",
        "src/booker.py",
        "README.md",
    )
    missing = [p for p in required if not (BASE_DIR / p).is_file()]
    if missing:
        return CheckResult("files", False, f"eksik: {', '.join(missing)}")
    return CheckResult("files", True, f"{len(required)} temel dosya mevcut")


def run_checks(mode: str) -> HealthReport:
    report = HealthReport(mode=mode)
    report.add(*_check_required_files())
    report.add(*_check_config())
    report.add(*_check_imports())

    if mode in ("weekly", "deploy"):
        report.add(*_check_workflows())
        report.add(*_check_slots_logic())
        report.add(*_run_pytest())

    if mode == "smoke":
        report.add(*_run_pytest())

    report.add(*_check_telegram_env())
    return report


def format_telegram_message(report: HealthReport) -> str:
    now = datetime.now(TRT).strftime("%Y-%m-%d %H:%M TRT")
    status = "OK" if report.passed else "FAIL"
    mode_labels = {
        "weekly": "Haftalık sağlık",
        "deploy": "Deploy kontrol",
        "smoke": "Smoke / hata",
    }
    title = mode_labels.get(report.mode, report.mode)
    lines = [f"[İZLEME] {title} — {status}", f"Zaman: {now}"]

    if report.extra:
        lines.append(f"Ek: {report.extra[:500]}")

    for c in report.checks:
        icon = "✓" if c.ok else "✗"
        line = f"{icon} {c.name}"
        if c.detail and not c.ok:
            line += f": {c.detail[:200]}"
        lines.append(line)

    failed = [c for c in report.checks if not c.ok]
    if failed:
        lines.append(f"Başarısız: {len(failed)}/{len(report.checks)}")
    else:
        lines.append(f"Tüm kontroller geçti ({len(report.checks)})")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Suadiye bot izleme sağlık kontrolü")
    parser.add_argument(
        "--mode",
        choices=("weekly", "deploy", "smoke"),
        default="weekly",
        help="Kontrol modu",
    )
    parser.add_argument("--extra", default="", help="Ek bağlam (webhook/hata özeti)")
    parser.add_argument("--no-telegram", action="store_true", help="Telegram gönderme")
    args = parser.parse_args()

    report = run_checks(args.mode)
    report.extra = args.extra.strip()

    msg = format_telegram_message(report)
    print(msg)

    telegram_ok = False
    if not args.no_telegram:
        telegram_ok = send_telegram(msg)
        print(f"\nTelegram: {'gönderildi' if telegram_ok else 'gönderilemedi'}")

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
