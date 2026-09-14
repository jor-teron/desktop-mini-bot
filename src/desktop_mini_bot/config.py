"""Load JSON config with stdlib only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULTS: dict[str, Any] = {
    "base_url": "http://127.0.0.1:11434/v1",
    "api_key": "ollama",
    "model": "hammer2.1:1.5b",
    "max_tokens": 80,
    "temperature": 0.1,
    "max_steps": 12,
    "dry_run": True,
}


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    if path is None:
        return cfg
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    cfg.update(data)
    return cfg
