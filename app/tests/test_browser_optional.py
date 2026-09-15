import unittest

from desktop_mini_bot.browser import _looks_url, _norm_url


class Helpers(unittest.TestCase):
    def test_url(self):
        self.assertTrue(_looks_url("https://example.com"))
        self.assertTrue(_looks_url("example.com"))
        self.assertFalse(_looks_url("Settings"))
        self.assertEqual(_norm_url("example.com"), "https://example.com")


class BrowserIntegration(unittest.TestCase):
    def test_demo_click(self):
        from pathlib import Path
        from shutil import which
        if not any(which(x) for x in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")):
            self.skipTest("no system Chromium/Chrome")
        from desktop_mini_bot.browser import BrowserUI, CdpError
        from desktop_mini_bot.llm import MockLLM
        from desktop_mini_bot.loop import SYSTEM_BROWSER, run_loop

        demo = Path(__file__).resolve().parents[1] / "examples" / "demo.html"
        try:
            ui = BrowserUI(headless=True, start_url=demo.as_uri(), port=9333)
            ui.start()
        except Exception as e:
            self.skipTest(str(e))
        try:
            steps = run_loop(
                goal="click Save",
                llm=MockLLM(goal="click Save", browser=True),
                ui=ui,
                system_prompt=SYSTEM_BROWSER,
                max_steps=6,
            )
            self.assertEqual(steps[-1]["action"]["a"], "done")
        finally:
            ui.close()


if __name__ == "__main__":
    unittest.main()
