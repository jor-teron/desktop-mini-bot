"""Unit test with a stub LLM — no mock product path, no live network."""

import unittest

from desktop_mini_bot.fake_ui import FakeUI
from desktop_mini_bot.loop import run_loop


class StubLLM:
    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.i = 0

    def complete(self, messages, *, max_tokens: int, temperature: float) -> str:
        if self.i >= len(self._replies):
            return '{"a":"done","s":"ok"}'
        r = self._replies[self.i]
        self.i += 1
        return r


class TestLoop(unittest.TestCase):
    def test_open_then_done(self) -> None:
        llm = StubLLM(
            [
                '{"a":"open_url","u":"https://example.com"}',
                '{"a":"done","s":"opened"}',
            ]
        )
        steps = run_loop(goal="open example", llm=llm, ui=FakeUI(), max_steps=5)
        self.assertEqual(steps[-1]["action"]["a"], "done")
        self.assertGreaterEqual(len(steps), 2)


if __name__ == "__main__":
    unittest.main()
