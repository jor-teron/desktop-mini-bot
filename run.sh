#!/usr/bin/env bash
# desktop-mini-bot v0.2.3 — convenience launcher for CLI / chat UI.
# Sets PYTHONPATH=app and forwards flags to python -m desktop_mini_bot.
# MIT / jor-teron.
set -euo pipefail

# --- paths / env ---
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Override with DMB_CONFIG=/path/to/config.txt if needed
CONFIG="${DMB_CONFIG:-$ROOT/config.txt}"
export PYTHONPATH="$ROOT/app${PYTHONPATH:+:$PYTHONPATH}"
PYTHON=python3

usage(){ cat <<USAGE
./run.sh --ui
./run.sh --browser "open google.com"
./run.sh --browser --provider ollama --model hammer2.0:1.5b "open https://www.google.com"
Config: $CONFIG  (api_key= for Gemini)
USAGE
}

# --- flag parse ---
GOAL=""; HEADLESS=0; URL=""; UI=0; PORT=8765; MODEL=""; PROVIDER=""; API_KEY=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    # Removed in v0.2 — real browser only
    --mock|--local|--dry-run) echo "note: mock/dry-run removed in v0.2 — real browser only" >&2; shift ;;
    --browser) shift ;;  # accepted for clarity; goals always use browser
    --headless) HEADLESS=1; shift ;;
    --ui) UI=1; shift ;;
    --port) PORT="$2"; shift 2 ;;
    --url) URL="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --provider) PROVIDER="$2"; shift 2 ;;
    --api-key) API_KEY="$2"; shift 2 ;;
    --config) CONFIG="$2"; shift 2 ;;
    --) shift; GOAL="$*"; break ;;
    -*) echo "unknown: $1" >&2; exit 1 ;;
    *) [[ -z "$GOAL" ]] && GOAL="$1" || GOAL="$GOAL $1"; shift ;;
  esac
done

# Seed config.txt from example on first run
[[ -f "$CONFIG" ]] || cp "$ROOT/config.example.txt" "$CONFIG"

# --- dispatch ---
if [[ "$UI" -eq 1 ]]; then
  exec "$PYTHON" -m desktop_mini_bot --ui --port "$PORT" --config "$CONFIG"
fi
if [[ -z "$GOAL" ]]; then
  read -r -p "Goal? " GOAL
  [[ -n "$GOAL" ]] || exit 1
fi
ARGS=(--goal "$GOAL" --config "$CONFIG" --browser)
[[ "$HEADLESS" -eq 1 ]] && ARGS+=(--headless)
[[ -n "$URL" ]] && ARGS+=(--url "$URL")
[[ -n "$MODEL" ]] && ARGS+=(--model "$MODEL")
[[ -n "$PROVIDER" ]] && ARGS+=(--provider "$PROVIDER")
[[ -n "$API_KEY" ]] && ARGS+=(--api-key "$API_KEY")
exec "$PYTHON" -m desktop_mini_bot "${ARGS[@]}"
