"""desktop-mini-bot v0.2.4 — agent loop: short prompts, short JSON, last-3 history.

Asks the LLM for one action per step, applies it on a UI surface, until done or max_steps.
max_steps <= 0 means unlimited (Stop / Ctrl+C is the escape hatch).
Every llm.complete path (including schema repair) goes through RateLimiter when provided.
Part of the lightweight no-vision Linux CUA (stdlib only).
MIT / jor-teron.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Protocol

from .fake_ui import FakeUI
from .llm import LLMClient
from .rate_limit import RateLimiter
from .schema import SchemaError, parse_action, to_wire


# --- UI protocol ---

class UISurface(Protocol):
    """Anything the loop can observe (compact_state) and act on (apply)."""

    def compact_state(self) -> str: ...
    def apply(self, action: dict[str, Any]) -> str: ...


# --- system prompts ---

# Desktop-oriented prompt (used when FakeUI is the surface)
SYSTEM_DESKTOP = """You are desktop-mini-bot, a Linux desktop agent.
No screenshots. Reply with ONE JSON object only. No prose.
Actions (short keys):
launch_app: {"a":"launch_app","n":"<app>"}
open_url: {"a":"open_url","u":"<url>"}
focus_window: {"a":"focus_window","t":"<title>"}
find: {"a":"find","r":"<role>","n":"<name>"}
click: {"a":"click","ref":"<id>"}
type: {"a":"type","txt":"<text>","ref":"<id>?"}
done: {"a":"done","s":"<summary>"}
Prefer find then click. Keep output under 80 tokens."""

# Live Chromium / DOM agent prompt (production path)
SYSTEM_BROWSER = """You are a real computer-use agent controlling a live web browser (DOM only, no screenshots).
Reply with ONE JSON object only. No prose, no markdown.
Actions:
open_url: {"a":"open_url","u":"<url>"}
find: {"a":"find","r":"<role>","n":"<name>"}
click: {"a":"click","ref":"<id>"}
type: {"a":"type","txt":"<text>","ref":"<id>?"}
done: {"a":"done","s":"<summary>"}
Roles: button, link, textbox, searchbox, checkbox, combobox.
Use refs from state (e1, e2, …) or hit1 after find.
Work step-by-step toward the goal. Prefer open_url then find/type/click.
When the goal is finished, emit done. Keep each reply under ~100 tokens."""


# --- agent loop ---

def run_loop(
    *,
    goal: str,
    llm: LLMClient,
    ui: UISurface | None = None,
    max_tokens: int = 80,
    temperature: float = 0.1,
    max_steps: int = 12,
    system_prompt: str | None = None,
    on_step: Callable[[dict[str, Any]], None] | None = None,
    on_stats: Callable[[dict[str, Any]], None] | None = None,
    rate_limiter: RateLimiter | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> list[dict[str, Any]]:
    """Run the observe → LLM → parse → apply cycle until done, stop, or max_steps.

    max_steps <= 0 means no step cap (0 = unlimited). Stop / Ctrl+C is the escape hatch
    when there is no hard ceiling — prefer should_stop over inventing a soft emergency max.

    Returns a list of step records: {step, action (wire), result, raw}.
    Retries once if the first LLM reply fails schema validation.
    When rate_limiter is set, every complete (including repair) goes through it.
    Optional should_stop is checked before each step and before a repair complete.
    Optional on_stats receives RateLimiter.stats snapshots after each complete.
    """
    ui = ui or FakeUI()
    system = system_prompt or SYSTEM_DESKTOP
    history: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    limiter = rate_limiter or RateLimiter()
    # 0 / negative = unlimited; Stop / Ctrl+C (should_stop) is the escape hatch
    unlimited = max_steps <= 0
    step = 0

    def _emit_stats() -> None:
        if on_stats and limiter.stats is not None:
            on_stats(limiter.stats.as_dict(now=limiter._monotonic()))

    def _complete(messages: list[dict[str, str]]) -> str:
        """LLM complete via RateLimiter (gap / RPM / token_rate); then emit stats."""
        text = limiter.call_complete(
            llm, messages, max_tokens=max_tokens, temperature=temperature
        )
        _emit_stats()
        return text

    def _stopped() -> bool:
        return bool(should_stop and should_stop())

    while True:
        step += 1
        if not unlimited and step > max_steps:
            break
        if _stopped():
            break

        # Only last 3 wire actions — keeps the prompt tiny for slow models
        hist = history[-3:]
        user = (
            f"goal: {goal}\n"
            f"state: {ui.compact_state()}\n"
            f"history: {json.dumps(hist, separators=(',', ':'))}\n"
            "next action JSON:"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        raw = _complete(messages)
        if _stopped():
            break
        try:
            action = parse_action(raw)
        except (SchemaError, json.JSONDecodeError) as e:
            # One repair turn with the bad output echoed back
            if _stopped():
                break
            repair = (
                f"Invalid JSON ({e}). Reply with one valid action object only.\n"
                f"Your previous output was:\n{raw[:200]}"
            )
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": repair})
            raw = _complete(messages)
            if _stopped():
                break
            action = parse_action(raw)

        result = ui.apply(action)
        wire = to_wire(action)
        record = {"step": step, "action": wire, "result": result, "raw": raw.strip()}
        steps.append(record)
        history.append(wire)
        if on_step:
            on_step(record)
        if action["action"] == "done":
            break
    return steps
