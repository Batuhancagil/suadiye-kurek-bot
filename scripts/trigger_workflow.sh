#!/usr/bin/env bash
# Yerel veya dış cron ile workflow tetikleme
# Kullanım: GITHUB_TOKEN=ghp_xxx ./scripts/trigger_workflow.sh schedule-poll.yml
#         GITHUB_TOKEN=ghp_xxx ./scripts/trigger_workflow.sh schedule-burst.yml '{"slot":"tuesday"}'

set -euo pipefail
REPO="Batuhancagil/suadiye-kurek-bot"
WORKFLOW="${1:?workflow dosyası gerekli örn. schedule-poll.yml}"
INPUTS="${2:-}"
TOKEN="${GITHUB_TOKEN:?GITHUB_TOKEN gerekli}"

if [ -n "$INPUTS" ]; then
  BODY="{\"ref\":\"master\",\"inputs\":${INPUTS}}"
else
  BODY='{"ref":"master"}'
fi

curl -fsS -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches" \
  -d "$BODY"

echo "OK: ${WORKFLOW} tetiklendi ($(TZ=Europe/Istanbul date '+%d.%m.%Y %H:%M %Z'))"
