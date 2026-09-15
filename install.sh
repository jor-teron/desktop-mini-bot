#!/usr/bin/env bash
# desktop-mini-bot — one-paste install/update (all files under project dir, no pip)
#   curl -fsSL https://raw.githubusercontent.com/jor-teron/desktop-mini-bot/main/install.sh | bash
set -euo pipefail

REPO_URL="${DMB_REPO:-https://github.com/jor-teron/desktop-mini-bot.git}"
DEST="${DMB_HOME:-$HOME/desktop-mini-bot}"
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
      echo "Everything stays under the project folder. No pip. No ~/.config scatter."
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

[[ -d "$ROOT/.git" ]] && git -C "$ROOT" pull --ff-only || true

# Project-local config only
if [[ ! -f "$ROOT/config.json" ]]; then
  cp "$ROOT/config.example.json" "$ROOT/config.json"
  ok "Wrote $ROOT/config.json"
else
  warn "Keeping $ROOT/config.json"
fi

# Project-local launcher (not ~/.local)
cat > "$ROOT/dmb" << LAUNCH
#!/usr/bin/env bash
ROOT="$ROOT"
export PYTHONPATH="\$ROOT/src\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m desktop_mini_bot "\$@"
LAUNCH
chmod +x "$ROOT/dmb"
ok "Launcher: $ROOT/dmb"

if [[ "$WITH_MODEL" -eq 1 ]]; then
  if have ollama; then
    model="${DMB_MODEL:-hammer2.0:1.5b}"
    ollama pull "$model" || warn "model pull failed — edit $ROOT/config.json"
    python3 - "$ROOT/config.json" "$model" <<'PY'
import json,sys
p,m=sys.argv[1],sys.argv[2]
c=json.load(open(p,encoding="utf-8"))
c["model"]=m
json.dump(c, open(p,"w",encoding="utf-8"), indent=2)
open(p,"a",encoding="utf-8").write("\n")
PY
  else
    warn "Ollama optional: curl -fsSL https://ollama.com/install.sh | sh"
  fi
fi

( cd "$ROOT" && PYTHONPATH=src python3 -m desktop_mini_bot --mock-llm --goal "click Save" >/dev/null ) \
  || die "verify failed"
ok "Verify passed"

cat <<S

${GRN}Ready${RST} — everything under $ROOT
  Config:  $ROOT/config.json   (set \"model\" from: ollama list)
  Chat:    $ROOT/run.sh --ui
  Google:  $ROOT/run.sh --browser --mock \"open google.com\"
  Update:  curl -fsSL https://raw.githubusercontent.com/jor-teron/desktop-mini-bot/main/install.sh | bash

S
