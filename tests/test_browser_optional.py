import unittest

from desktop_mini_bot.browser import BrowserError, _looks_like_url, _normalize_url


class BrowserHelpers(unittest.TestCase):
    def test_url_helpers(self):
        self.assertTrue(_looks_like_url("https://example.com"))
        self.assertTrue(_looks_like_url("example.com"))
        self.assertFalse(_looks_like_url("Settings"))
        self.assertEqual(_normalize_url("example.com"), "https://example.com")


class BrowserIntegration(unittest.TestCase):
    def test_demo_page_click_save(self):
        try:
            from desktop_mini_bot.browser import BrowserUI
        except Exception as e:
            self.skipTest(str(e))
        from pathlib import Path
        from desktop_mini_bot.llm import MockLLM
        from desktop_mini_bot.loop import SYSTEM_BROWSER, run_loop

        demo = Path(__file__).resolve().parents[1] / "examples" / "demo.html"
        try:
            ui = BrowserUI(headless=True, start_url=demo.as_uri())
            ui.start()
        except BrowserError as e:
            self.skipTest(str(e))
        except Exception as e:
            self.skipTest(f"playwright/chromium unavailable: {e}")
        try:
            steps = run_loop(
                goal="click Save",
                llm=MockLLM(goal="click Save", browser=True),
                ui=ui,
                system_prompt=SYSTEM_BROWSER,
                max_steps=6,
            )
            self.assertEqual(steps[-1]["action"]["a"], "done")
            joined = " ".join(s["result"] for s in steps)
            self.assertTrue("click" in joined.lower() or "Save" in joined)
        finally:
            ui.close()


if __name__ == "__main__":
    unittest.main()
