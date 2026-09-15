# desktop-mini-bot

Lightweight **no-vision** Linux desktop CUA for **low-RAM** machines (about 1–4 GB) and **slow local models** (~10 tok/s).

Most computer-use agents assume a fast cloud VLM and screenshots. This one does not.

## Design

| Choice | Why |
|--------|-----|
| No screenshots | Fits weak CPUs; no vision model |
| Short JSON actions | Usable at ~10 tok/s |
| Plan small / execute locally | Model rarely called |
| Stdlib core + optional Playwright | Tiny default footprint |
| Local models only | Offline after one-time download |

**Suggested brain:** Hammer 2.0 1.5B or MiniCPM5-1B via Ollama (`127.0.0.1`).

## Status — Phase 1

- **Phase 0:** dry-run fake UI + mock/local LLM ✅
- **Phase 1:** real Chromium via Playwright **DOM** (no screenshots) ✅
- **Phase 2:** nested Xephyr practice desk (next)
- **Phase 3:** AT-SPI native apps
- **Later:** gated `run_command`

## Install / update (one paste)

```bash
curl -fsSL https://raw.githubusercontent.com/jor-teron/desktop-mini-bot/main/install.sh | bash
```

This **solve-all** script will:
1. Install missing system packages (git, python3, venv) via `apt` when needed  
2. Clone or update `~/desktop-mini-bot`  
3. Install the launcher + Playwright Chromium (browser hands)  
4. Run a quick verify smoke test  

```bash
# update later (same one-liner)
curl -fsSL https://raw.githubusercontent.com/jor-teron/desktop-mini-bot/main/install.sh | bash -s -- --update
# or: desktop-mini-bot-update

# agent only (no browser)
curl -fsSL https://raw.githubusercontent.com/jor-teron/desktop-mini-bot/main/install.sh | bash -s -- --no-browser

# also pull an Ollama model
curl -fsSL https://raw.githubusercontent.com/jor-teron/desktop-mini-bot/main/install.sh | bash -s -- --with-model
```

## Run

```bash
# Tiny local chat page (middle ground UI)
./run.sh --ui

# Terminal practice (fake desk)
./run.sh "click Save"

# Real browser window you can watch (mock brain)
./run.sh --browser --mock "click Save"

# Real browser + your local Ollama model
./run.sh --browser --local "click Save"

# Headless browser
./run.sh --browser --headless --mock "click Save"
```

On your PC after we push updates:

```bash
cd desktop-mini-bot
git pull
./install.sh --browser   # once, if you want real browser mode
```

## Action wire format

```json
{"a":"open_url","u":"https://example.com"}
{"a":"find","r":"button","n":"Save"}
{"a":"click","ref":"e1"}
{"a":"type","txt":"hello","ref":"e3"}
{"a":"done","s":"Finished"}
```

| `a` | fields |
|-----|--------|
| `launch_app` | `n` name or URL |
| `open_url` | `u` url |
| `focus_window` | `t` title (dry-run) |
| `find` | `r` role, `n` name |
| `click` | `ref` (or `hit1` after find) |
| `type` | `txt`, optional `ref` |
| `done` | `s` summary |

## Config

See `config.example.json`. Point `model` at whatever you have locally, e.g. `hammer2.0:1.5b`.

## License

MIT
