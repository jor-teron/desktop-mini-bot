# desktop-mini-bot

Lightweight **no-vision** Linux desktop CUA for **low-RAM** machines and **~10 tok/s** local models.

**v0.1.1** — stdlib only (no pip), plain `config.txt`, clean `app/` layout, web UI model dropdown.

## Install / update

```bash
curl -fsSL https://raw.githubusercontent.com/jor-teron/desktop-mini-bot/main/install.sh | bash
```

## Layout

```text
desktop-mini-bot/
  README.md  LICENSE  install.sh  run.sh
  config.txt              # your settings (plain text)
  config.example.txt
  app/                    # code, tests, examples, chrome-data/
```

## Config

Edit `config.txt`:

```text
model=your-ollama-tag
base_url=http://127.0.0.1:11434/v1
```

Or pick the model in the web UI dropdown (`./run.sh --ui`).

## Run

```bash
./run.sh --ui
./run.sh --browser --mock "open google.com"
./run.sh --browser --local "open https://www.google.com"
```

## License

MIT
