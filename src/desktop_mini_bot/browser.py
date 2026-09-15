"""Playwright DOM browser surface — no screenshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse


class BrowserError(RuntimeError):
    pass


def _require_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise BrowserError(
            "Playwright not installed. Run: ./install.sh --browser"
        ) from e
    return sync_playwright


def _looks_like_url(name: str) -> bool:
    n = name.strip()
    if n.startswith(("http://", "https://", "file://")):
        return True
    if "." in n and " " not in n and not n.startswith("."):
        return True
    return False


def _normalize_url(name: str) -> str:
    n = name.strip()
    if n.startswith(("http://", "https://", "file://")):
        return n
    return "https://" + n


@dataclass
class BrowserUI:
    """Real Chromium page driven by accessibility/DOM — never screenshots."""

    headless: bool = False
    start_url: str = "about:blank"
    _pw: Any = field(default=None, repr=False)
    _browser: Any = field(default=None, repr=False)
    _page: Any = field(default=None, repr=False)
    _refs: dict[str, Any] = field(default_factory=dict, repr=False)
    _elements: list[dict[str, str]] = field(default_factory=list)
    _last_hits: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)

    def start(self) -> None:
        sync_playwright = _require_playwright()
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page()
        self._page.goto(self.start_url, wait_until="domcontentloaded")
        self._refresh_elements()

    def close(self) -> None:
        try:
            if self._browser is not None:
                self._browser.close()
        finally:
            self._browser = None
            self._page = None
            if self._pw is not None:
                self._pw.stop()
                self._pw = None

    def __enter__(self) -> "BrowserUI":
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _refresh_elements(self) -> None:
        assert self._page is not None
        # Prefer role-based accessible nodes; fall back to common controls.
        script = """
