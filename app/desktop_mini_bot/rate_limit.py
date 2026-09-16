"""desktop-mini-bot v0.2.2 — LLM request pacing (gap, RPM, token_rate).

RateLimiter sleeps around llm.complete() so free-tier / local pacing stays polite.
Token pacing uses approx tokens = max(1, len(text)//4) (chars/4); does not stream-edit the API.
Part of the lightweight no-vision Linux CUA (stdlib only).
MIT / jor-teron.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Callable


# Approx tokens from completion text length (chars/4, at least 1).
def approx_tokens(text: str) -> int:
    """Estimate token count as max(1, len(text) // 4). Documented chars/4 heuristic."""
    return max(1, len(text) // 4)


# --- RateLimiter ---

class RateLimiter:
    """Enforce request_gap_sec, rpm_limit (sliding 60s), and post-reply token_rate pacing.

    Inject sleep/monotonic for unit tests. All limits treat 0 as unlimited / no pacing.
    """

    def __init__(
        self,
        *,
        token_rate: int = 0,
        request_gap_sec: float = 0.0,
        rpm_limit: int = 0,
        sleep: Callable[[float], None] | None = None,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        """Store limits; optional injectable clock/sleeper for tests."""
        self.token_rate = int(token_rate or 0)
        self.request_gap_sec = float(request_gap_sec or 0.0)
        self.rpm_limit = int(rpm_limit or 0)
        self._sleep = sleep or time.sleep
        self._monotonic = monotonic or time.monotonic
        self._last_request_at: float | None = None
        self._request_times: deque[float] = deque()

    # --- before LLM call ---

    def before_request(self) -> None:
        """Sleep for request_gap_sec and/or until under rpm_limit; record request time."""
        now = self._monotonic()

        # Minimum gap since previous request start
        if self.request_gap_sec > 0 and self._last_request_at is not None:
            wait = self.request_gap_sec - (now - self._last_request_at)
            if wait > 0:
                self._sleep(wait)
                now = self._monotonic()

        # Sliding 60s RPM window
        if self.rpm_limit > 0:
            window = 60.0
            while True:
                now = self._monotonic()
                while self._request_times and (now - self._request_times[0]) >= window:
                    self._request_times.popleft()
                if len(self._request_times) < self.rpm_limit:
                    break
                wait = window - (now - self._request_times[0])
                if wait > 0:
                    self._sleep(wait)
                else:
                    # oldest already expired; loop to re-prune
                    self._request_times.popleft()

        started = self._monotonic()
        self._last_request_at = started
        if self.rpm_limit > 0:
            self._request_times.append(started)

    # --- after LLM reply ---

    def after_response(self, text: str, *, started_at: float) -> None:
        """If token_rate > 0, sleep so elapsed >= approx_tokens(text) / token_rate."""
        if self.token_rate <= 0:
            return
        need = approx_tokens(text) / float(self.token_rate)
        elapsed = self._monotonic() - started_at
        wait = need - elapsed
        if wait > 0:
            self._sleep(wait)

    # --- wrap complete ---

    def call_complete(
        self,
        llm: object,
        messages: list,
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """before_request → llm.complete → after_response; return completion text."""
        self.before_request()
        started = self._monotonic()
        text = llm.complete(messages, max_tokens=max_tokens, temperature=temperature)  # type: ignore[attr-defined]
        self.after_response(text, started_at=started)
        return text
