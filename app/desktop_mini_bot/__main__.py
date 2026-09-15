"""CLI entry: python -m desktop_mini_bot"""

from __future__ import annotations

import argparse
import json
import sys

from .config import load_config
from .fake_ui import FakeUI
from .llm import HttpLLM, MockLLM, guess_url
from .loop import SYSTEM_BROWSER, run_loop
from .paths import config_path, ensure_config, project_root


def _demo_url() -> str:
    return (project_root() / "app" / "examples" / "demo.html").as_uri()


def _start_url(args, cfg, goal: str) -> str:
    if args.url:
        return args.url
    guessed = guess_url(goal)
    if guessed:
        return guessed
    configured = (cfg.get("start_url") or "").strip()
    if configured and configured not in {"demo", "about:blank"}:
        return configured
    g = goal.lower()
    if any(w in g for w in ("save", "demo", "settings")) and "http" not in g:
        return _demo_url()
    return configured or "about:blank"


def main(argv: list[str] | None = None) -> int:
    ensure_config()
    p = argparse.ArgumentParser(
        prog="desktop-mini-bot",
        description="Lightweight no-vision Linux CUA (project-local config)",
    )
    p.add_argument("--ui", action="store_true", help="Tiny local chat page (127.0.0.1)")
    p.add_argument("--port", type=int, default=8765, help="Chat UI port")
    p.add_argument("--goal", required=False, help="What to accomplish")
    p.add_argument("--config", default=None, help=f"config.txt (default: {config_path()})")
    p.add_argument("--dry-run", action="store_true", help="Fake UI only (no browser)")
    p.add_argument("--browser", action="store_true", help="Control real Chromium via CDP")
    p.add_argument("--headless", action="store_true", help="Browser without a visible window")
    p.add_argument("--url", default=None, help="Start URL (default: about:blank or guessed from goal)")
    p.add_argument("--mock-llm", action="store_true", help="Use scripted offline LLM")
    p.add_argument("--model", default=None, help="Override model id")
    p.add_argument("--base-url", default=None, help="Override OpenAI-compatible base URL")
    args = p.parse_args(argv)

    cfg_path = args.config or str(config_path())

    if args.ui:
        from .ui_server import serve
        serve(port=args.port, config_path=cfg_path, open_browser=True)
        return 0

    if not args.goal:
        p.error("--goal is required unless --ui")

    cfg = load_config(cfg_path)
    if args.model:
        cfg["model"] = args.model
    if args.base_url:
        cfg["base_url"] = args.base_url

    use_browser = bool(args.browser)
    llm = MockLLM(goal=args.goal, browser=use_browser) if args.mock_llm else HttpLLM(
        cfg["base_url"], cfg["api_key"], cfg["model"]
    )

    def on_step(rec: dict) -> None:
        print(f"[{rec['step']}] {json.dumps(rec['action'], separators=(',', ':'))} -> {rec['result']}")

    browser = None
    steps: list = []
    try:
        if use_browser:
            from .browser import BrowserUI
            start = _start_url(args, cfg, args.goal)
            headless = bool(args.headless or cfg.get("headless", False))
            browser = BrowserUI(headless=headless, start_url=start)
            browser.start()
            ui, system = browser, SYSTEM_BROWSER
            print(f"browser: {start} (headless={headless})", flush=True)
            print(f"config: {cfg_path} model={cfg.get('model')}", flush=True)
        else:
            ui, system = FakeUI(), None

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
