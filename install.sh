#!/usr/bin/env bash
# desktop-mini-bot — one-paste install/update (no pip)
#   curl -fsSL https://raw.githubusercontent.com/jor-teron/desktop-mini-bot/main/install.sh | bash
set -euo pipefail

REPO_URL="${DMB_REPO:-https://github.com/jor-teron/desktop-mini-bot.git}"
DEST="${DMB_HOME:-$HOME/desktop-mini-bot}"
PREFIX="${PREFIX:-$HOME/.local}"
BIN_DIR="$PREFIX/bin"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/desktop-mini-bot"
CONFIG_FILE="$CONFIG_DIR/config.json"
WITH_BROWSER=1
WITH_MODEL=0
SKIP_APT=0

RED=$'\033[31m'; GRN=$'\033[32m'; YLW=$'\033[33m'; RST=$'\033[0m'
info(){ printf '%s\n' "$*"; }
ok(){ printf '%s✓ %s%s\n' "$GRN" "$*" "$RST"; }
warn(){ printf '%s! %s%s\n' "$YLW" "$*" "$RST"; }
die(){ printf '%s✗ %s%s\n' "$RED" "$*" "$RST" >&2; exit 1; }
have(){ command -v "$1" >/dev/null 2>&1; }

_apt_install() {
  have sudo || die "need sudo to install: $*"
  info "apt install: $*"
  sudo apt-get update -y || die "apt-get update failed"
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "$@" || die "apt install failed: $*"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --update) shift ;;
    --browser) WITH_BROWSER=1; shift ;;
    --no-browser) WITH_BROWSER=0; shift ;;
    --with-model) WITH_MODEL=1; shift ;;
    --skip-apt) SKIP_APT=1; shift ;;
    -h|--help)
      echo "Usage: install.sh [--update] [--browser|--no-browser] [--with-model] [--skip-apt]"
      echo "Pure Python (stdlib). Optional: system Chromium via apt. No pip."
      exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || true)"
if [[ -z "${_SRC}" || ! -f "${_SRC}/src/desktop_mini_bot/__main__.py" ]]; then
  if ! have git; then
    [[ "$SKIP_APT" -eq 0 ]] && _apt_install git || die "git required"
  fi
  if [[ -d "$DEST/.git" ]]; then
    info "Updating $DEST …"
    git -C "$DEST" pull --ff-only || die "git pull failed"
  else
    info "Cloning → $DEST …"
    git clone --depth 1 "$REPO_URL" "$DEST" || die "git clone failed"
  fi
  args=()
  [[ "$WITH_BROWSER" -eq 1 ]] && args+=(--browser) || args+=(--no-browser)
  [[ "$WITH_MODEL" -eq 1 ]] && args+=(--with-model)
  [[ "$SKIP_APT" -eq 1 ]] && args+=(--skip-apt)
  exec bash "$DEST/install.sh" "${args[@]}"
fi
ROOT="$_SRC"

ensure_system() {
  [[ "$SKIP_APT" -eq 1 ]] && return 0
  have apt-get || { warn "no apt — install python3 yourself"; return 0; }
  local need=()
  have git || need+=(git)
  have python3 || need+=(python3)
  if [[ "$WITH_BROWSER" -eq 1 ]]; then
    if ! have chromium && ! have chromium-browser && ! have google-chrome && ! have google-chrome-stable; then
      need+=(chromium)
    fi
  fi
  if [[ ${#need[@]} -gt 0 ]]; then
    _apt_install "${need[@]}"
  fi
  have python3 || die "python3 missing"
  python3 -c 'import sys; raise SystemExit(0 if sys.version_info>=(3,10) else 1)' \
    || die "Need Python >= 3.10"
  ok "System deps OK"
}

install_agent() {
  mkdir -p "$BIN_DIR" "$CONFIG_DIR"
  cat > "$BIN_DIR/desktop-mini-bot" << LAUNCH
#!/usr/bin/env bash
export PYTHONPATH="$ROOT/src\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m desktop_mini_bot "\$@"
LAUNCH
  chmod +x "$BIN_DIR/desktop-mini-bot"
  cat > "$BIN_DIR/desktop-mini-bot-update" << UPD
#!/usr/bin/env bash
exec bash "$ROOT/install.sh" --update "\$@"
UPD
  chmod +x "$BIN_DIR/desktop-mini-bot-update"
  [[ -f "$CONFIG_FILE" ]] || cp "$ROOT/config.example.json" "$CONFIG_FILE"
  if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    warn "Add to PATH:  export PATH=\"$BIN_DIR:\$PATH\""
  fi
  ok "Launcher installed (stdlib only — no pip)"
}

maybe_model() {
  [[ "$WITH_MODEL" -eq 1 ]] || return 0
  if ! have ollama; then
    warn "Ollama not found (optional): curl -fsSL https://ollama.com/install.sh | sh"
    return 0
  fi
  local model="${DMB_MODEL:-hammer2.0:1.5b}"
  ollama pull "$model" || warn "model pull failed"
}

verify() {
  info "Verifying…"
  ( cd "$ROOT" && PYTHONPATH=src python3 -c "import desktop_mini_bot" ) || die "import failed"
  ( cd "$ROOT" && PYTHONPATH=src python3 -m desktop_mini_bot --mock-llm --goal "click Save" >/dev/null ) \
    || die "mock run failed"
  if [[ "$WITH_BROWSER" -eq 1 ]]; then
    if have chromium || have chromium-browser || have google-chrome || have google-chrome-stable; then
      ok "Chromium/Chrome present"
    else
      warn "No Chromium found — browser mode needs: sudo apt install chromium"
    fi
  fi
  ok "Verify passed"
}

ensure_system
[[ -d "$ROOT/.git" ]] && git -C "$ROOT" pull --ff-only || true
install_agent
maybe_model
verify
cat <<S

${GRN}desktop-mini-bot ready${RST}  (pure Python stdlib — no pip)
  $ROOT/run.sh --ui
  desktop-mini-bot --ui
  Update: curl -fsSL https://raw.githubusercontent.com/jor-teron/desktop-mini-bot/main/install.sh | bash

S
