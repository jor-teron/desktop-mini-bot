#!/usr/bin/env bash
# desktop-mini-bot — day-to-day runner (local only)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${DMB_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/desktop-mini-bot/config.json}"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

usage() {
  cat <<USAGE
Usage: ./run.sh [options] [--] [goal...]

  ./run.sh                          Interactive: ask for goal
  ./run.sh "click Save"             Mock brain (offline practice)
  ./run.sh --mock "click Save"      Same (explicit)
  ./run.sh --local "click Save"     Real local model via config
  ./run.sh --config PATH --local …  Custom config JSON

Env:
  DMB_CONFIG   default config path ($CONFIG)

Mock = dummy brain (no model). Local = your Ollama/llama.cpp on 127.0.0.1.
USAGE
}

MODE="mock"
GOAL=""
CONFIG_FLAG=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --mock) MODE="mock"; shift ;;
    --local) MODE="local"; shift ;;
    --config)
      [[ $# -ge 2 ]] || { echo "run.sh: --config needs a path" >&2; exit 1; }
      CONFIG="$2"
      CONFIG_FLAG=(--config "$CONFIG")
      shift 2
      ;;
    --) shift; GOAL="$*"; break ;;
    -*)
      echo "run.sh: unknown option: $1" >&2
      usage
      exit 1
      ;;
    *)
      if [[ -z "$GOAL" ]]; then
        GOAL="$1"
      else
        GOAL="$GOAL $1"
      fi
      shift
      ;;
  esac
done

if [[ -z "$GOAL" ]]; then
  read -r -p "What should the bot try to do? " GOAL
  [[ -n "$GOAL" ]] || { echo "run.sh: empty goal" >&2; exit 1; }
fi

ARGS=(--goal "$GOAL" --dry-run)
case "$MODE" in
  mock)
    ARGS+=(--mock-llm)
    ;;
  local)
    if [[ ! -f "$CONFIG" ]]; then
      echo "run.sh: missing config: $CONFIG" >&2
      echo "Run ./install.sh --agent first, or pass --config" >&2
      exit 1
    fi
    ARGS+=(--config "$CONFIG")
    ;;
esac

# If user passed --config with mock, still honor config path only for local;
# mock ignores model server on purpose.
exec python3 -m desktop_mini_bot "${ARGS[@]}"
