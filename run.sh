#!/usr/bin/env bash
# All paths are inside this project directory.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${DMB_CONFIG:-$ROOT/config.json}"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
PYTHON=python3

usage() {
  cat <<USAGE
Usage: ./run.sh [options] [goal...]

  ./run.sh --ui
  ./run.sh --browser --mock "open google.com"
  ./run.sh --browser --local "open https://www.google.com"
  ./run.sh --browser --mock "click Save"          # demo page

Options: --mock --local --browser --headless --url URL --model NAME --ui --port N --config PATH
Config file: $CONFIG
USAGE
}

MODE=mock; GOAL=""; BROWSER=0; HEADLESS=0; URL=""; UI=0; PORT=8765; MODEL=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --mock) MODE=mock; shift ;;
    --local) MODE=local; shift ;;
    --browser) BROWSER=1; shift ;;
    --headless) HEADLESS=1; shift ;;
    --ui) UI=1; shift ;;
    --port) PORT="$2"; shift 2 ;;
    --url) URL="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --config) CONFIG="$2"; shift 2 ;;
    --) shift; GOAL="$*"; break ;;
    -*) echo "unknown: $1" >&2; usage; exit 1 ;;
    *) [[ -z "$GOAL" ]] && GOAL="$1" || GOAL="$GOAL $1"; shift ;;
  esac
done

if [[ "$UI" -eq 1 ]]; then
  [[ -f "$CONFIG" ]] || cp "$ROOT/config.example.json" "$CONFIG"
  exec "$PYTHON" -m desktop_mini_bot --ui --port "$PORT" --config "$CONFIG"
fi

if [[ -z "$GOAL" ]]; then
  read -r -p "Goal? " GOAL
  [[ -n "$GOAL" ]] || { echo "empty goal" >&2; exit 1; }
fi

ARGS=(--goal "$GOAL" --config "$CONFIG")
[[ "$BROWSER" -eq 1 ]] && ARGS+=(--browser) || ARGS+=(--dry-run)
[[ "$HEADLESS" -eq 1 ]] && ARGS+=(--headless)
[[ -n "$URL" ]] && ARGS+=(--url "$URL")
[[ -n "$MODEL" ]] && ARGS+=(--model "$MODEL")
[[ "$MODE" == mock ]] && ARGS+=(--mock-llm)
[[ -f "$CONFIG" ]] || cp "$ROOT/config.example.json" "$CONFIG"
exec "$PYTHON" -m desktop_mini_bot "${ARGS[@]}"
