"""desktop-mini-bot v0.2.3 — short-JSON action schema (token-cheap).

Parses model output into validated long-key action dicts and compact wire form.
Part of the lightweight no-vision Linux CUA (stdlib only).
MIT / jor-teron.
"""

from __future__ import annotations

import json
from typing import Any

# Required long keys per action name (wire keys are short on purpose)
ACTION_KEYS = {
    "launch_app": ("name",),
    "open_url": ("url",),
    "focus_window": ("title",),
    "find": ("role", "name"),
    "click": ("ref",),
    "type": ("text",),  # optional ref handled below
    "done": ("summary",),
}

# Short wire key -> long key (models emit short keys to save tokens)
ALIASES = {
    "a": "action",
    "n": "name",
    "u": "url",
    "url": "url",
    "t": "title",
    "r": "role",
    "ref": "ref",
    "txt": "text",
    "text": "text",
    "s": "summary",
    "summary": "summary",
    "name": "name",
    "title": "title",
    "role": "role",
}


class SchemaError(ValueError):
    """Raised when model output is not a valid action object."""
    pass


# --- expand / validate ---

def _expand(raw: dict[str, Any]) -> dict[str, Any]:
    """Map short aliases to long keys; keep unknown keys as-is."""
    out: dict[str, Any] = {}
    for k, v in raw.items():
        key = ALIASES.get(k, k)
        out[key] = v
    if "action" not in out and "a" in raw:
        out["action"] = raw["a"]
    return out


def parse_action(text: str) -> dict[str, Any]:
    """Parse model output into a validated action dict with long keys.

    Strips markdown fences and surrounding prose; requires a known action
    and its mandatory fields.
    """
    text = text.strip()
    # Strip common fences / trailing chatter.
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                text = part
                break
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0 or end <= start:
        raise SchemaError("no JSON object found")
    raw = json.loads(text[start : end + 1])
    if not isinstance(raw, dict):
        raise SchemaError("action must be a JSON object")
    data = _expand(raw)
    action = data.get("action") or data.get("a")
    if not action or not isinstance(action, str):
        raise SchemaError("missing action")
    action = action.strip()
    if action not in ACTION_KEYS:
        raise SchemaError(f"unknown action: {action}")

    required = ACTION_KEYS[action]
    out: dict[str, Any] = {"action": action}
    for key in required:
        if key not in data or data[key] in (None, ""):
            raise SchemaError(f"{action} requires '{key}'")
        out[key] = data[key]
    if action == "type" and "ref" in data and data["ref"] not in (None, ""):
        out["ref"] = data["ref"]
    if action == "find":
        out["role"] = str(out["role"])
        out["name"] = str(out["name"])
    return out


def to_wire(action: dict[str, Any]) -> dict[str, Any]:
    """Compact short-key form for prompts and step logs."""
    a = action["action"]
    wire: dict[str, Any] = {"a": a}
    if a == "launch_app":
        wire["n"] = action["name"]
    elif a == "open_url":
        wire["u"] = action["url"]
    elif a == "focus_window":
        wire["t"] = action["title"]
    elif a == "find":
        wire["r"] = action["role"]
        wire["n"] = action["name"]
    elif a == "click":
        wire["ref"] = action["ref"]
    elif a == "type":
        wire["txt"] = action["text"]
        if "ref" in action:
            wire["ref"] = action["ref"]
    elif a == "done":
        wire["s"] = action["summary"]
    return wire
