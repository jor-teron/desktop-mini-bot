"""LLM backends: Gemini (default) + Ollama. Stdlib only. No mock."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any, Protocol


class LLMClient(Protocol):
    def complete(self, messages: list[dict[str, str]], *, max_tokens: int, temperature: float) -> str: ...


def guess_url(goal: str) -> str | None:
    g = goal.strip()
    m = re.search(r"https?://[^\s]+", g, re.I)
    if m:
        return m.group(0).rstrip(".,)")
    gl = g.lower()
    if "google" in gl and any(w in gl for w in ("open", "go", "visit", "browse", "search")):
        return "https://www.google.com"
    m = re.search(r"\b([a-z0-9-]+\.[a-z]{2,})(/[^\s]*)?", gl)
    if m and any(w in gl for w in ("open", "go to", "visit", "browse", "navigate")):
        return "https://" + m.group(0)
    return None


class GeminiLLM:
    """Google Gemini generateContent API."""

    def __init__(self, api_key: str, model: str = "gemini-3.5-flash-lite") -> None:
        if not api_key or not api_key.strip():
            raise RuntimeError(
                "Missing Gemini api_key in config.txt. Get one at https://aistudio.google.com/apikey"
            )
        self.api_key = api_key.strip()
        self.model = model.strip() or "gemini-3.5-flash-lite"

    def complete(self, messages: list[dict[str, str]], *, max_tokens: int, temperature: float) -> str:
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        contents: list[dict[str, Any]] = []
        for m in messages:
            role = m.get("role", "user")
            if role == "system":
                continue
            gem_role = "model" if role == "assistant" else "user"
            contents.append({"role": gem_role, "parts": [{"text": m.get("content", "")}]})
        if not contents:
            contents = [{"role": "user", "parts": [{"text": ""}]}]

        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system_parts:
            body["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}

        import urllib.parse as up
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{up.quote(self.model, safe='')}:generateContent?key={up.quote(self.api_key)}"
        )
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:400]
            raise RuntimeError(f"Gemini HTTP {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Gemini request failed: {e}") from e

        try:
            parts = payload["candidates"][0]["content"]["parts"]
            texts = [p.get("text", "") for p in parts if "text" in p]
            return "\n".join(texts).strip()
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"unexpected Gemini response: {payload!r}") from e


class OllamaLLM:
    """OpenAI-compatible local Ollama."""

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "ollama"
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
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(
                f"Ollama HTTP {e.code}. Check model in config.txt (ollama list). {detail}"
            ) from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama request failed: {e}") from e
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"unexpected Ollama response: {payload!r}") from e


def make_llm(cfg: dict[str, Any]) -> LLMClient:
    provider = str(cfg.get("provider", "gemini")).strip().lower()
    model = str(cfg.get("model", "gemini-3.5-flash-lite"))
    if provider in {"ollama", "local"}:
        return OllamaLLM(
            str(cfg.get("ollama_base_url") or cfg.get("base_url") or "http://127.0.0.1:11434/v1"),
            str(cfg.get("ollama_api_key") or cfg.get("api_key") or "ollama"),
            model,
        )
    return GeminiLLM(str(cfg.get("api_key") or ""), model)
