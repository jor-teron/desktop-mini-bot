"""CLI entry: python -m desktop_mini_bot"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config
from .fake_ui import FakeUI
from .llm import HttpLLM, MockLLM
from .loop import SYSTEM_BROWSER, run_loop


def _demo_url() -> str:
    demo = Path(__file__).resolve().parents[2] / "examples" / "demo.html"
    return demo.as_uri()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="desktop-mini-bot",
        description="Lightweight no-vision Linux CUA (dry-run + browser DOM)",
    )
    p.add_argument("--goal", required=True, help="What to accomplish")
    p.add_argument("--config", default=None, help="Path to JSON config")
    p.add_argument("--dry-run", action="store_true", help="Fake UI only (no browser)")
    p.add_argument("--browser", action="store_true", help="Control a real Chromium window via DOM")
    p.add_argument("--headless", action="store_true", help="Browser without a visible window")
    p.add_argument("--url", default=None, help="Start URL (default: bundled demo.html in browser mode)")
    p.add_argument("--mock-llm", action="store_true", help="Use scripted offline LLM")
    p.add_argument("--model", default=None, help="Override model id")
    p.add_argument("--base-url", default=None, help="Override OpenAI-compatible base URL")
    args = p.parse_args(argv)

    cfg = load_config(args.config)
    if args.model:
        cfg["model"] = args.model
    if args.base_url:
        cfg["base_url"] = args.base_url

    use_browser = bool(args.browser)
    if not use_browser and not args.dry_run:
        # Default remains dry-run/fake UI for safety.
        use_browser = False

    if args.mock_llm:
        llm = MockLLM(goal=args.goal, browser=use_browser)
    else:
        llm = HttpLLM(cfg["base_url"], cfg["api_key"], cfg["model"])

    def on_step(rec: dict) -> None:
        print(f"[{rec['step']}] {json.dumps(rec['action'], separators=(',', ':'))} -> {rec['result']}")

    ui = None
    browser = None
    try:
        if use_browser:
            from .browser import BrowserUI

            start = args.url or cfg.get("start_url") or _demo_url()
            headless = bool(args.headless or cfg.get("headless", False))
            browser = BrowserUI(headless=headless, start_url=start)
            browser.start()
            ui = browser
            system = SYSTEM_BROWSER
            print(f"browser: {start} (headless={headless})", flush=True)
        else:
            ui = FakeUI()
            system = None

        steps = run_loop(
            goal=args.goal,
            llm=llm,
            ui=ui,
            max_tokens=int(cfg["max_tokens"]),
            temperature=float(cfg["temperature"]),
            max_steps=int(cfg["max_steps"]),
            system_prompt=system,
            on_step=on_step,
        )
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    finally:
        if browser is not None:
            browser.close()

    if not steps or steps[-1]["action"].get("a") != "done":
        print("warning: stopped without done", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
