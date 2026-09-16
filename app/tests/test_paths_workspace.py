"""desktop-mini-bot v0.2.4 — paths.workspace_dir and keep_browser_open defaults.

No live Chromium required.
Part of the lightweight no-vision Linux CUA (stdlib only).
MIT / jor-teron.
"""

import unittest
from pathlib import Path
from desktop_mini_bot.config import DEFAULTS, load_txt
from desktop_mini_bot.paths import chrome_dir, project_root, workspace_dir


# --- workspace / chrome paths ---

class TestWorkspacePaths(unittest.TestCase):
    """workspace_dir lives under project root; chrome-data is AI-only under app/."""

    def test_workspace_dir_under_project_root(self) -> None:
        """workspace_dir() returns <root>/workspace and creates it if missing."""
        root = project_root()
        ws = workspace_dir()
        self.assertEqual(ws, root / "workspace")
        self.assertTrue(ws.is_dir())
        self.assertEqual(ws.parent, root)

    def test_chrome_dir_under_app_not_home(self) -> None:
        """AI profile is app/chrome-data/, not ~/.config/chromium or similar."""
        d = chrome_dir()
        self.assertEqual(d, project_root() / "app" / "chrome-data")
        self.assertTrue(d.is_dir())
        home = Path.home()
        self.assertFalse(str(d).startswith(str(home / ".config")))


# --- keep_browser_open config ---

class TestKeepBrowserOpen(unittest.TestCase):
    """Config default and bool parsing for keep_browser_open."""

    def test_default_true(self) -> None:
        """DEFAULTS keep_browser_open is True."""
        self.assertIs(DEFAULTS["keep_browser_open"], True)

    def test_parse_bool(self) -> None:
        """load_txt coerces keep_browser_open=false to False."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "c.txt"
            p.write_text("keep_browser_open=false\n", encoding="utf-8")
            data = load_txt(p)
            self.assertIs(data["keep_browser_open"], False)

    def test_close_kill_process_signature(self) -> None:
        """BrowserUI.close accepts kill_process without launching Chromium."""
        from desktop_mini_bot.browser import BrowserUI

        ui = BrowserUI(headless=True)
        # No process started — close(kill_process=False) must not raise
        ui.close(kill_process=False)
        ui.close(kill_process=True)


if __name__ == "__main__":
    unittest.main()
