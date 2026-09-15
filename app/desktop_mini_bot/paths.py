"""desktop-mini-bot v0.2.1 — project paths (repo root, config, chrome profile).

Everything lives under the repo; Python package code is in app/.
Part of the lightweight no-vision Linux CUA (stdlib only).
MIT / jor-teron.
"""

from __future__ import annotations

from pathlib import Path

# Cached absolute repo root (parents[2] from this file: …/app/desktop_mini_bot/paths.py)
_ROOT: Path | None = None


# --- paths / filesystem ---

def project_root() -> Path:
    """Absolute path to the desktop-mini-bot repo root (cached)."""
    global _ROOT
    if _ROOT is None:
        _ROOT = Path(__file__).resolve().parents[2]
    return _ROOT


def app_dir() -> Path:
    """Path to the app/ directory (package + chrome-data + tests)."""
    return project_root() / "app"


def config_path() -> Path:
    """Path to the user's config.txt at the repo root (gitignored)."""
    return project_root() / "config.txt"


def chrome_dir() -> Path:
    """Chromium --user-data-dir under app/chrome-data/ (created if missing)."""
    d = app_dir() / "chrome-data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensure_config() -> Path:
    """Create config.txt from config.example.txt if missing; return its path."""
    cfg = config_path()
    if not cfg.is_file():
        example = project_root() / "config.example.txt"
        cfg.write_text(
            example.read_text(encoding="utf-8")
            if example.is_file()
            else "provider=gemini\nmodel=gemini-3.5-flash-lite\napi_key=\n",
            encoding="utf-8",
        )
    return cfg
