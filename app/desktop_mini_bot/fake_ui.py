"""desktop-mini-bot v0.2.4 — tiny fake UI for unit tests (no real desktop).

Implements the same compact_state / apply surface as BrowserUI for dry loop tests.
Not used by the production Gemini/browser path.
Part of the lightweight no-vision Linux CUA (stdlib only).
MIT / jor-teron.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# --- fake DOM ---

@dataclass
class Element:
    """A pretend UI control with a stable ref id."""

    ref: str
    role: str
    name: str
    value: str = ""


@dataclass
class FakeUI:
    """In-memory desktop stub: focused window, apps list, and a few elements."""

    focused: str = "Settings"
    apps: list[str] = field(default_factory=lambda: ["Settings", "Files", "Terminal"])
    elements: list[Element] = field(
        default_factory=lambda: [
            Element("b1", "button", "Save"),
            Element("b2", "button", "Cancel"),
            Element("t1", "text", "Name", value="desktop-mini-bot"),
            Element("c1", "checkbox", "Autostart"),
        ]
    )
    log: list[str] = field(default_factory=list)

    def snapshot(self) -> dict[str, Any]:
        """Full structured state (for debugging / richer callers)."""
        return {
            "focused": self.focused,
            "apps": list(self.apps),
            "elements": [
                {"ref": e.ref, "role": e.role, "name": e.name, "value": e.value}
                for e in self.elements
            ],
        }

    def compact_state(self) -> str:
        """Compressed catalog for the model (few tokens)."""
        lines = [f"win={self.focused}"]
        for e in self.elements:
            bit = f"{e.ref}:{e.role}/{e.name}"
            if e.value:
                bit += f"={e.value}"
            lines.append(bit)
        return " | ".join(lines)

    def apply(self, action: dict[str, Any]) -> str:
        """Apply one long-key action dict; append a result string to log and return it."""
        a = action["action"]
        if a == "launch_app":
            name = str(action["name"])
            if name not in self.apps:
                self.apps.append(name)
            self.focused = name
            msg = f"launched {name}"
        elif a == "open_url":
            url = str(action["url"])
            self.focused = url
            msg = f"opened {url}"
        elif a == "focus_window":
            title = str(action["title"])
            self.focused = title
            msg = f"focused {title}"
        elif a == "find":
            role, name = str(action["role"]), str(action["name"])
            hits = [e for e in self.elements if e.role == role and name.lower() in e.name.lower()]
            if not hits:
                msg = f"find miss {role}/{name}"
            else:
                msg = f"find ok {[e.ref for e in hits]}"
        elif a == "click":
            ref = str(action["ref"])
            el = next((e for e in self.elements if e.ref == ref), None)
            if el is None:
                msg = f"click miss {ref}"
            else:
                msg = f"clicked {ref} ({el.role}/{el.name})"
        elif a == "type":
            text = str(action["text"])
            ref = action.get("ref")
            if ref:
                el = next((e for e in self.elements if e.ref == ref), None)
                if el:
                    el.value = text
                    msg = f"typed into {ref}: {text!r}"
                else:
                    msg = f"type miss {ref}"
            else:
                msg = f"typed {text!r}"
        elif a == "done":
            msg = f"done: {action.get('summary', '')}"
        else:
            msg = f"unknown {a}"
        self.log.append(msg)
        return msg
