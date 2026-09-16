"""desktop-mini-bot v0.2.3 — agent loop with a stub LLM (no live network).

Uses FakeUI only; not a product mock path — production always uses real browser.
Part of the lightweight no-vision Linux CUA (stdlib only).
MIT / jor-teron.
"""

import unittest

from desktop_mini_bot.fake_ui import FakeUI
from desktop_mini_bot.loop import run_loop


# --- stub LLM ---

class StubLLM:
    """Feeds canned JSON replies in order; falls back to done when exhausted."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.i = 0

    def complete(self, messages, *, max_tokens: int, temperature: float) -> str:
        """Return the next canned reply (or a done action)."""
        if self.i >= len(self._replies):
            return '{"a":"done","s":"ok"}'
        r = self._replies[self.i]
        self.i += 1
        return r


# --- loop ---

class TestLoop(unittest.TestCase):
    """End-to-end dry loop: open_url then done."""

    def test_open_then_done(self) -> None:
        """Two-step stub run ends with wire action a=done."""
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