() => {
  const out = [];
  const push = (el, role, name) => {
    if (!el || out.length >= 40) return;
    const r = role || el.getAttribute('role') || el.tagName.toLowerCase();
    let n = (name || el.getAttribute('aria-label') || el.innerText || el.value || el.getAttribute('placeholder') || el.getAttribute('name') || '').trim();
    n = n.replace(/\\s+/g, ' ').slice(0, 60);
    if (!n && r !== 'textbox' && r !== 'searchbox') return;
    out.push({role: r, name: n || r, tag: el.tagName.toLowerCase()});
  };
  document.querySelectorAll('a[href], button, input, textarea, select, [role="button"], [role="link"], [role="textbox"], [role="checkbox"], [role="menuitem"]').forEach(el => {
    let role = el.getAttribute('role');
    if (!role) {
      const t = el.tagName.toLowerCase();
      if (t === 'a') role = 'link';
      else if (t === 'button') role = 'button';
      else if (t === 'textarea') role = 'textbox';
      else if (t === 'select') role = 'combobox';
      else if (t === 'input') {
        const ty = (el.getAttribute('type') || 'text').toLowerCase();
        if (ty === 'submit' || ty === 'button') role = 'button';
        else if (ty === 'checkbox') role = 'checkbox';
        else if (ty === 'radio') role = 'radio';
        else if (ty === 'search') role = 'searchbox';
        else role = 'textbox';
      } else role = t;
    }
    push(el, role, null);
  });
  return out;
}
"""
        raw = self._page.evaluate(script)
        self._refs.clear()
        self._elements = []
        for i, item in enumerate(raw):
            ref = f"e{i+1}"
            # locator by role+name when possible
            role = item.get("role") or "generic"
            name = item.get("name") or ""
            self._elements.append({"ref": ref, "role": role, "name": name})
            try:
                if name and role in {
                    "button",
                    "link",
                    "textbox",
                    "searchbox",
                    "checkbox",
                    "radio",
                    "menuitem",
                    "combobox",
                }:
                    loc = self._page.get_by_role(role, name=name)
                elif role in {"textbox", "searchbox"}:
                    loc = self._page.locator("input, textarea").nth(i)
                else:
                    loc = self._page.locator("a, button, input, textarea, select").nth(i)
                self._refs[ref] = loc.first
            except Exception:
                continue

    def compact_state(self) -> str:
        assert self._page is not None
        title = ""
        url = ""
        try:
            title = (self._page.title() or "")[:40]
            url = self._page.url or ""
            host = urlparse(url).netloc or url[:40]
        except Exception:
            host = "?"
        parts = [f"win={title or host}", f"url={url[:80]}"]
        for e in self._elements[:25]:
            parts.append(f"{e['ref']}:{e['role']}/{e['name']}")
        return " | ".join(parts)

    def snapshot(self) -> dict[str, Any]:
        return {
            "url": self._page.url if self._page else "",
            "elements": list(self._elements),
        }

    def apply(self, action: dict[str, Any]) -> str:
        assert self._page is not None
        a = action["action"]
        try:
            if a == "launch_app":
                name = str(action["name"])
                if _looks_like_url(name) or name.lower() in {"browser", "chromium", "chrome"}:
                    url = self.start_url if name.lower() in {"browser", "chromium", "chrome"} else _normalize_url(name)
                    self._page.goto(url, wait_until="domcontentloaded")
                    self._refresh_elements()
                    msg = f"opened {self._page.url}"
                else:
                    msg = f"launch_app ignored for non-URL '{name}' (browser mode)"
            elif a == "open_url":
                url = str(action["url"])
                if not url.startswith(("http://", "https://", "file://", "about:")):
                    url = "https://" + url
                self._page.goto(url, wait_until="domcontentloaded")
                self._refresh_elements()
                msg = f"opened {self._page.url}"
            elif a == "focus_window":
                msg = f"focus_window no-op in browser ({action.get('title')})"
            elif a == "find":
                role, name = str(action["role"]), str(action["name"])
                self._refresh_elements()
                hits = [
                    e["ref"]
                    for e in self._elements
                    if e["role"] == role and name.lower() in (e["name"] or "").lower()
                ]
                self._last_hits = hits
                msg = f"find ok {hits}" if hits else f"find miss {role}/{name}"
            elif a == "click":
                ref = str(action["ref"])
                if ref in {"hit", "hit1", "first"} and self._last_hits:
                    ref = self._last_hits[0]
                loc = self._refs.get(ref)
                if loc is None:
                    self._refresh_elements()
                    loc = self._refs.get(ref)
                if loc is None and self._last_hits:
                    loc = self._refs.get(self._last_hits[0])
                    ref = self._last_hits[0]
                if loc is None:
                    # Last resort: role-name from action history not available; try Save button
                    try:
                        self._page.get_by_role("button", name="Save").click(timeout=5000)
                        self._page.wait_for_load_state("domcontentloaded")
                        self._refresh_elements()
                        msg = "clicked Save (fallback)"
                    except Exception:
                        msg = f"click miss {ref}"
                else:
                    loc.click(timeout=5000)
                    self._page.wait_for_load_state("domcontentloaded")
                    self._refresh_elements()
                    msg = f"clicked {ref}"
            elif a == "type":
                text = str(action["text"])
                ref = action.get("ref")
                if ref:
                    loc = self._refs.get(str(ref))
                    if loc is None:
                        self._refresh_elements()
                        loc = self._refs.get(str(ref))
                    if loc is None:
                        msg = f"type miss {ref}"
                    else:
                        loc.fill(text, timeout=5000)
                        msg = f"typed into {ref}: {text!r}"
                else:
                    self._page.keyboard.type(text)
                    msg = f"typed {text!r}"
                self._refresh_elements()
            elif a == "done":
                msg = f"done: {action.get('summary', '')}"
            else:
                msg = f"unknown {a}"
        except Exception as e:
            msg = f"error: {e}"
        self.log.append(msg)
        return msg
