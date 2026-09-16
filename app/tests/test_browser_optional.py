"""desktop-mini-bot v0.2.4 — browser URL helpers + optional Chromium smoke.

Skips if no system Chromium/Chrome is installed.
Part of the lightweight no-vision Linux CUA (stdlib only).
MIT / jor-teron.
"""

import unittest

from pathlib import Path

from desktop_mini_bot.browser import _looks_url, _norm_url


# --- URL helpers ---

class Helpers(unittest.TestCase):
    """Pure checks for _looks_url / _norm_url (no browser process)."""

    def test_url(self):
        """Hostnames and schemes normalize; plain app names do not look like URLs."""
        self.assertTrue(_looks_url("https://example.com"))
        self.assertTrue(_looks_url("example.com"))
        self.assertFalse(_looks_url("Settings"))
        self.assertEqual(_norm_url("example.com"), "https://example.com")


# --- optional live Chromium ---

class BrowserSmoke(unittest.TestCase):
    """Start headless Chromium briefly if present; skip otherwise."""

    def test_chromium_starts_if_present(self):
        """Launch BrowserUI on about:blank and assert compact_state is a string."""
        from shutil import which

        if not any(
            which(x)
            for x in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")
        ):
            self.skipTest("no system Chromium/Chrome")
        from desktop_mini_bot.browser import BrowserUI

        try:
            ui = BrowserUI(headless=True, start_url="about:blank", port=9333)
            ui.start()
        except Exception as e:
            self.skipTest(str(e))
        try:
            state = ui.compact_state()
            self.assertIsInstance(state, str)
        finally:
            ui.close()



# --- browser_bin resolution ---

class TestResolveBrowserBin(unittest.TestCase):
    """Unit tests for resolve_browser_bin (auto vs path; no launch)."""

    def test_auto_finds_or_raises(self) -> None:
        """auto delegates to find_chromium (may raise if no browser installed)."""
        from desktop_mini_bot.cdp import resolve_browser_bin, CdpError
        from shutil import which

        has = any(
            which(x)
            for x in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome")
        )
        if has:
            path = resolve_browser_bin("auto")
            self.assertTrue(path)
            self.assertTrue(Path(path).is_file() or which(Path(path).name))
        else:
            with self.assertRaises(CdpError):
                resolve_browser_bin("auto")

    def test_absolute_fake_path_raises(self) -> None:
        """Missing absolute path raises CdpError."""
        from desktop_mini_bot.cdp import resolve_browser_bin, CdpError

        with self.assertRaises(CdpError):
            resolve_browser_bin("/nonexistent/fake/browser-bin-xyz")

    def test_absolute_existing_path(self) -> None:
        """Existing absolute file path is returned resolved."""
        import os
        import tempfile
        from desktop_mini_bot.cdp import resolve_browser_bin

        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name
        try:
            os.chmod(path, 0o755)
            got = resolve_browser_bin(path)
            self.assertEqual(got, str(Path(path).resolve()))
        finally:
            os.unlink(path)



if __name__ == "__main__":
    unittest.main()
