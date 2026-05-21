"""config.json yükleme ve CLI override."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG: dict[str, Any] = {
    "poll_interval_minutes": 30,
    "burst_start_before_minutes": 5,
    "burst_retry_interval_seconds": 8,
    "burst_duration_minutes": 15,
}


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg = deepcopy(DEFAULT_CONFIG)
    config_path = path or (BASE_DIR / "config.json")
    example_path = BASE_DIR / "config.example.json"

    source = config_path if config_path.is_file() else example_path
    if source.is_file():
        with open(source, encoding="utf-8") as f:
            user_cfg = json.load(f)
        if isinstance(user_cfg, dict):
            cfg.update(user_cfg)
    return cfg


def apply_cli_overrides(
    cfg: dict[str, Any],
    *,
    poll_interval: int | None = None,
    burst_retry: int | None = None,
    burst_duration: int | None = None,
    burst_start_before: int | None = None,
) -> dict[str, Any]:
    out = deepcopy(cfg)
    if poll_interval is not None:
        out["poll_interval_minutes"] = poll_interval
    if burst_retry is not None:
        out["burst_retry_interval_seconds"] = burst_retry
    if burst_duration is not None:
        out["burst_duration_minutes"] = burst_duration
    if burst_start_before is not None:
        out["burst_start_before_minutes"] = burst_start_before
    return out
