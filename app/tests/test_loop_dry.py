"""desktop-mini-bot v0.2.4 — agent loop with a stub LLM (no live network).

Uses FakeUI only; not a product mock path — production always uses real browser.
Covers max_steps=0 unlimited, max_steps=1 cap, and should_stop abort.
Part of the lightweight no-vision Linux CUA (stdlib only).
MIT / jor-teron.
"""

import unittest

from desktop_mini_bot.fake_ui import FakeUI
from desktop_mini_bot.loop import run_loop
from desktop_mini_bot.rate_limit import RateLimiter, RunStats


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
    """End-to-end dry loop: open_url then done; caps; stop; stats."""

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

    def test_max_steps_zero_unlimited_until_done(self) -> None:
        """max_steps=0 runs until done (stub dones on step 2) — not an empty loop."""
        llm = StubLLM(
            [
                '{"a":"open_url","u":"https://example.com"}',
                '{"a":"done","s":"opened"}',
            ]
        )
        steps = run_loop(goal="open example", llm=llm, ui=FakeUI(), max_steps=0)
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[-1]["action"]["a"], "done")
        self.assertEqual(llm.i, 2)

    def test_max_steps_one_stops_without_done(self) -> None:
        """max_steps=1 stops after one action even if not done."""
        llm = StubLLM(
            [
                '{"a":"open_url","u":"https://example.com"}',
                '{"a":"done","s":"opened"}',
            ]
        )
        steps = run_loop(goal="open example", llm=llm, ui=FakeUI(), max_steps=1)
        self.assertEqual(len(steps), 1)
        self.assertNotEqual(steps[-1]["action"]["a"], "done")

    def test_should_stop_aborts_mid_loop(self) -> None:
        """should_stop True after first step aborts before further completes."""
        llm = StubLLM(
            [
                '{"a":"open_url","u":"https://example.com"}',
                '{"a":"open_url","u":"https://example.org"}',
                '{"a":"done","s":"opened"}',
            ]
        )
        calls = {"n": 0}

        def should_stop() -> bool:
            # Stop once we have completed the first step (checked at start of step 2)
            return calls["n"] >= 1

        def on_step(_rec: dict) -> None:
            calls["n"] += 1

        steps = run_loop(
            goal="open",
            llm=llm,
            ui=FakeUI(),
            max_steps=10,
            should_stop=should_stop,
            on_step=on_step,
        )
        self.assertEqual(len(steps), 1)
        self.assertEqual(llm.i, 1)

    def test_stats_increment_via_rate_limiter(self) -> None:
        """RunStats.requests / tokens bump on each complete."""
        llm = StubLLM(
            [
                '{"a":"open_url","u":"https://example.com"}',
                '{"a":"done","s":"opened"}',
            ]
        )
        limiter = RateLimiter(stats=RunStats())
        seen: list[dict] = []
        steps = run_loop(
            goal="open",
            llm=llm,
            ui=FakeUI(),
            max_steps=5,
            rate_limiter=limiter,
            on_stats=lambda s: seen.append(dict(s)),
        )
        self.assertEqual(len(steps), 2)
        self.assertIsNotNone(limiter.stats)
        self.assertEqual(limiter.stats.requests, 2)
        self.assertGreater(limiter.stats.tokens_in, 0)
        self.assertGreater(limiter.stats.tokens_out, 0)
        self.assertTrue(limiter.stats.tokens_est)
        self.assertGreaterEqual(len(seen), 2)


if __name__ == "__main__":
    unittest.main()
