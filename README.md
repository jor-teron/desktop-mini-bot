# desktop-mini-bot

Lightweight **no-vision** Linux desktop CUA. **v0.2.3** is a real browser agent: **Google Gemini** online by default (`gemini-3.5-flash-lite`), **Ollama** optional. Stdlib only (no pip). API key lives in plain `config.txt`.

**v0.2.3** adds a project-root `workspace/` for downloads, keeps the AI browser open after a run (configurable), maximizes the window on launch, and a chat UI **Clear** button. Chromium uses a dedicated profile under `app/chrome-data/` — never your personal Chrome.

**v0.2.2** added optional LLM pacing: `token_rate`, `request_gap_sec`, and `rpm_limit` in `config.txt` (all default 0 = unlimited).

## Install / update

```bash
curl -fsSL https://raw.githubusercontent.com/jor-teron/desktop-mini-bot/main/install.sh | bash
```

## Config

Copy `config.example.txt` → `config.txt` (install does this). Put your key there:

```text
provider=gemini
api_key=YOUR_KEY
model=gemini-3.5-flash-lite
```

Get a key: https://aistudio.google.com/apikey  
`config.txt` is gitignored — do not commit it.

For local models:

```text
provider=ollama
model=your-ollama-tag
ollama_base_url=http://127.0.0.1:11434/v1
```

Browser-related keys:

```text
headless=false
keep_browser_open=true   # leave Chromium open after a goal (default)
start_url=about:blank
```

## Run

```bash
./run.sh --ui
./run.sh --browser "open google.com"
./run.sh --browser --provider ollama --model hammer2.0:1.5b "open https://www.google.com"
```

The web UI lets you pick provider/model and **Save** the API key into `config.txt`. Use **Clear** to wipe the run log (does not touch config or workspace files).

## Layout

```text
desktop-mini-bot/
  README.md  LICENSE  install.sh  run.sh
  config.txt              # your settings (plain text, not committed)
  config.example.txt
  workspace/              # downloads + saved files (gitignored contents)
  app/                    # code, tests
  app/chrome-data/        # AI-only Chromium profile (not your personal Chrome)
```

## License

MIT
