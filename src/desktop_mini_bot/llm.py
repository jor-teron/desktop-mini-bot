"""OpenAI-compatible chat completions via urllib (stdlib only)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Protocol


class LLMClient(Protocol):
    def complete(self, messages: list[dict[str, str]], *, max_tokens: int, temperature: float) -> str: ...


class HttpLLM:
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def complete(self, messages: list[dict[str, str]], *, max_tokens: int, temperature: float) -> str:
        url = f"{self.base_url}/chat/completions"
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise RuntimeError(f"LLM request failed: {e}") from e
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"unexpected LLM response: {payload!r}") from e


class MockLLM:
    """Scripted actions so demos/tests work offline."""

    def __init__(self, goal: str = "") -> None:
        g = goal.lower()
        if "settings" in g:
            seq = [
                '{"a":"launch_app","n":"Settings"}',
                '{"a":"find","r":"button","n":"Save"}',
                '{"a":"click","ref":"b1"}',
                '{"a":"done","s":"Opened Settings and clicked Save"}',
            ]
        elif "save" in g:
            seq = [
                '{"a":"find","r":"button","n":"Save"}',
                '{"a":"click","ref":"b1"}',
                '{"a":"done","s":"Clicked Save"}',
            ]
        else:
            seq = [
                '{"a":"find","r":"button","n":"Save"}',
                '{"a":"click","ref":"b1"}',
                '{"a":"done","s":"Finished dry-run"}',
            ]
        self._seq = seq
        self._i = 0

    def complete(self, messages: list[dict[str, str]], *, max_tokens: int, temperature: float) -> str:
        if self._i >= len(self._seq):
            return '{"a":"done","s":"no more mock steps"}'
        # If last user message looks like a repair, still advance.
        out = self._seq[self._i]
        self._i += 1
        return out
