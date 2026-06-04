#!/usr/bin/env python3
"""
Cursor izleme otomasyonu — SuperSaaS rezervasyonu veya Playwright girişi YAPMAZ.

Modlar:
  weekly  — haftalık sağlık (pytest + statik kontroller)
  deploy  — deploy sonrası (weekly ile aynı testler, farklı Telegram başlığı)
  smoke   — hızlı kontrol (pytest + isteğe bağlı --extra özet)
"""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DEFAULT_CONFIG, load_config  # noqa: E402
from src.notify import send_telegram  # noqa: E402
from src.slots import TARGET_SLOTS, SlotId, opening_datetime, lesson_datetime  # noqa: E402

EXPECTED_BURST_CRONS = {
    "55 3 * * 5",
    "55 3 * * 0",
    "55 4 * * 2",
}


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class HealthReport:
    mode: str
    results: list[CheckResult] = field(default_factory=list)
    telegram_sent: bool = False
    extra: str = ""

    @property
    def passed(self) -> bool:
        return all(r.ok for r in self.results)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.results.append(CheckResult(name=name, ok=ok, detail=detail))


def _check_telegram_env(report: HealthReport) -> None:
    import os

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip() or os.environ.get(
        "TELEGRAM_CHAT_IDS", ""
    ).strip()
    ok = bool(token and chat)
    detail = "yapılandırıldı" if ok else "TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_ID eksik"
    report.add("telegram_env", ok, detail)


def _check_config_load(report: HealthReport) -> None:
    try:
        cfg = load_config(ROOT / "config.example.json")
        for key in DEFAULT_CONFIG:
            if key not in cfg:
                report.add("config_load", False, f"eksik anahtar: {key}")
                return
        report.add("config_load", True, "config.example.json OK")
    except (OSError, json.JSONDecodeError) as e:
        report.add("config_load", False, str(e))


def _check_slot_opening_window(report: HealthReport) -> None:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    trt = ZoneInfo("Europe/Istanbul")
    ref = datetime(2026, 5, 21, 12, 0, tzinfo=trt)
    try:
        for sid in SlotId:
            slot = TARGET_SLOTS[sid]
            lesson = lesson_datetime(slot, ref)
            opening = opening_datetime(slot, ref)
            delta_days = (lesson.date() - opening.date()).days
            if delta_days != 4:
                report.add(
                    "slot_opening_window",
                    False,
                    f"{sid.value}: açılış {delta_days} gün önce (beklenen 4)",
                )
                return
        report.add("slot_opening_window", True, "3 slot, 4 gün kuralı")
    except Exception as e:
        report.add("slot_opening_window", False, str(e))


def _check_imports(report: HealthReport) -> None:
    modules = ("src.slots", "src.notify", "src.config", "src.booker", "src.main")
    failed = []
    for mod in modules:
        try:
            importlib.import_module(mod)
        except Exception as e:
            failed.append(f"{mod}: {e}")
    if failed:
        report.add("imports", False, "; ".join(failed))
    else:
        report.add("imports", True, f"{len(modules)} modül")


def _check_workflow_crons(report: HealthReport) -> None:
    wf = ROOT / ".github" / "workflows" / "schedule-burst.yml"
    if not wf.is_file():
        report.add("workflow_crons", False, "schedule-burst.yml yok")
        return
    text = wf.read_text(encoding="utf-8")
    missing = [c for c in EXPECTED_BURST_CRONS if c not in text]
    if missing:
        report.add("workflow_crons", False, f"eksik cron: {missing}")
    else:
        report.add("workflow_crons", True, "burst UTC cronları mevcut")


def _run_pytest(report: HealthReport) -> None:
    tests_dir = ROOT / "tests"
    if not tests_dir.is_dir():
        report.add("pytest", False, "tests/ dizini yok")
        return
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(tests_dir),
        "-q",
        "--tb=line",
    ]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    summary = out.strip().splitlines()[-1] if out.strip() else f"exit {proc.returncode}"
    report.add("pytest", proc.returncode == 0, summary[:500])


def _format_telegram_message(report: HealthReport) -> str:
    mode_labels = {
        "weekly": "Haftalık sağlık",
        "deploy": "Deploy sağlık",
        "smoke": "Smoke / hata inceleme",
    }
    title = mode_labels.get(report.mode, report.mode)
    status = "OK" if report.passed else "FAIL"
    lines = [f"<b>[İZLEME] {title}</b>", f"Durum: <b>{status}</b>", ""]
    for r in report.results:
        icon = "✓" if r.ok else "✗"
        line = f"{icon} {r.name}"
        if r.detail:
            line += f" — {r.detail}"
        lines.append(line)
    if report.extra:
        lines.extend(["", "<b>Ek:</b>", report.extra[:1500]])
    if not report.passed:
        lines.append("")
        lines.append(
            "Not: Otomasyon SuperSaaS rezervasyonu veya Playwright girişi yapmaz."
        )
    return "\n".join(lines)


def run_checks(mode: str, extra: str = "") -> HealthReport:
    report = HealthReport(mode=mode, extra=extra)
    _check_telegram_env(report)
    _check_imports(report)
    _check_config_load(report)
    _check_slot_opening_window(report)
    if mode in ("weekly", "deploy"):
        _check_workflow_crons(report)
    _run_pytest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Suadiye bot izleme sağlık kontrolü")
    parser.add_argument(
        "--mode",
        choices=("weekly", "deploy", "smoke"),
        required=True,
        help="weekly | deploy | smoke",
    )
    parser.add_argument(
        "--extra",
        default="",
        help="Webhook/hata özeti (smoke modunda)",
    )
    parser.add_argument(
        "--skip-telegram",
        action="store_true",
        help="Telegram gönderme (yerel test)",
    )
    args = parser.parse_args()

    report = run_checks(args.mode, extra=args.extra.strip())

    print(f"Mod: {report.mode}")
    for r in report.results:
        mark = "PASS" if r.ok else "FAIL"
        print(f"  [{mark}] {r.name}: {r.detail}")

    if args.skip_telegram:
        report.telegram_sent = False
        print("Telegram: atlandı (--skip-telegram)")
    else:
        msg = _format_telegram_message(report)
        report.telegram_sent = send_telegram(msg)
        print(f"Telegram: {'gönderildi' if report.telegram_sent else 'gönderilemedi'}")

    print(f"Özet: {'BAŞARILI' if report.passed else 'BAŞARISIZ'}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
