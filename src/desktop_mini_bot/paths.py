"""Everything lives under the project working directory."""

from __future__ import annotations

from pathlib import Path

_ROOT: Path | None = None


def project_root() -> Path:
    global _ROOT
    if _ROOT is None:
        # src/desktop_mini_bot/paths.py -> repo root
        _ROOT = Path(__file__).resolve().parents[2]
    return _ROOT


def config_path() -> Path:
    return project_root() / "config.json"


def chrome_dir() -> Path:
    d = project_root() / "chrome-data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensure_config() -> Path:
    """Create config.json from example if missing."""
    cfg = config_path()
    if not cfg.is_file():
        example = project_root() / "config.example.json"
        cfg.write_text(example.read_text(encoding="utf-8") if example.is_file() else "{\n}\n", encoding="utf-8")
    return cfg
