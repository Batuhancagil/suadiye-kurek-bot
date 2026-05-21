"""Slot zaman hesabı testleri."""

from datetime import datetime
from zoneinfo import ZoneInfo

from src.slots import (
    SlotId,
    TARGET_SLOTS,
    lesson_datetime,
    opening_datetime,
    parse_slot_arg,
    slots_for_run,
)

TRT = ZoneInfo("Europe/Istanbul")


def test_opening_is_four_days_before_lesson():
    slot = TARGET_SLOTS[SlotId.TUESDAY]
    ref = datetime(2026, 5, 21, 12, 0, tzinfo=TRT)
    lesson = lesson_datetime(slot, ref)
    assert lesson == datetime(2026, 5, 26, 7, 0, tzinfo=TRT)
    assert opening_datetime(slot, ref) == datetime(2026, 5, 22, 7, 0, tzinfo=TRT)


def test_parse_slot_all():
    assert slots_for_run("all") == list(TARGET_SLOTS.values())
    assert len(slots_for_run("tuesday")) == 1


def test_parse_slot_invalid():
    try:
        parse_slot_arg("monday")
        assert False
    except ValueError:
        pass


def test_lesson_datetime_future():
    slot = TARGET_SLOTS[SlotId.SATURDAY]
    lesson = lesson_datetime(slot, datetime(2026, 5, 21, 12, 0, tzinfo=TRT))
    assert lesson.weekday() == 5
    assert lesson.hour == 8
