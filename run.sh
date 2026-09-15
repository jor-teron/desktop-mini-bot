#!/usr/bin/env bash
# desktop-mini-bot — day-to-day runner (local only)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${DMB_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/desktop-mini-bot/config.json}"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
PYTHON="python3"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi

usage() {
  cat <<USAGE
Usage: ./run.sh [options] [--] [goal...]

  ./run.sh "click Save"                  Fake desk + mock brain (terminal only)
  ./run.sh --browser --mock "click Save" Real Chromium window + mock brain
  ./run.sh --browser --local "click Save" Real browser + your local Ollama model
  ./run.sh --local "click Save"          Fake desk + local model

Options:
  --mock       Dummy brain (default)
  --local      Real local model via config
  --browser    Drive a real browser (DOM, no screenshots)
  --headless   Browser with no visible window
  --url URL    Start URL (default: bundled examples/demo.html)
  --config PATH

Mock = dummy brain. Local = Ollama/llama.cpp on 127.0.0.1.
USAGE
}

MODE="mock"
GOAL=""
BROWSER=0
HEADLESS=0
URL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --mock) MODE="mock"; shift ;;
    --local) MODE="local"; shift ;;
    --browser) BROWSER=1; shift ;;
    --headless) HEADLESS=1; shift ;;
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
