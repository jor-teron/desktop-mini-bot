#!/usr/bin/env bash
# desktop-mini-bot — one-line install/update (Ollama-style)
#   curl -fsSL https://raw.githubusercontent.com/jor-teron/desktop-mini-bot/main/install.sh | bash
#   curl -fsSL .../install.sh | bash -s -- --browser
#   curl -fsSL .../install.sh | bash -s -- --update
set -euo pipefail

REPO_URL="${DMB_REPO:-https://github.com/jor-teron/desktop-mini-bot.git}"
DEST="${DMB_HOME:-$HOME/desktop-mini-bot}"
PREFIX="${PREFIX:-$HOME/.local}"
BIN_DIR="$PREFIX/bin"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/desktop-mini-bot"
CONFIG_FILE="$CONFIG_DIR/config.json"

RED=$'\033[31m'; GRN=$'\033[32m'; YLW=$'\033[33m'; RST=$'\033[0m'
info(){ printf '%s\n' "$*"; }
ok(){ printf '%s%s%s\n' "$GRN" "$*" "$RST"; }
warn(){ printf '%s%s%s\n' "$YLW" "$*" "$RST"; }
die(){ printf '%s%s%s\n' "$RED" "$*" "$RST" >&2; exit 1; }

# If this script is not inside a checkout (e.g. curl | bash), clone/update then re-exec.
_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || true)"
if [[ -z "${_SRC}" || ! -f "${_SRC}/src/desktop_mini_bot/__main__.py" ]]; then
  command -v git >/dev/null 2>&1 || die "git required (sudo apt install git)"
  if [[ -d "$DEST/.git" ]]; then
    info "Updating $DEST …"
    git -C "$DEST" pull --ff-only || die "git pull failed"
  else
    info "Installing into $DEST …"
    git clone --depth 1 "$REPO_URL" "$DEST" || die "git clone failed"
  fi
  exec bash "$DEST/install.sh" "$@"
fi
ROOT="$_SRC"

need_python() {
  command -v python3 >/dev/null 2>&1 || die "python3 not found (sudo apt install python3)"
  python3 -c 'import sys; raise SystemExit(0 if sys.version_info>=(3,10) else 1)' \
    || die "Need Python >= 3.10"
  ok "Python $(python3 -c 'import sys; print("%d.%d"%sys.version_info[:2])') OK"
}

install_agent() {
  info "Installing launcher…"
  need_python
  mkdir -p "$BIN_DIR" "$CONFIG_DIR"
  cat > "$BIN_DIR/desktop-mini-bot" << LAUNCH
#!/usr/bin/env bash
ROOT="$ROOT"
if [[ -x "\$ROOT/.venv/bin/python" ]]; then
  export PYTHONPATH="\$ROOT/src\${PYTHONPATH:+:\$PYTHONPATH}"
  exec "\$ROOT/.venv/bin/python" -m desktop_mini_bot "\$@"
fi
export PYTHONPATH="\$ROOT/src\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m desktop_mini_bot "\$@"
LAUNCH
  chmod +x "$BIN_DIR/desktop-mini-bot"
  # Convenience: update/reinstall in one command
  cat > "$BIN_DIR/desktop-mini-bot-update" << UPD
#!/usr/bin/env bash
exec bash "$ROOT/install.sh" --update "\$@"
UPD
  chmod +x "$BIN_DIR/desktop-mini-bot-update"

  if [[ ! -f "$CONFIG_FILE" ]]; then
    cp "$ROOT/config.example.json" "$CONFIG_FILE"
    ok "Wrote $CONFIG_FILE"
  else
    warn "Keeping existing $CONFIG_FILE"
  fi
  if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    warn "Add to PATH:  export PATH=\"$BIN_DIR:\$PATH\""
  fi
  ok "Agent installed at $ROOT"
  info "Chat UI:  desktop-mini-bot --ui"
  info "Or:       $ROOT/run.sh --ui"
}

do_update() {
  info "Updating from git…"
  if [[ -d "$ROOT/.git" ]]; then
    git -C "$ROOT" pull --ff-only || die "git pull failed"
  else
    warn "Not a git checkout; skip pull"
  fi
  install_agent
  # Refresh browser deps if venv already exists
  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    info "Refreshing Playwright…"
    install_browser
  else
    ok "Update done (agent). For browser: re-run with --browser"
  fi
}

