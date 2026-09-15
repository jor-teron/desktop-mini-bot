import tempfile
import unittest
from pathlib import Path

from desktop_mini_bot.config import load_config, load_txt, set_keys
from desktop_mini_bot.llm import make_llm, guess_url


class TestConfig(unittest.TestCase):
    def test_set_keys_preserves_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.txt"
            p.write_text("provider=gemini\napi_key=secret\nmodel=gemini-3.5-flash-lite\n")
            set_keys({"model": "gemini-2.0-flash"}, p)
            data = load_txt(p)
            self.assertEqual(data["api_key"], "secret")
            self.assertEqual(data["model"], "gemini-2.0-flash")

    def test_make_llm_requires_key(self) -> None:
        with self.assertRaises(RuntimeError):
            make_llm({"provider": "gemini", "api_key": "", "model": "gemini-3.5-flash-lite"})

    def test_guess_url(self) -> None:
        self.assertEqual(guess_url("open google.com"), "https://www.google.com")


if __name__ == "__main__":
    unittest.main()
