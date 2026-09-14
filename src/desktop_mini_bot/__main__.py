"""CLI entry: python -m desktop_mini_bot"""

from __future__ import annotations

import argparse
import json
import sys

from .config import load_config
from .llm import HttpLLM, MockLLM
from .loop import run_loop


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="desktop-mini-bot", description="Lightweight no-vision Linux CUA (dry-run)")
    p.add_argument("--goal", required=True, help="What to accomplish")
    p.add_argument("--config", default=None, help="Path to JSON config")
    p.add_argument("--dry-run", action="store_true", default=True, help="Print actions only (default)")
    p.add_argument("--mock-llm", action="store_true", help="Use scripted offline LLM")
    p.add_argument("--model", default=None, help="Override model id")
    p.add_argument("--base-url", default=None, help="Override OpenAI-compatible base URL")
    args = p.parse_args(argv)

    cfg = load_config(args.config)
    if args.model:
        cfg["model"] = args.model
    if args.base_url:
        cfg["base_url"] = args.base_url

    if args.mock_llm:
        llm = MockLLM(goal=args.goal)
    else:
        llm = HttpLLM(cfg["base_url"], cfg["api_key"], cfg["model"])

    def on_step(rec: dict) -> None:
        print(f"[{rec['step']}] {json.dumps(rec['action'], separators=(',', ':'))} -> {rec['result']}")

    try:
        steps = run_loop(
            goal=args.goal,
            llm=llm,
            max_tokens=int(cfg["max_tokens"]),
            temperature=float(cfg["temperature"]),
            max_steps=int(cfg["max_steps"]),
            dry_run=True,
            on_step=on_step,
        )
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if not steps or steps[-1]["action"].get("a") != "done":
        print("warning: stopped without done", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