install_ollama_hint() {
  info "Local model runtime (Ollama)…"
  if ! command -v ollama >/dev/null 2>&1; then
    warn "Ollama not installed. One-time: curl -fsSL https://ollama.com/install.sh | sh"
    return 0
  fi
  ok "Ollama: $(command -v ollama)"
  local model="${DMB_MODEL:-hammer2.0:1.5b}"
  info "Pulling '$model'…"
  if ollama pull "$model"; then
    ok "Model ready: $model"
  else
    warn "Pull failed — set model in $CONFIG_FILE"
  fi
  if [[ -f "$CONFIG_FILE" ]]; then
    python3 - "$CONFIG_FILE" "$model" <<'PY'
import json,sys
p,m=sys.argv[1],sys.argv[2]
c=json.load(open(p,encoding="utf-8"))
c.update({"base_url":"http://127.0.0.1:11434/v1","api_key":"ollama","model":m})
json.dump(c, open(p,"w",encoding="utf-8"), indent=2); open(p,"a",encoding="utf-8").write("\n")
print("updated",p)
PY
  fi
}

install_browser() {
  info "Installing Playwright…"
  need_python
  local venv="$ROOT/.venv"
  if [[ ! -x "$venv/bin/python" ]]; then
    rm -rf "$venv"
    python3 -m venv "$venv" || die "venv failed (sudo apt install python3-venv python3-full)"
  fi
  [[ -x "$venv/bin/python" ]] || die "no $venv/bin/python"
  "$venv/bin/python" -m pip install -U pip >/dev/null
  "$venv/bin/python" -m pip install -U "playwright>=1.40" || die "pip playwright failed"
  "$venv/bin/python" -m playwright install chromium || die "chromium install failed"
  ok "Playwright ready"
  install_agent
  info "Try:  $ROOT/run.sh --browser --mock \"click Save\""
}

smoke_test() {
  need_python
  local py=python3
  [[ -x "$ROOT/.venv/bin/python" ]] && py="$ROOT/.venv/bin/python"
  ( cd "$ROOT" && PYTHONPATH=src "$py" -m unittest discover -s tests -q )
  ok "Tests passed"
  ( cd "$ROOT" && PYTHONPATH=src "$py" -m desktop_mini_bot --mock-llm --goal "click Save" )
}

usage() {
  cat <<USAGE
desktop-mini-bot installer

One-line (install or update):
  curl -fsSL https://raw.githubusercontent.com/jor-teron/desktop-mini-bot/main/install.sh | bash

With browser hands:
  curl -fsSL https://raw.githubusercontent.com/jor-teron/desktop-mini-bot/main/install.sh | bash -s -- --browser

From a checkout:
  ./install.sh              menu
  ./install.sh --agent      launcher only
  ./install.sh --browser    agent + Playwright
  ./install.sh --with-model agent + Ollama model helper
  ./install.sh --update     git pull + refresh install
  ./install.sh --test

Env: DMB_HOME=$DEST  DMB_REPO=...  DMB_MODEL=...  PREFIX=$PREFIX
USAGE
}

menu() {
  cat <<MENU

desktop-mini-bot
  1) Agent only
  2) Agent + browser
  3) Agent + local model
  4) Update (git pull + refresh)
  5) Tests
  6) Quit

MENU
  local c; read -r -p "Choose [1-6]: " c
  case "$c" in
    1) install_agent ;;
    2) install_agent; install_browser ;;
    3) install_agent; install_ollama_hint ;;
    4) do_update ;;
    5) smoke_test ;;
    6) exit 0 ;;
    *) die "Invalid choice" ;;
  esac
}

main() {
  case "${1:-}" in
    "") menu ;;
    --agent) install_agent ;;
    --browser) install_agent; install_browser ;;
    --with-model) install_agent; install_ollama_hint ;;
    --update) do_update ;;
    --test) smoke_test ;;
    -h|--help) usage ;;
    *) usage; die "Unknown option: $1" ;;
  esac
}

main "$@"
