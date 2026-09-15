"""Load plain-text config.txt (key=value)."""

from __future__ import annotations

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

_BOOL = {"1", "true", "yes", "on"}


def _parse_value(key: str, raw: str) -> Any:
    v = raw.strip()
    if key in {"max_tokens", "max_steps"}:
        return int(v)
    if key in {"temperature"}:
        return float(v)
    if key in {"headless", "dry_run"}:
        return v.lower() in _BOOL
    return v


def load_txt(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, val = line.partition("=")
        k, val = k.strip(), val.strip()
        if k:
            out[k] = _parse_value(k, val)
    return out


def save_model(model: str, path: Path | None = None) -> None:
    """Update model= in config.txt, keeping other lines."""
    p = path or config_path()
    ensure_config()
    lines = p.read_text(encoding="utf-8").splitlines()
    found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith("model=") or line.strip().startswith("model ="):
            new_lines.append(f"model={model}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"model={model}")
    p.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    p = Path(path) if path else ensure_config()
    # allow legacy .json only if explicitly passed
    if p.suffix == ".json":
        import json
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            cfg.update({k: v for k, v in data.items() if v not in ("", None)})
        return cfg
    cfg.update(load_txt(p))
    return cfg
