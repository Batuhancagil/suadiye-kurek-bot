"""Hedef ders slotları ve açılış/ders zamanı hesapları (TRT)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from zoneinfo import ZoneInfo

TRT = ZoneInfo("Europe/Istanbul")
BOOKING_WINDOW = timedelta(days=4)

SCHEDULE_URL = (
    "https://www.supersaas.com.tr/schedule/Suadiye_Kurek_Kulubu/DERS_TAKVIMI"
)


class SlotId(str, Enum):
    TUESDAY = "tuesday"
    THURSDAY = "thursday"
    SATURDAY = "saturday"


# SuperSaaS haftalık takvim başlık kısaltmaları (site büyük harf kullanıyor)
HEADER_WEEKDAY: dict[str, str] = {
    "Pazartesi": "PZT",
    "Salı": "SAL",
    "Çarşamba": "ÇRŞ",
    "Perşembe": "PRŞ",
    "Cuma": "CUM",
    "Cumartesi": "CMT",
    "Pazar": "PAZ",
}
WEEKDAY_HEADER_INDEX = ("PZT", "SAL", "ÇRŞ", "PRŞ", "CUM", "CMT", "PAZ")
WEEKDAY_NAMES_TR = (
    "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar",
)


@dataclass(frozen=True)
class TargetSlot:
    id: SlotId
    weekday: int  # 0=Mon .. 6=Sun (datetime.weekday())
    start_hour: int
    start_minute: int
    end_hour: int
    end_minute: int
    label_tr: str

    @property
    def header_weekday(self) -> str:
        if self.label_tr in HEADER_WEEKDAY:
            return HEADER_WEEKDAY[self.label_tr]
        if 0 <= self.weekday < len(WEEKDAY_HEADER_INDEX):
            return WEEKDAY_HEADER_INDEX[self.weekday]
        return self.label_tr[:3].upper()

    @property
    def time_label(self) -> str:
        return (
            f"{self.start_hour:02d}:{self.start_minute:02d}"
            f"-{self.end_hour:02d}:{self.end_minute:02d}"
        )


TARGET_SLOTS: dict[SlotId, TargetSlot] = {
    SlotId.TUESDAY: TargetSlot(
        id=SlotId.TUESDAY,
        weekday=1,
        start_hour=7,
        start_minute=0,
        end_hour=8,
        end_minute=0,
        label_tr="Salı",
    ),
    SlotId.THURSDAY: TargetSlot(
        id=SlotId.THURSDAY,
        weekday=3,
        start_hour=7,
        start_minute=0,
        end_hour=8,
        end_minute=0,
        label_tr="Perşembe",
    ),
    SlotId.SATURDAY: TargetSlot(
        id=SlotId.SATURDAY,
        weekday=5,
        start_hour=8,
        start_minute=0,
        end_hour=9,
        end_minute=0,
        label_tr="Cumartesi",
    ),
}


def _next_weekday_on_or_after(dt: datetime, weekday: int) -> datetime:
    """dt gününde veya sonrasında ilk `weekday` gününün tarihini döndürür."""
    days_ahead = (weekday - dt.weekday()) % 7
    return (dt + timedelta(days=days_ahead)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def lesson_datetime(slot: TargetSlot, on_or_after: datetime | None = None) -> datetime:
    """Slot için bir sonraki (veya aynı gün) ders başlangıç zamanı TRT."""
    now = on_or_after or datetime.now(TRT)
    if now.tzinfo is None:
        now = now.replace(tzinfo=TRT)
    else:
        now = now.astimezone(TRT)

    base = _next_weekday_on_or_after(now, slot.weekday)
    lesson = base.replace(
        hour=slot.start_hour,
        minute=slot.start_minute,
        second=0,
        microsecond=0,
    )
    if lesson < now:
        lesson += timedelta(days=7)
    return lesson


def opening_datetime(
    slot: TargetSlot,
    on_or_after: datetime | None = None,
    *,
    lesson_dt: datetime | None = None,
) -> datetime:
    """Rezervasyonun açıldığı an: ders başlangıcından tam 4 gün önce."""
    lesson = lesson_dt or lesson_datetime(slot, on_or_after)
    return lesson.astimezone(TRT) - BOOKING_WINDOW


def parse_slot_arg(value: str) -> SlotId | None:
    v = value.strip().lower()
    if v in ("all", "*"):
        return None
    try:
        return SlotId(v)
    except ValueError:
        raise ValueError(
            f"Geçersiz slot: {value!r}. "
            f"Seçenekler: {', '.join(s.value for s in SlotId)} veya all"
        ) from None


def slots_for_run(slot_arg: str | None) -> list[TargetSlot]:
    if slot_arg is None or slot_arg.lower() in ("all", "*"):
        return list(TARGET_SLOTS.values())
    sid = parse_slot_arg(slot_arg)
    assert sid is not None
    return [TARGET_SLOTS[sid]]


def slot_for_datetime(
    lesson_dt: datetime,
    *,
    end_hour: int | None = None,
    end_minute: int = 0,
) -> TargetSlot:
    """Belirli bir ders zamanı için geçici slot tanımı (test / tek seferlik)."""
    d = lesson_dt.astimezone(TRT)
    wd = d.weekday()
    eh = end_hour if end_hour is not None else d.hour + 1
    return TargetSlot(
        id=SlotId.TUESDAY,
        weekday=wd,
        start_hour=d.hour,
        start_minute=d.minute,
        end_hour=eh,
        end_minute=end_minute,
        label_tr=WEEKDAY_NAMES_TR[wd],
    )


def format_lesson_date(dt: datetime) -> str:
    months = (
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
    )
    d = dt.astimezone(TRT)
    return f"{d.day} {months[d.month - 1]} {d.year}"


def slot_display_name(slot: TargetSlot, lesson_dt: datetime | None = None) -> str:
    lesson = lesson_dt or lesson_datetime(slot)
    return f"{slot.label_tr} {slot.time_label} ({format_lesson_date(lesson)})"
