"""Load JSON config from the project directory (stdlib only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import config_path, ensure_config

DEFAULTS: dict[str, Any] = {
    "base_url": "http://127.0.0.1:11434/v1",
    "api_key": "ollama",
    "model": "hammer2.0:1.5b",
    "max_tokens": 80,
    "temperature": 0.1,
    "max_steps": 12,
    "dry_run": True,
    "headless": False,
    "start_url": "about:blank",
}


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    p = Path(path) if path else ensure_config()
    if p.is_file():
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("config must be a JSON object")
        cfg.update({k: v for k, v in data.items() if v not in ("", None)})
    return cfg
