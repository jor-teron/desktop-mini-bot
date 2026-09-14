"""Dry-run agent loop: short prompts, short JSON, last-3 history."""

from __future__ import annotations

import json
from typing import Any, Callable

from .fake_ui import FakeUI
from .llm import LLMClient
from .schema import SchemaError, parse_action, to_wire

SYSTEM = """You are desktop-mini-bot, a Linux desktop agent.
No screenshots. Reply with ONE JSON object only. No prose.
Actions (short keys):
launch_app: {"a":"launch_app","n":"<app>"}
focus_window: {"a":"focus_window","t":"<title>"}
find: {"a":"find","r":"<role>","n":"<name>"}
click: {"a":"click","ref":"<id>"}
type: {"a":"type","txt":"<text>","ref":"<id>?"}
done: {"a":"done","s":"<summary>"}
Prefer find then click. Keep output under 80 tokens."""


def run_loop(
    *,
    goal: str,
    llm: LLMClient,
    ui: FakeUI | None = None,
    max_tokens: int = 80,
    temperature: float = 0.1,
    max_steps: int = 12,
    dry_run: bool = True,
    on_step: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    ui = ui or FakeUI()
    history: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []

    for step in range(1, max_steps + 1):
        hist = history[-3:]
        user = (
            f"goal: {goal}\n"
            f"state: {ui.compact_state()}\n"
            f"history: {json.dumps(hist, separators=(',', ':'))}\n"
            "next action JSON:"
        )
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ]
        raw = llm.complete(messages, max_tokens=max_tokens, temperature=temperature)
        try:
            action = parse_action(raw)
        except (SchemaError, json.JSONDecodeError) as e:
            repair = (
                f"Invalid JSON ({e}). Reply with one valid action object only.\n"
                f"Your previous output was:\n{raw[:200]}"
            )
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": repair})
            raw = llm.complete(messages, max_tokens=max_tokens, temperature=temperature)
            action = parse_action(raw)

        result = ui.apply(action) if dry_run or True else ui.apply(action)
        wire = to_wire(action)
        record = {"step": step, "action": wire, "result": result, "raw": raw.strip()}
        steps.append(record)
        history.append(wire)
        if on_step:
            on_step(record)
        if action["action"] == "done":
            break
    return steps
