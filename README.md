# desktop-mini-bot

Lightweight **no-vision** Linux desktop CUA for **low-RAM** machines (about 1–4 GB) and **slow local models** (~10 tok/s).

Most computer-use agents assume a fast cloud VLM and screenshots. This one does not.

## Design

| Choice | Why |
|--------|-----|
| No screenshots | Fits weak CPUs; no vision model |
| Short JSON actions | Usable at ~10 tok/s |
| Plan small / execute locally | Model rarely called |
| Stdlib-only core | Tiny dependency surface |
| Dry-run first | Prove the loop before real clicks |

**Default brain:** 1B-class tool-calling model (e.g. Hammer2.1-1.5b via Ollama).

## Status — Phase 0

Dry-run agent loop with a fake UI. No real desktop control yet.

Roadmap:

1. **Phase 0** — dry-run + schema + local LLM HTTP *(this repo)*
2. **Phase 1** — Playwright DOM (still no screenshots)
3. **Phase 2** — nested Xephyr “practice desk” sandbox
4. **Phase 3** — AT-SPI for native Linux apps
5. **Later** — gated `run_command` (allowlisted shell)

## Install

```bash
git clone https://github.com/jor-teron/desktop-mini-bot.git
cd desktop-mini-bot
./install.sh
```

Menu options:

1. **Agent only** — offline, no downloads (launcher + config)
2. **Agent + local model** — sets up Ollama pull (one-time network, then offline)
3. **Tests / smoke** — unittest + `--mock-llm` demo

Non-interactive:

```bash
./install.sh --agent        # offline
./install.sh --with-model   # agent + ollama model helper
./install.sh --test
```

After install:

```bash
desktop-mini-bot --mock-llm --goal "click Save"
desktop-mini-bot --config ~/.config/desktop-mini-bot/config.json --goal "click Save"
```

## Quick start (no install)

```bash
# offline demo (no model server)
PYTHONPATH=src python3 -m desktop_mini_bot --mock-llm --goal "click Save"

# with local Ollama (example)
cp config.example.json config.json
PYTHONPATH=src python3 -m desktop_mini_bot --config config.json --goal "Open settings and click Save"
```

Tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
# or: ./install.sh --test
```

## Action wire format

Short keys keep generation cheap:

```json
{"a":"find","r":"button","n":"Save"}
{"a":"click","ref":"b1"}
{"a":"type","txt":"hello","ref":"t1"}
{"a":"done","s":"Finished"}
```

| `a` | fields |
|-----|--------|
| `launch_app` | `n` name |
| `focus_window` | `t` title |
| `find` | `r` role, `n` name |
| `click` | `ref` |
| `type` | `txt`, optional `ref` |
| `done` | `s` summary |

## Config

See `config.example.json`. Point `base_url` at any OpenAI-compatible server (Ollama, llama.cpp, vLLM).

## License

MIT
