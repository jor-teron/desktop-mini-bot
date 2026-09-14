import unittest

from desktop_mini_bot.llm import MockLLM
from desktop_mini_bot.loop import run_loop


class LoopTests(unittest.TestCase):
    def test_mock_save_goal(self):
        steps = run_loop(goal="click Save", llm=MockLLM(goal="click Save"))
        self.assertGreaterEqual(len(steps), 2)
        self.assertEqual(steps[-1]["action"]["a"], "done")
        actions = [s["action"]["a"] for s in steps]
        self.assertIn("click", actions)

    def test_settings_goal(self):
        steps = run_loop(
            goal="Open settings and click Save",
            llm=MockLLM(goal="Open settings and click Save"),
        )
        self.assertEqual(steps[-1]["action"]["a"], "done")
        self.assertEqual(steps[0]["action"]["a"], "launch_app")


if __name__ == "__main__":
    unittest.main()
