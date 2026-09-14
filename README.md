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

## Quick start

```bash
# offline demo (no model server)
PYTHONPATH=src python -m desktop_mini_bot --mock-llm --goal "click Save"

# with Ollama (example)
# ollama pull <your-1b-tool-model>
cp config.example.json config.json
PYTHONPATH=src python -m desktop_mini_bot --config config.json --goal "Open settings and click Save"
```

Tests:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
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
