# desktop-mini-bot

Lightweight **no-vision** Linux desktop CUA. **v0.2.0** is a real browser agent: **Google Gemini** online by default (`gemini-3.5-flash-lite`), **Ollama** optional. Stdlib only (no pip). API key lives in plain `config.txt`.

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

## Run

```bash
./run.sh --ui
./run.sh --browser "open google.com"
./run.sh --browser --provider ollama --model hammer2.0:1.5b "open https://www.google.com"
```

The web UI lets you pick provider/model and **Save** the API key into `config.txt`.

## Layout

```text
desktop-mini-bot/
  README.md  LICENSE  install.sh  run.sh
  config.txt              # your settings (plain text, not committed)
  config.example.txt
  app/                    # code, tests, chrome-data/
```

## License

MIT
