"""Load/save plain-text config.txt (key=value)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .paths import config_path, ensure_config

DEFAULTS: dict[str, Any] = {
    "provider": "gemini",
    "api_key": "",
    "model": "gemini-3.5-flash-lite",
    "ollama_base_url": "http://127.0.0.1:11434/v1",
    "ollama_api_key": "ollama",
    "max_tokens": 120,
    "temperature": 0.1,
    "max_steps": 20,
    "headless": False,
    "start_url": "about:blank",
}

_BOOL = {"1", "true", "yes", "on"}


def _parse_value(key: str, raw: str) -> Any:
    v = raw.strip()
    if key in {"max_tokens", "max_steps"}:
        return int(v)
    if key == "temperature":
        return float(v)
    if key in {"headless", "dry_run"}:
        return v.lower() in _BOOL
    return v


def load_txt(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, val = s.partition("=")
        k = k.strip()
        if k:
            out[k] = _parse_value(k, val)
    return out


def set_keys(updates: dict[str, str], path: Path | None = None) -> None:
    """Update keys in config.txt, preserving comments/order."""
    p = path or ensure_config()
    lines = p.read_text(encoding="utf-8").splitlines()
    done = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}")
                done.add(k)
                continue
        new_lines.append(line)
    for k, v in updates.items():
        if k not in done:
            new_lines.append(f"{k}={v}")
    p.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def save_model(model: str, path: Path | None = None) -> None:
    set_keys({"model": model}, path)


def save_api_key(api_key: str, path: Path | None = None) -> None:
    set_keys({"api_key": api_key}, path)


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    p = Path(path) if path else ensure_config()
    cfg.update(load_txt(p))
    # legacy aliases
    if cfg.get("base_url") and not path:
        pass
    if "base_url" in cfg and "ollama_base_url" not in load_txt(p):
        cfg["ollama_base_url"] = cfg.get("base_url") or cfg["ollama_base_url"]
    return cfg
