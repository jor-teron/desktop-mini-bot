#!/usr/bin/env bash
# desktop-mini-bot — one-paste install / update
#   curl -fsSL https://raw.githubusercontent.com/jor-teron/desktop-mini-bot/main/install.sh | bash
#   curl -fsSL .../install.sh | bash -s -- --update
set -euo pipefail

REPO_URL="${DMB_REPO:-https://github.com/jor-teron/desktop-mini-bot.git}"
DEST="${DMB_HOME:-$HOME/desktop-mini-bot}"
PREFIX="${PREFIX:-$HOME/.local}"
BIN_DIR="$PREFIX/bin"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/desktop-mini-bot"
CONFIG_FILE="$CONFIG_DIR/config.json"
WITH_BROWSER=1
WITH_MODEL=0
DO_UPDATE=0
SKIP_APT=0

RED=$'\033[31m'; GRN=$'\033[32m'; YLW=$'\033[33m'; RST=$'\033[0m'
info(){ printf '%s\n' "$*"; }
ok(){ printf '%s✓ %s%s\n' "$GRN" "$*" "$RST"; }
warn(){ printf '%s! %s%s\n' "$YLW" "$*" "$RST"; }
die(){ printf '%s✗ %s%s\n' "$RED" "$*" "$RST" >&2; exit 1; }

have(){ command -v "$1" >/dev/null 2>&1; }

# --- args (before bootstrap so curl|bash -s -- flags work) ---
parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --update) DO_UPDATE=1; shift ;;
      --browser) WITH_BROWSER=1; shift ;;
      --no-browser) WITH_BROWSER=0; shift ;;
      --with-model) WITH_MODEL=1; shift ;;
      --skip-apt) SKIP_APT=1; shift ;;
      -h|--help)
        cat <<H
Usage: install.sh [--update] [--browser|--no-browser] [--with-model] [--skip-apt]

Default (one-paste): install/update app + system deps + Playwright browser hands.
H
        exit 0 ;;
      *) die "Unknown option: $1 (try --help)" ;;
    esac
  done
}
parse_args "$@"

# --- bootstrap when piped / not in a checkout ---
_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || true)"
if [[ -z "${_SRC}" || ! -f "${_SRC}/src/desktop_mini_bot/__main__.py" ]]; then
  have git || { [[ "$SKIP_APT" -eq 0 ]] && _apt_install git || die "git required"; }
  have git || die "git required (sudo apt install git)"
  if [[ -d "$DEST/.git" ]]; then
    info "Updating $DEST …"
    git -C "$DEST" pull --ff-only || die "git pull failed — fix local changes or: rm -rf $DEST"
  else
    info "Cloning $REPO_URL → $DEST …"
    mkdir -p "$(dirname "$DEST")"
    git clone --depth 1 "$REPO_URL" "$DEST" || die "git clone failed"
  fi
  [[ -f "$DEST/install.sh" ]] || die "clone missing install.sh"
  # Re-exec with same flags
  args=()
  [[ "$DO_UPDATE" -eq 1 ]] && args+=(--update)
  [[ "$WITH_BROWSER" -eq 1 ]] && args+=(--browser) || args+=(--no-browser)
  [[ "$WITH_MODEL" -eq 1 ]] && args+=(--with-model)
  [[ "$SKIP_APT" -eq 1 ]] && args+=(--skip-apt)
  exec bash "$DEST/install.sh" "${args[@]}"
fi
ROOT="$_SRC"

_apt_install() {
  local pkgs=("$@")
  have sudo || die "need sudo to install: ${pkgs[*]}"
  info "Installing packages: ${pkgs[*]}"
  sudo apt-get update -y || die "apt-get update failed"
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${pkgs[@]}" \
    || die "apt-get install failed: ${pkgs[*]}"
}

