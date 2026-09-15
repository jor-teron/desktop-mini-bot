"""Project paths — everything under the repo; code lives in app/."""

from __future__ import annotations

from pathlib import Path

_ROOT: Path | None = None


def project_root() -> Path:
    global _ROOT
    if _ROOT is None:
        _ROOT = Path(__file__).resolve().parents[2]
    return _ROOT


def app_dir() -> Path:
    return project_root() / "app"


def config_path() -> Path:
    return project_root() / "config.txt"


def chrome_dir() -> Path:
    d = app_dir() / "chrome-data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensure_config() -> Path:
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
