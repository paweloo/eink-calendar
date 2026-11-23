#!/usr/bin/env bash
# Render every panel screen in every theme into the product site (site/public/screens).
# Run after changing anything in inkcal/render so the website shows what the device really draws.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[ -x "$PY" ] || PY=python3
"$PY" -m inkcal preview --out site/public/screens --themes classic,mono,bold,dark
