"""desktop-mini-bot v0.2.1 — load/save plain-text config.txt (key=value).

Merges defaults with on-disk settings; preserves comments when updating keys.
Part of the lightweight no-vision Linux CUA (stdlib only).
MIT / jor-teron.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .paths import config_path, ensure_config

# Defaults applied when a key is absent from config.txt
DEFAULTS: dict[str, Any] = {
    "provider": "gemini",  # gemini (online) | ollama (local)
    "api_key": "",  # Gemini API key from Google AI Studio
    "model": "gemini-3.5-flash-lite",
    "ollama_base_url": "http://127.0.0.1:11434/v1",  # OpenAI-compat endpoint
    "ollama_api_key": "ollama",  # placeholder for local Ollama
    "max_tokens": 120,  # LLM reply budget per step
    "temperature": 0.1,  # low = more deterministic JSON
    "max_steps": 20,  # agent loop safety cap
    "headless": False,  # hide Chromium window when true
    "start_url": "about:blank",
}

# Truthy strings for boolean config keys
_BOOL = {"1", "true", "yes", "on"}


# --- parsing ---

def _parse_value(key: str, raw: str) -> Any:
    """Coerce a raw string value based on the config key type."""
    v = raw.strip()
    if key in {"max_tokens", "max_steps"}:
        return int(v)
    if key == "temperature":
        return float(v)
    if key in {"headless", "dry_run"}:
        return v.lower() in _BOOL
    return v


def load_txt(path: Path) -> dict[str, Any]:
    """Parse a key=value text file; skip blanks and # comments. Returns typed dict."""
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


# --- mutate config.txt ---

def set_keys(updates: dict[str, str], path: Path | None = None) -> None:
    """Update keys in config.txt in place, preserving comments and order."""
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
    """Persist the model id into config.txt."""
    set_keys({"model": model}, path)


def save_api_key(api_key: str, path: Path | None = None) -> None:
    """Persist the API key into config.txt (never commit that file)."""
    set_keys({"api_key": api_key}, path)


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Return DEFAULTS merged with values from config.txt (or given path)."""
    cfg = dict(DEFAULTS)
    p = Path(path) if path else ensure_config()
    cfg.update(load_txt(p))
    # legacy aliases: older configs used base_url instead of ollama_base_url
    if cfg.get("base_url") and not path:
        pass
    if "base_url" in cfg and "ollama_base_url" not in load_txt(p):
        cfg["ollama_base_url"] = cfg.get("base_url") or cfg["ollama_base_url"]
    return cfg