ensure_system_deps() {
  [[ "$SKIP_APT" -eq 1 ]] && { warn "Skipping apt (--skip-apt)"; return 0; }
  # Only auto-apt on Debian/Ubuntu-like systems
  if [[ ! -f /etc/debian_version ]] && ! have apt-get; then
    warn "Not Debian/apt — install python3 (>=3.10), git, python3-venv yourself"
    return 0
  fi
  local need=()
  have git || need+=(git)
  have curl || need+=(curl)
  have python3 || need+=(python3)
  # venv module
  if have python3 && ! python3 -c 'import venv' 2>/dev/null; then
    need+=(python3-venv python3-full)
  fi
  # ensurepip often needs full
  if have python3 && ! python3 -c 'import ensurepip' 2>/dev/null; then
    need+=(python3-venv python3-full)
  fi
  if [[ ${#need[@]} -gt 0 ]]; then
    # uniq
    local u=() x
    for x in "${need[@]}"; do
      [[ " ${u[*]} " == *" $x "* ]] || u+=("$x")
    done
    _apt_install "${u[@]}"
  fi
  have python3 || die "python3 still missing after apt"
  python3 -c 'import sys; raise SystemExit(0 if sys.version_info>=(3,10) else 1)' \
    || die "Need Python >= 3.10 (found $(python3 -c 'import sys; print("%d.%d"%sys.version_info[:2])'))"
  ok "System deps OK"
}

ensure_repo_current() {
  if [[ -d "$ROOT/.git" ]]; then
    info "Fetching latest…"
    if ! git -C "$ROOT" pull --ff-only; then
      warn "git pull failed (local changes?) — continuing with current tree"
    else
      ok "Repo up to date"
    fi
  fi
}

install_agent() {
  info "Installing launcher…"
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
  cat > "$BIN_DIR/desktop-mini-bot-update" << UPD
#!/usr/bin/env bash
exec bash "$ROOT/install.sh" --update "\$@"
UPD
  chmod +x "$BIN_DIR/desktop-mini-bot-update"
  if [[ ! -f "$CONFIG_FILE" ]]; then
    cp "$ROOT/config.example.json" "$CONFIG_FILE" || die "cannot write $CONFIG_FILE"
    ok "Config: $CONFIG_FILE"
  else
    warn "Keeping config: $CONFIG_FILE"
  fi
  if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    warn "Add to PATH:  export PATH=\"$BIN_DIR:\$PATH\""
  fi
  ok "Launcher: $BIN_DIR/desktop-mini-bot"
}

install_browser() {
  info "Installing Playwright + Chromium…"
  local venv="$ROOT/.venv"
  if [[ ! -x "$venv/bin/python" ]]; then
    rm -rf "$venv"
    python3 -m venv "$venv" || die "python3 -m venv failed (sudo apt install python3-venv python3-full)"
  fi
  [[ -x "$venv/bin/python" ]] || die "venv broken: $venv/bin/python missing"
  "$venv/bin/python" -m pip install -U pip || die "pip upgrade failed"
  "$venv/bin/python" -m pip install -U "playwright>=1.40" || die "pip install playwright failed"
  "$venv/bin/python" -m playwright install chromium || die "playwright install chromium failed"
  # Best-effort OS libs for Chromium on Debian
  if have apt-get && [[ "$SKIP_APT" -eq 0 ]]; then
    if "$venv/bin/python" -m playwright install-deps chromium 2>/dev/null; then
      ok "Chromium system libs"
    else
      warn "playwright install-deps skipped/failed — browser may still work"
    fi
  fi
  ok "Browser hands ready"
}

install_model_hint() {
  if ! have ollama; then
    warn "Ollama not found. Optional: curl -fsSL https://ollama.com/install.sh | sh"
    return 0
  fi
  local model="${DMB_MODEL:-hammer2.0:1.5b}"
  info "Pulling model $model …"
  if ollama pull "$model"; then
    ok "Model $model"
    [[ -f "$CONFIG_FILE" ]] && python3 - "$CONFIG_FILE" "$model" <<'PY'
import json,sys
p,m=sys.argv[1],sys.argv[2]
c=json.load(open(p,encoding="utf-8"))
c.update({"base_url":"http://127.0.0.1:11434/v1","api_key":"ollama","model":m})
json.dump(c, open(p,"w",encoding="utf-8"), indent=2)
open(p,"a",encoding="utf-8").write("\n")
PY
  else
    warn "Model pull failed — edit $CONFIG_FILE later"
  fi
}

verify() {
  info "Verifying…"
  local py=python3
  [[ -x "$ROOT/.venv/bin/python" ]] && py="$ROOT/.venv/bin/python"
  ( cd "$ROOT" && PYTHONPATH=src "$py" -c "import desktop_mini_bot; print(desktop_mini_bot.__version__)" ) \
    || die "import desktop_mini_bot failed"
  ( cd "$ROOT" && PYTHONPATH=src "$py" -m desktop_mini_bot --mock-llm --goal "click Save" >/dev/null ) \
    || die "mock dry-run failed"
  if [[ "$WITH_BROWSER" -eq 1 ]]; then
    ( cd "$ROOT" && PYTHONPATH=src "$py" -c "from playwright.sync_api import sync_playwright" ) \
      || die "playwright import failed"
  fi
  ok "Verify passed"
}

summary() {
  cat <<S

${GRN}desktop-mini-bot ready${RST}
  App:    $ROOT
  Run UI: $ROOT/run.sh --ui
          desktop-mini-bot --ui
  Browser mock: $ROOT/run.sh --browser --mock "click Save"
  Update: curl -fsSL https://raw.githubusercontent.com/jor-teron/desktop-mini-bot/main/install.sh | bash -s -- --update
          desktop-mini-bot-update

S
}

main() {
  info "desktop-mini-bot install (solve-all)"
  ensure_system_deps
  ensure_repo_current
  install_agent
  if [[ "$WITH_BROWSER" -eq 1 ]]; then
    install_browser
    install_agent  # refresh launcher to prefer .venv
  fi
  [[ "$WITH_MODEL" -eq 1 ]] && install_model_hint
  verify
  summary
}

main
