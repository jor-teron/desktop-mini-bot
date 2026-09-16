"""desktop-mini-bot v0.2.2 — config.txt mutation and LLM factory tests.

Ensures set_keys preserves api_key and Gemini requires a non-empty key.
Part of the lightweight no-vision Linux CUA (stdlib only).
MIT / jor-teron.
"""

import tempfile
import unittest
from pathlib import Path

from desktop_mini_bot.config import load_config, load_txt, set_keys
from desktop_mini_bot.llm import make_llm, guess_url


# --- config ---

class TestConfig(unittest.TestCase):
    """Temp-file checks for config parsing and LLM construction."""

    def test_set_keys_preserves_api_key(self) -> None:
        """Updating model must not wipe an existing api_key line."""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.txt"
            p.write_text("provider=gemini\napi_key=secret\nmodel=gemini-3.5-flash-lite\n")
            set_keys({"model": "gemini-2.0-flash"}, p)
            data = load_txt(p)
            self.assertEqual(data["api_key"], "secret")
            self.assertEqual(data["model"], "gemini-2.0-flash")

    def test_make_llm_requires_key(self) -> None:
        """Gemini provider with empty api_key raises RuntimeError."""
        with self.assertRaises(RuntimeError):
            make_llm({"provider": "gemini", "api_key": "", "model": "gemini-3.5-flash-lite"})

    def test_guess_url(self) -> None:
        """Natural-language google goal maps to https://www.google.com."""
        self.assertEqual(guess_url("open google.com"), "https://www.google.com")


    def test_rate_limit_defaults(self) -> None:
        """DEFAULTS leave token_rate / gap / rpm at unlimited (0)."""
        from desktop_mini_bot.config import DEFAULTS, load_txt, load_config
        self.assertEqual(DEFAULTS["token_rate"], 0)
        self.assertEqual(DEFAULTS["request_gap_sec"], 0.0)
        self.assertEqual(DEFAULTS["rpm_limit"], 0)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.txt"
            p.write_text(
                "token_rate=10\nrequest_gap_sec=1.5\nrpm_limit=15\n",
                encoding="utf-8",
            )
            data = load_txt(p)
            self.assertEqual(data["token_rate"], 10)
            self.assertEqual(data["request_gap_sec"], 1.5)
            self.assertEqual(data["rpm_limit"], 15)
            cfg = load_config(p)
            self.assertEqual(cfg["token_rate"], 10)


if __name__ == "__main__":
    unittest.main()
