#!/usr/bin/env bash
# Copy the project from your Mac to a Pi and (re)install it.
#   ./scripts/deploy.sh pi@calendar-dev.local
set -euo pipefail
TARGET="${1:?usage: deploy.sh user@host}"
cd "$(dirname "$0")/.."

rsync -az --delete \
  --exclude '.git' --exclude '.venv' --exclude '.dev-data' --exclude 'out' \
  --exclude '__pycache__' --exclude '.pytest_cache' --exclude '.DS_Store' \
  ./ "$TARGET:~/eink-calendar/"

ssh -t "$TARGET" 'sudo ~/eink-calendar/scripts/install.sh'
