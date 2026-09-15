#!/usr/bin/env bash
# desktop-mini-bot — day-to-day runner (local only)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${DMB_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/desktop-mini-bot/config.json}"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
PYTHON="python3"

usage() {
  cat <<USAGE
Usage: ./run.sh [options] [--] [goal...]

  ./run.sh "click Save"                  Fake desk + mock brain (terminal only)
  ./run.sh --browser --mock "click Save" Real Chromium window + mock brain
  ./run.sh --browser --local "click Save" Real browser + your local Ollama model
  ./run.sh --local "click Save"          Fake desk + local model
  ./run.sh --ui                          Tiny local chat page in browser

Options:
  --mock       Dummy brain (default)
  --local      Real local model via config
  --browser    Drive a real browser (DOM, no screenshots)
  --headless   Browser with no visible window
  --url URL    Start URL (default: bundled examples/demo.html)
  --ui         Open tiny local chat page
  --port N     Chat UI port (default 8765)
  --config PATH

Mock = dummy brain. Local = Ollama/llama.cpp on 127.0.0.1.
USAGE
}

MODE="mock"
GOAL=""
BROWSER=0
HEADLESS=0
URL=""
UI=0
PORT=8765

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --mock) MODE="mock"; shift ;;
    --local) MODE="local"; shift ;;
    --browser) BROWSER=1; shift ;;
    --headless) HEADLESS=1; shift ;;
    --ui) UI=1; shift ;;
    --port)
      [[ $# -ge 2 ]] || { echo "run.sh: --port needs a value" >&2; exit 1; }
      PORT="$2"; shift 2 ;;
    --url)
      [[ $# -ge 2 ]] || { echo "run.sh: --url needs a value" >&2; exit 1; }
      URL="$2"; shift 2 ;;
    --config)
      [[ $# -ge 2 ]] || { echo "run.sh: --config needs a path" >&2; exit 1; }
      CONFIG="$2"; shift 2 ;;
    --) shift; GOAL="$*"; break ;;
    -*)
      echo "run.sh: unknown option: $1" >&2
      usage
      exit 1
      ;;
    *)
      if [[ -z "$GOAL" ]]; then GOAL="$1"; else GOAL="$GOAL $1"; fi
      shift
      ;;
  esac
done

if [[ "$UI" -eq 1 ]]; then
  ARGS=(--ui --port "$PORT")
  [[ -f "$CONFIG" ]] && ARGS+=(--config "$CONFIG")
  exec "$PYTHON" -m desktop_mini_bot "${ARGS[@]}"
fi

if [[ -z "$GOAL" ]]; then
  read -r -p "What should the bot try to do? " GOAL
  [[ -n "$GOAL" ]] || { echo "run.sh: empty goal" >&2; exit 1; }
fi

ARGS=(--goal "$GOAL")
if [[ "$BROWSER" -eq 1 ]]; then
  ARGS+=(--browser)
  [[ "$HEADLESS" -eq 1 ]] && ARGS+=(--headless)
  [[ -n "$URL" ]] && ARGS+=(--url "$URL")
else
  ARGS+=(--dry-run)
fi

case "$MODE" in
  mock) ARGS+=(--mock-llm) ;;
  local)
    if [[ ! -f "$CONFIG" ]]; then
      echo "run.sh: missing config: $CONFIG" >&2
      echo "Run ./install.sh --agent first, or pass --config" >&2
      exit 1
    fi
    ARGS+=(--config "$CONFIG")
    ;;
esac

exec "$PYTHON" -m desktop_mini_bot "${ARGS[@]}"
