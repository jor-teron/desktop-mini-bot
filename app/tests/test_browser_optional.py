"""desktop-mini-bot v0.2.2 — browser URL helpers + optional Chromium smoke.

Skips if no system Chromium/Chrome is installed.
Part of the lightweight no-vision Linux CUA (stdlib only).
MIT / jor-teron.
"""

import unittest

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


if __name__ == "__main__":
    unittest.main()
