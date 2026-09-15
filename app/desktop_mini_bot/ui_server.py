"""Minimal local chat UI — stdlib only. Gemini default; Ollama optional."""

from __future__ import annotations

import json
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from .config import load_config, set_keys
from .llm import make_llm, guess_url
from .loop import SYSTEM_BROWSER, run_loop
from .paths import project_root

CHAT = Path(__file__).with_name("static") / "chat.html"

# Sensible Gemini model picks for the dropdown (online)
GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
]


def _sse(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


def list_ollama_models(base_url: str) -> list[str]:
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


def _start_url(goal: str, cfg: dict) -> str:
    guessed = guess_url(goal)
    if guessed:
        return guessed
    configured = (cfg.get("start_url") or "").strip()
    if configured and configured != "about:blank":
        return configured
    return "about:blank"


def _run(
    goal: str,
    headless: bool,
    config: str | None,
    model: str | None,
    provider: str | None,
    api_key: str | None,
    emit: Callable,
) -> None:
    cfg = load_config(config)
    updates: dict[str, str] = {}
    if provider:
        cfg["provider"] = provider
        updates["provider"] = provider
    if model:
        cfg["model"] = model
        updates["model"] = model
    if api_key is not None and api_key != "":
        cfg["api_key"] = api_key
        updates["api_key"] = api_key
    if updates:
        try:
            set_keys(updates)
        except Exception:
            pass

    try:
        llm = make_llm(cfg)
    except Exception as e:
        emit("error", {"message": str(e)})
        return

    br = None
    try:
        from .browser import BrowserUI

        start = _start_url(goal, cfg)
        br = BrowserUI(headless=headless or bool(cfg.get("headless")), start_url=start)
        br.start()
        emit("info", {"message": f"browser: {start}"})
        emit(
            "info",
            {
                "message": f"provider={cfg.get('provider')} model={cfg.get('model')}"
            },
        )
        steps = run_loop(
            goal=goal,
            llm=llm,
            ui=br,
            max_tokens=int(cfg["max_tokens"]),
            temperature=float(cfg["temperature"]),
            max_steps=int(cfg["max_steps"]),
            system_prompt=SYSTEM_BROWSER,
            on_step=lambda r: emit(
                "step",
                {"step": r["step"], "action": r["action"], "result": r["result"]},
            ),
        )
        emit(
            "done",
            {
                "message": "Done."
                if steps and steps[-1]["action"].get("a") == "done"
                else "Stopped.",
                "steps": len(steps),
            },
        )
    except Exception as e:
        emit("error", {"message": str(e)})
    finally:
        if br:
            br.close()


def serve(
    host: str = "127.0.0.1",
    port: int = 8765,
    config_path: str | None = None,
    open_browser: bool = True,
) -> None:
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
            if path == "/api/config":
                cfg = load_config(config_path)
                body = json.dumps(
                    {
                        "provider": cfg.get("provider", "gemini"),
                        "model": cfg.get("model", ""),
                        "has_api_key": bool(str(cfg.get("api_key") or "").strip()),
                        # never send the raw key to the page after first save — blank means keep
                        "api_key_hint": "••••••" if str(cfg.get("api_key") or "").strip() else "",
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path == "/api/models":
                cfg = load_config(config_path)
                provider = str(cfg.get("provider", "gemini")).lower()
                if provider in {"ollama", "local"}:
                    models = list_ollama_models(
                        str(cfg.get("ollama_base_url") or cfg.get("base_url") or "")
                    )
                else:
                    models = list(GEMINI_MODELS)
                    cur = str(cfg.get("model") or "")
                    if cur and cur not in models:
                        models = [cur] + models
                body = json.dumps(
                    {
                        "models": models,
                        "current": cfg.get("model", ""),
                        "provider": provider,
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_error(404)

        def do_POST(self):  # noqa: N802
            path = urlparse(self.path).path
            n = int(self.headers.get("Content-Length", 0))
            try:
                p = json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError:
                self.send_error(400)
                return

            if path == "/api/save-key":
                try:
                    updates: dict[str, str] = {}
                    if p.get("provider"):
                        updates["provider"] = str(p["provider"])
                    if p.get("model"):
                        updates["model"] = str(p["model"])
                    key = p.get("api_key")
                    if key is not None and str(key).strip() != "":
                        updates["api_key"] = str(key).strip()
                    if updates:
                        set_keys(updates)
                except Exception as e:
                    body = json.dumps({"ok": False, "error": str(e)}).encode()
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                body = b'{"ok":true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if path != "/api/run":
                self.send_error(404)
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

            api_key = p.get("api_key")
            if api_key == "" or api_key is None:
                api_key = None  # keep config.txt value
            _run(
                goal,
                bool(p.get("headless", False)),
                config_path,
                str(p["model"]) if p.get("model") else None,
                str(p["provider"]) if p.get("provider") else None,
                str(api_key) if api_key is not None else None,
                emit,
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
