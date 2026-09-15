"""Minimal local chat UI — stdlib only. Models from Ollama."""

from __future__ import annotations

import json
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from .config import load_config, save_model
from .fake_ui import FakeUI
from .llm import HttpLLM, MockLLM, guess_url
from .loop import SYSTEM_BROWSER, run_loop
from .paths import project_root

CHAT = Path(__file__).with_name("static") / "chat.html"


def _demo() -> str:
    return (project_root() / "app" / "examples" / "demo.html").as_uri()


def _sse(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


def list_ollama_models(base_url: str) -> list[str]:
    # OpenAI-compatible root is .../v1 — tags API is on host root
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3]
    url = root + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            data = json.loads(r.read().decode())
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


def _start_url(goal: str, cfg: dict, browser: bool) -> str:
    guessed = guess_url(goal)
    if guessed:
        return guessed
    configured = (cfg.get("start_url") or "").strip()
    if configured and configured not in {"demo", "about:blank"}:
        return configured
    g = goal.lower()
    if browser and any(w in g for w in ("save", "demo", "settings")) and "http" not in g:
        return _demo()
    return configured or "about:blank"


def _run(goal: str, mock: bool, browser: bool, headless: bool, config: str | None, model: str | None, emit: Callable) -> None:
    cfg = load_config(config)
    if model:
        cfg["model"] = model
        try:
            save_model(model)
        except Exception:
            pass
    llm = MockLLM(goal=goal, browser=browser) if mock else HttpLLM(cfg["base_url"], cfg["api_key"], cfg["model"])
    br = None
    try:
        if browser:
            from .browser import BrowserUI
            start = _start_url(goal, cfg, True)
            br = BrowserUI(headless=headless or bool(cfg.get("headless")), start_url=start)
            br.start()
            ui, system = br, SYSTEM_BROWSER
            emit("info", {"message": f"browser: {start}"})
            emit("info", {"message": f"model={'mock' if mock else cfg.get('model')}"})
        else:
            ui, system = FakeUI(), None
        steps = run_loop(
            goal=goal, llm=llm, ui=ui,
            max_tokens=int(cfg["max_tokens"]), temperature=float(cfg["temperature"]),
            max_steps=int(cfg["max_steps"]), system_prompt=system,
            on_step=lambda r: emit("step", {"step": r["step"], "action": r["action"], "result": r["result"]}),
        )
        emit("done", {"message": "Done." if steps and steps[-1]["action"].get("a") == "done" else "Stopped.", "steps": len(steps)})
    except Exception as e:
        emit("error", {"message": str(e)})
    finally:
        if br:
            br.close()


def serve(host: str = "127.0.0.1", port: int = 8765, config_path: str | None = None, open_browser: bool = True) -> None:
    class H(BaseHTTPRequestHandler):
        def log_message(self, *_a):
            return

        def do_GET(self):  # noqa: N802
            path = urlparse(self.path).path
            if path in {"/", "/chat"}:
                body = CHAT.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path == "/api/models":
                cfg = load_config(config_path)
                models = list_ollama_models(str(cfg.get("base_url", "")))
                body = json.dumps({"models": models, "current": cfg.get("model", "")}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_error(404)

        def do_POST(self):  # noqa: N802
            if urlparse(self.path).path != "/api/run":
                self.send_error(404)
                return
            n = int(self.headers.get("Content-Length", 0))
            try:
                p = json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError:
                self.send_error(400)
                return
            goal = str(p.get("goal") or "").strip()
            if not goal:
                self.send_error(400)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            def emit(ev: str, data: dict) -> None:
                try:
                    self.wfile.write(_sse(ev, data))
                    self.wfile.flush()
                except BrokenPipeError:
                    pass

            _run(
                goal, bool(p.get("mock", True)), bool(p.get("browser", False)),
                bool(p.get("headless", False)), config_path,
                str(p["model"]) if p.get("model") else None, emit,
            )

    httpd = ThreadingHTTPServer((host, port), H)
    url = f"http://{host}:{port}/"
    print(f"chat UI: {url}  (Ctrl+C to stop)", flush=True)
    print(f"config: {config_path or (project_root() / 'config.txt')}", flush=True)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped", flush=True)
    finally:
        httpd.server_close()
