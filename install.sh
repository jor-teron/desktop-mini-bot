#!/usr/bin/env bash
# desktop-mini-bot installer — local / offline-friendly (Debian & friends)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${PREFIX:-$HOME/.local}"
BIN_DIR="$PREFIX/bin"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/desktop-mini-bot"
CONFIG_FILE="$CONFIG_DIR/config.json"

RED=$'\033[31m'; GRN=$'\033[32m'; YLW=$'\033[33m'; DIM=$'\033[2m'; RST=$'\033[0m'

info()  { printf '%s\n' "$*"; }
ok()    { printf '%s%s%s\n' "$GRN" "$*" "$RST"; }
warn()  { printf '%s%s%s\n' "$YLW" "$*" "$RST"; }
die()   { printf '%s%s%s\n' "$RED" "$*" "$RST" >&2; exit 1; }

need_python() {
  command -v python3 >/dev/null 2>&1 || die "python3 not found. On Debian: sudo apt install python3"
  local ver
  ver="$(python3 -c 'import sys; print("%d.%d"%sys.version_info[:2])')"
  python3 -c 'import sys; raise SystemExit(0 if sys.version_info>=(3,10) else 1)' \
    || die "Need Python >= 3.10 (found $ver)"
  ok "Python $ver OK"
}

install_agent() {
  info "Installing desktop-mini-bot (stdlib only — no pip packages)…"
  need_python
  mkdir -p "$BIN_DIR" "$CONFIG_DIR"

  # Editable layout via a tiny launcher (avoids requiring pip/setuptools).
  cat > "$BIN_DIR/desktop-mini-bot" << LAUNCH
#!/usr/bin/env bash
export PYTHONPATH="$ROOT/src\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m desktop_mini_bot "\$@"
LAUNCH
  chmod +x "$BIN_DIR/desktop-mini-bot"

  if [[ ! -f "$CONFIG_FILE" ]]; then
    cp "$ROOT/config.example.json" "$CONFIG_FILE"
    ok "Wrote $CONFIG_FILE"
  else
    warn "Keeping existing $CONFIG_FILE"
  fi

  if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    warn "Add to PATH (e.g. in ~/.bashrc):"
    info "  export PATH=\"$BIN_DIR:\$PATH\""
  fi

  ok "Agent installed."
  info "Try:  desktop-mini-bot --mock-llm --goal \"click Save\""
  info "  or:  $BIN_DIR/desktop-mini-bot --mock-llm --goal \"click Save\""
}

# One-time network may be needed to fetch Ollama / the model weights.
# After that, everything stays local (127.0.0.1).
install_ollama_hint() {
  info "Local model runtime (Ollama)…"
  if command -v ollama >/dev/null 2>&1; then
    ok "Ollama already installed: $(command -v ollama)"
  else
    warn "Ollama is not installed."
    info "Install once (needs network), then models run fully offline:"
    info "  curl -fsSL https://ollama.com/install.sh | sh"
    info "Or Debian manual: https://ollama.com/download/linux"
    return 0
  fi

  # Prefer a small tool-call model; user can change in config.
  local model="${DMB_MODEL:-hammer2.1:1.5b}"
  info "Pulling model '$model' (one-time download; then offline)…"
  if ollama pull "$model"; then
    ok "Model ready: $model"
  else
    warn "Could not pull '$model'."
    info "List local models: ollama list"
    info "Set any local tag in $CONFIG_FILE → \"model\""
  fi

  # Point config at local Ollama if we just set things up.
  if [[ -f "$CONFIG_FILE" ]]; then
    python3 - "$CONFIG_FILE" "$model" <<'PY'
import json, sys
path, model = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as f:
    cfg = json.load(f)
cfg["base_url"] = "http://127.0.0.1:11434/v1"
cfg["api_key"] = "ollama"
cfg["model"] = model
with open(path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")
print("updated", path)
PY
  fi

  info "Start server if needed:  ollama serve"
  info "Run agent:  desktop-mini-bot --config $CONFIG_FILE --goal \"click Save\""
}

smoke_test() {
  need_python
  ( cd "$ROOT" && PYTHONPATH=src python3 -m unittest discover -s tests -q )
  ok "Tests passed"
  ( cd "$ROOT" && PYTHONPATH=src python3 -m desktop_mini_bot --mock-llm --goal "click Save" )
}

usage() {
  cat <<USAGE
Usage: ./install.sh [option]

  (no args)     Interactive menu
  --agent       Install agent launcher + config only (fully offline)
  --with-model  Agent + help install/pull local Ollama model
  --test        Run unit tests + mock-llm smoke demo
  --help        Show this help

Env:
  PREFIX=$PREFIX     install bin here
  DMB_MODEL=...      model tag for ollama pull (default hammer2.1:1.5b)

Everything talks to 127.0.0.1 — no cloud API. Model download is the only
step that needs network, and only once.
USAGE
}

menu() {
  cat <<MENU

desktop-mini-bot installer
  1) Agent only          (offline — no model download)
  2) Agent + local model (Ollama; one-time download)
  3) Run tests / smoke
  4) Quit

MENU
  local choice
  read -r -p "Choose [1-4]: " choice
  case "$choice" in
    1) install_agent ;;
    2) install_agent; install_ollama_hint ;;
    3) smoke_test ;;
    4) exit 0 ;;
    *) die "Invalid choice" ;;
  esac
}

main() {
  case "${1:-}" in
    "" ) menu ;;
    --agent) install_agent ;;
    --with-model) install_agent; install_ollama_hint ;;
    --test) smoke_test ;;
    -h|--help) usage ;;
    *) usage; die "Unknown option: $1" ;;
  esac
}

main "$@"
