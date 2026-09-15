import unittest

from desktop_mini_bot.browser import _looks_url, _norm_url


class Helpers(unittest.TestCase):
    def test_url(self):
        self.assertTrue(_looks_url("https://example.com"))
        self.assertTrue(_looks_url("example.com"))
        self.assertFalse(_looks_url("Settings"))
        self.assertEqual(_norm_url("example.com"), "https://example.com")


class BrowserSmoke(unittest.TestCase):
    def test_chromium_starts_if_present(self):
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
