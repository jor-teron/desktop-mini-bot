"""CLI entry: python -m desktop_mini_bot"""

from __future__ import annotations

import argparse
import json
import sys

from .config import load_config
from .llm import make_llm, guess_url
from .loop import SYSTEM_BROWSER, run_loop
from .paths import config_path, ensure_config


def _start_url(args, cfg, goal: str) -> str:
    if args.url:
        return args.url
    guessed = guess_url(goal)
    if guessed:
        return guessed
    configured = (cfg.get("start_url") or "").strip()
    if configured and configured != "about:blank":
        return configured
    return "about:blank"


def main(argv: list[str] | None = None) -> int:
    ensure_config()
    p = argparse.ArgumentParser(
        prog="desktop-mini-bot",
        description="Lightweight no-vision Linux CUA (Gemini default, Ollama optional)",
    )
    p.add_argument("--ui", action="store_true", help="Local chat page (127.0.0.1)")
    p.add_argument("--port", type=int, default=8765, help="Chat UI port")
    p.add_argument("--goal", required=False, help="What to accomplish")
    p.add_argument("--config", default=None, help=f"config.txt (default: {config_path()})")
    p.add_argument("--browser", action="store_true", help="Control Chromium via CDP (always on for goals)")
    p.add_argument("--no-browser", action="store_true", help="Error out (fake UI removed)")
    p.add_argument("--headless", action="store_true", help="Browser without a visible window")
    p.add_argument("--url", default=None, help="Start URL (default: about:blank or guessed)")
    p.add_argument("--model", default=None, help="Override model id")
    p.add_argument("--provider", default=None, help="gemini | ollama")
    p.add_argument("--api-key", default=None, help="Override api_key (prefer config.txt)")
    args = p.parse_args(argv)

    cfg_path = args.config or str(config_path())

    if args.ui:
        from .ui_server import serve

        serve(port=args.port, config_path=cfg_path, open_browser=True)
        return 0

    if not args.goal:
        p.error("--goal is required unless --ui")

    if args.no_browser:
        print("error: dry-run/fake UI removed — use a real browser (--browser)", file=sys.stderr)
        return 1

    cfg = load_config(cfg_path)
    if args.model:
        cfg["model"] = args.model
    if args.provider:
        cfg["provider"] = args.provider
    if args.api_key:
        cfg["api_key"] = args.api_key

    try:
        llm = make_llm(cfg)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    def on_step(rec: dict) -> None:
        print(f"[{rec['step']}] {json.dumps(rec['action'], separators=(',', ':'))} -> {rec['result']}")

    browser = None
    steps: list = []
    try:
        from .browser import BrowserUI

        start = _start_url(args, cfg, args.goal)
        headless = bool(args.headless or cfg.get("headless", False))
        browser = BrowserUI(headless=headless, start_url=start)
        browser.start()
        print(f"browser: {start} (headless={headless})", flush=True)
        print(
            f"config: {cfg_path} provider={cfg.get('provider')} model={cfg.get('model')}",
            flush=True,
        )
        steps = run_loop(
            goal=args.goal,
            llm=llm,
            ui=browser,
            max_tokens=int(cfg["max_tokens"]),
            temperature=float(cfg["temperature"]),
            max_steps=int(cfg["max_steps"]),
            system_prompt=SYSTEM_BROWSER,
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
