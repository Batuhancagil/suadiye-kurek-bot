#!/usr/bin/env bash
# Yerel dry-run: Telegram + burst/poll akışı (siteye burst'ta dokunmaz)
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PY:-./venv/bin/python}"

echo "=== Burst dry-run (tuesday) ==="
"$PY" -m src.main --mode burst --slot tuesday --dry-run -v

echo "=== Poll dry-run (all) ==="
"$PY" -m src.main --mode poll --slot all --dry-run -v

echo "OK — GitHub için: Actions → Burst Rezervasyon → Run workflow"
