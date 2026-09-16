"""desktop-mini-bot v0.2.2 — RateLimiter unit tests (gap, RPM, token_rate).

Uses an injectable fake clock/sleeper — no real wall-clock waits.
Part of the lightweight no-vision Linux CUA (stdlib only).
MIT / jor-teron.
"""

from __future__ import annotations

import unittest

from desktop_mini_bot.rate_limit import RateLimiter, approx_tokens


# --- fake clock ---

class FakeClock:
    """Monotonic clock + sleep that advances time without wall delays."""

    def __init__(self, start: float = 1000.0) -> None:
        self.t = start
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.t

    def sleep(self, secs: float) -> None:
        self.sleeps.append(secs)
        self.t += secs


# --- approx_tokens ---

class TestApproxTokens(unittest.TestCase):
    """chars/4 heuristic."""

    def test_empty_is_one(self) -> None:
        self.assertEqual(approx_tokens(""), 1)

    def test_chars_div_4(self) -> None:
        self.assertEqual(approx_tokens("abcd"), 1)
        self.assertEqual(approx_tokens("a" * 40), 10)


# --- RateLimiter ---

class TestRateLimiter(unittest.TestCase):
    """Gap, RPM sliding window, and token_rate pacing with FakeClock."""

    def test_token_rate_zero_skips(self) -> None:
        """token_rate=0 must not sleep after a response."""
        clock = FakeClock()
        rl = RateLimiter(token_rate=0, sleep=clock.sleep, monotonic=clock.monotonic)
        rl.after_response("x" * 400, started_at=clock.t)
        self.assertEqual(clock.sleeps, [])

    def test_token_rate_paces(self) -> None:
        """Pace so elapsed >= approx_tokens / token_rate."""
        clock = FakeClock()
        rl = RateLimiter(token_rate=10, sleep=clock.sleep, monotonic=clock.monotonic)
        # 40 chars → 10 tokens → need 1.0s at 10 tok/s; API "took" 0.1s
        started = clock.t
        clock.t += 0.1
        rl.after_response("a" * 40, started_at=started)
        self.assertAlmostEqual(clock.sleeps[0], 0.9, places=5)

    def test_request_gap(self) -> None:
        """Second before_request sleeps remaining gap."""
        clock = FakeClock()
        rl = RateLimiter(request_gap_sec=5.0, sleep=clock.sleep, monotonic=clock.monotonic)
        rl.before_request()
        self.assertEqual(clock.sleeps, [])
        clock.t += 2.0  # only 2s elapsed
        rl.before_request()
        self.assertAlmostEqual(clock.sleeps[0], 3.0, places=5)

    def test_rpm_limit_waits(self) -> None:
        """When at rpm_limit, sleep until oldest request exits the 60s window."""
        clock = FakeClock()
        rl = RateLimiter(rpm_limit=2, sleep=clock.sleep, monotonic=clock.monotonic)
        rl.before_request()
        clock.t += 1.0
        rl.before_request()
        # two requests in window; third must wait ~59s from first
        t_before = clock.t
        rl.before_request()
        self.assertGreater(sum(clock.sleeps), 50.0)
        self.assertGreaterEqual(clock.t - t_before, 50.0)

    def test_unlimited_defaults_no_sleep(self) -> None:
        """All-zero defaults never sleep across several calls."""
        clock = FakeClock()
        rl = RateLimiter(sleep=clock.sleep, monotonic=clock.monotonic)
        for _ in range(5):
            rl.before_request()
            rl.after_response("hello", started_at=clock.t)
            clock.t += 0.01
        self.assertEqual(clock.sleeps, [])

    def test_call_complete_wires_llm(self) -> None:
        """call_complete invokes llm.complete and returns its text."""
        clock = FakeClock()

        class Stub:
            def complete(self, messages, *, max_tokens, temperature):
                return '{"a":"done","s":"ok"}'

        rl = RateLimiter(token_rate=0, sleep=clock.sleep, monotonic=clock.monotonic)
        out = rl.call_complete(Stub(), [], max_tokens=80, temperature=0.1)
        self.assertIn("done", out)


if __name__ == "__main__":
    unittest.main()
