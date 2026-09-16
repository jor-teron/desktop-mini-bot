#!/usr/bin/env bash
# desktop-mini-bot v0.2.3 — one-paste install/update (no pip; all under project dir)
#   curl -fsSL https://raw.githubusercontent.com/jor-teron/desktop-mini-bot/main/install.sh | bash
# MIT / jor-teron.
set -euo pipefail

# --- settings ---
REPO_URL="${DMB_REPO:-https://github.com/jor-teron/desktop-mini-bot.git}"
DEST="${DMB_HOME:-$HOME/desktop-mini-bot}"
WITH_BROWSER=1   # install Chromium via apt when missing
WITH_MODEL=0     # optionally ollama pull a local model
SKIP_APT=0

RED=$'\033[31m'; GRN=$'\033[32m'; YLW=$'\033[33m'; RST=$'\033[0m'
info(){ printf '%s\n' "$*"; }
ok(){ printf '%s✓ %s%s\n' "$GRN" "$*" "$RST"; }
warn(){ printf '%s! %s%s\n' "$YLW" "$*" "$RST"; }
die(){ printf '%s✗ %s%s\n' "$RED" "$*" "$RST" >&2; exit 1; }
have(){ command -v "$1" >/dev/null 2>&1; }

# --- apt helper ---
_apt_install() {
  have sudo || die "need sudo to install: $*"
  info "apt install: $*"
  sudo apt-get update -y || die "apt-get update failed"
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "$@" || die "apt install failed: $*"
}

# --- CLI flags ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --update) shift ;;  # no-op alias for re-runs
    --browser) WITH_BROWSER=1; shift ;;
    --no-browser) WITH_BROWSER=0; shift ;;
    --with-model) WITH_MODEL=1; shift ;;
    --skip-apt) SKIP_APT=1; shift ;;
    -h|--help) echo "Usage: install.sh [--update] [--browser|--no-browser] [--with-model] [--skip-apt]"; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

# --- clone or re-exec from repo copy ---
# When piped via curl, this script is not inside the repo yet — clone then re-exec.
_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || true)"
if [[ -z "${_SRC}" || ! -f "${_SRC}/app/desktop_mini_bot/__main__.py" ]]; then
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

# --- system deps ---
if [[ "$SKIP_APT" -eq 0 ]] && have apt-get; then
  need=()
  have git || need+=(git)
  have python3 || need+=(python3)
  if [[ "$WITH_BROWSER" -eq 1 ]]; then
    if ! have chromium && ! have chromium-browser && ! have google-chrome && ! have google-chrome-stable; then
      need+=(chromium)
    fi
  fi
  [[ ${#need[@]} -gt 0 ]] && _apt_install "${need[@]}"
fi
have python3 || die "python3 missing"
python3 -c 'import sys; raise SystemExit(0 if sys.version_info>=(3,10) else 1)' || die "Need Python >= 3.10"
ok "System deps OK"

# Fast-forward if this tree is a git checkout
[[ -d "$ROOT/.git" ]] && git -C "$ROOT" pull --ff-only || true

# --- config.txt ---
if [[ ! -f "$ROOT/config.txt" ]]; then
  cp "$ROOT/config.example.txt" "$ROOT/config.txt"
  ok "Wrote $ROOT/config.txt — set api_key= for Gemini (https://aistudio.google.com/apikey)"
else
  warn "Keeping $ROOT/config.txt"
fi

# --- dmb launcher shim ---
cat > "$ROOT/dmb" << LAUNCH
#!/usr/bin/env bash
ROOT="$ROOT"
export PYTHONPATH="\$ROOT/app\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m desktop_mini_bot "\$@"
LAUNCH
chmod +x "$ROOT/dmb"
ok "Launcher: $ROOT/dmb"

# --- optional Ollama model ---
if [[ "$WITH_MODEL" -eq 1 ]]; then
  if have ollama; then
    model="${DMB_MODEL:-hammer2.0:1.5b}"
    ollama pull "$model" || warn "model pull failed — edit $ROOT/config.txt"
    if grep -q '^model=' "$ROOT/config.txt" 2>/dev/null; then
      sed -i "s/^model=.*/model=$model/" "$ROOT/config.txt"
    else
      echo "model=$model" >> "$ROOT/config.txt"
    fi
  else
    warn "Ollama optional: curl -fsSL https://ollama.com/install.sh | sh"
  fi
fi

# --- smoke verify ---
( cd "$ROOT" && PYTHONPATH=app python3 -c "from desktop_mini_bot.llm import make_llm, guess_url; from desktop_mini_bot.schema import parse_action; assert guess_url('open google.com'); parse_action('{\"a\":\"done\",\"s\":\"ok\"}'); print('ok')" ) \
  || die "verify failed"
ok "Verify passed (v0.2.3)"

cat <<S

${GRN}Ready 0.2.3${RST} — $ROOT
  Config: $ROOT/config.txt   (set api_key= for Gemini)
  Chat:   $ROOT/run.sh --ui
  Run:    $ROOT/run.sh --browser "open google.com"

S
