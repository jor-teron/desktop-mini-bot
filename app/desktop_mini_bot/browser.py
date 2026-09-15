"""Browser hands via system Chromium CDP — no pip / Playwright."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from .cdp import Cdp, CdpError, launch_chromium, wait_ws_url


def _norm_url(name: str) -> str:
    n = name.strip()
    if n.startswith(("http://", "https://", "file://", "about:")):
        return n
    return "https://" + n


def _looks_url(name: str) -> bool:
    n = name.strip()
    return n.startswith(("http://", "https://", "file://")) or ("." in n and " " not in n)


@dataclass
class BrowserUI:
    headless: bool = False
    start_url: str = "about:blank"
    port: int = 9222
    _proc: Any = field(default=None, repr=False)
    _cdp: Cdp | None = field(default=None, repr=False)
    _elements: list[dict[str, str]] = field(default_factory=list)
    _last_hits: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)

    def start(self) -> None:
        self._proc = launch_chromium(self.port, self.headless, self.start_url)
        self._cdp = Cdp(wait_ws_url(self.port))
        self._cdp.call("Runtime.enable")
        self._cdp.call("Page.enable")
        self._refresh()

    def close(self) -> None:
        if self._cdp:
            self._cdp.close()
            self._cdp = None
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except Exception:
                self._proc.kill()
        self._proc = None

    def __enter__(self) -> "BrowserUI":
        self.start()
        return self

    def __exit__(self, *a: Any) -> None:
        self.close()

    def _eval(self, expr: str) -> Any:
        assert self._cdp
        r = self._cdp.call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
        if r.get("exceptionDetails"):
            raise CdpError(str(r["exceptionDetails"]))
        return (r.get("result") or {}).get("value")

    def _refresh(self) -> None:
        script = r"""
(() => {
  const out = [];
  const add = (el, role) => {
    if (!el || out.length >= 40) return;
    let n = (el.getAttribute('aria-label') || el.innerText || el.value ||
             el.getAttribute('placeholder') || el.getAttribute('name') || '').trim()
             .replace(/\s+/g, ' ').slice(0, 60);
    if (!n && role !== 'textbox' && role !== 'searchbox') return;
    const i = out.length;
    el.setAttribute('data-dmb', String(i + 1));
    out.push({ref: 'e' + (i + 1), role, name: n || role});
  };
  document.querySelectorAll('a[href],button,input,textarea,select,[role="button"],[role="link"],[role="textbox"]').forEach(el => {
    let role = el.getAttribute('role');
    if (!role) {
      const t = el.tagName.toLowerCase();
      if (t === 'a') role = 'link';
      else if (t === 'button') role = 'button';
      else if (t === 'textarea') role = 'textbox';
      else if (t === 'select') role = 'combobox';
      else if (t === 'input') {
        const ty = (el.type || 'text').toLowerCase();
        role = ty === 'submit' || ty === 'button' ? 'button' : ty === 'checkbox' ? 'checkbox' : ty === 'search' ? 'searchbox' : 'textbox';
      } else role = t;
    }
    add(el, role);
  });
  return out;
})()
"""
        self._elements = list(self._eval(script) or [])

    def compact_state(self) -> str:
        try:
            title = self._eval("document.title") or ""
            url = self._eval("location.href") or ""
        except Exception:
            title, url = "", ""
        parts = [f"win={str(title)[:40]}", f"url={str(url)[:80]}"]
        for e in self._elements[:25]:
            parts.append(f"{e['ref']}:{e['role']}/{e['name']}")
        return " | ".join(parts)

    def apply(self, action: dict[str, Any]) -> str:
        a = action["action"]
        try:
            if a in {"open_url", "launch_app"}:
                raw = str(action.get("url") or action.get("name") or "")
                if a == "launch_app" and raw.lower() in {"browser", "chromium", "chrome"}:
                    url = self.start_url
                elif _looks_url(raw) or a == "open_url":
                    url = _norm_url(raw)
                else:
                    return f"launch_app ignored for non-URL '{raw}' (browser mode)"
                assert self._cdp
                self._cdp.call("Page.navigate", {"url": url})
                import time
                for _ in range(50):
                    time.sleep(0.1)
                    try:
                        ready = self._eval("document.readyState")
                        if ready in {"interactive", "complete"}:
                            break
                    except Exception:
                        pass
                self._refresh()
                msg = f"opened {self._eval('location.href')}"
            elif a == "focus_window":
                msg = f"focus_window no-op in browser ({action.get('title')})"
            elif a == "find":
                role, name = str(action["role"]), str(action["name"]).lower()
                self._refresh()
                hits = [e["ref"] for e in self._elements if e["role"] == role and name in (e["name"] or "").lower()]
                self._last_hits = hits
                msg = f"find ok {hits}" if hits else f"find miss {role}/{name}"
            elif a == "click":
                ref = str(action["ref"])
                if ref in {"hit", "hit1", "first"} and self._last_hits:
                    ref = self._last_hits[0]
                if ref not in {e["ref"] for e in self._elements} and self._last_hits:
                    ref = self._last_hits[0]
                n = ref[1:] if ref.startswith("e") else ref
                ok = self._eval(
                    f"""(() => {{ const el = document.querySelector('[data-dmb="{n}"]');
                    if (!el) return false; el.click(); return true; }})()"""
                )
                import time
                time.sleep(0.3)
                self._refresh()
                msg = f"clicked {ref}" if ok else f"click miss {ref}"
            elif a == "type":
                text = str(action["text"])
                ref = action.get("ref")
                if ref:
                    n = str(ref)[1:] if str(ref).startswith("e") else str(ref)
                    ok = self._eval(
                        f"""(() => {{ const el = document.querySelector('[data-dmb="{n}"]');
                        if (!el) return false; el.focus(); el.value = {json.dumps(text)};
                        el.dispatchEvent(new Event('input', {{bubbles:true}})); return true; }})()"""
                    )
                    msg = f"typed into {ref}: {text!r}" if ok else f"type miss {ref}"
                else:
                    msg = f"typed {text!r} (no ref)"
                self._refresh()
            elif a == "done":
                msg = f"done: {action.get('summary', '')}"
            else:
                msg = f"unknown {a}"
        except Exception as e:
            msg = f"error: {e}"
        self.log.append(msg)
        return msg


# Back-compat name used by older messages
BrowserError = CdpError
