"""desktop-mini-bot v0.2.4 — LLM backends: Gemini (default) + Ollama.

Stdlib urllib only; no mock/demo provider. API key comes from config.txt.
Part of the lightweight no-vision Linux CUA (stdlib only).
MIT / jor-teron.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any, Protocol


# --- protocol ---

class LLMClient(Protocol):
    """Anything that can complete a chat-style message list into a string."""

    def complete(self, messages: list[dict[str, str]], *, max_tokens: int, temperature: float) -> str: ...


# --- URL heuristics ---

def guess_url(goal: str) -> str | None:
    """Extract or infer a start URL from a natural-language goal, or None."""
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


# --- Gemini API ---

class GeminiLLM:
    """Google Gemini generateContent API (v1beta)."""

    def __init__(self, api_key: str, model: str = "gemini-3.5-flash-lite") -> None:
        """Require a non-empty api_key; default model is gemini-3.5-flash-lite."""
        if not api_key or not api_key.strip():
            raise RuntimeError(
                "Missing Gemini api_key in config.txt. Get one at https://aistudio.google.com/apikey"
            )
        self.api_key = api_key.strip()
        self.model = model.strip() or "gemini-3.5-flash-lite"
        self.last_usage: dict | None = None  # filled by complete() from usageMetadata

    def complete(self, messages: list[dict[str, str]], *, max_tokens: int, temperature: float) -> str:
        """Map OpenAI-style messages to Gemini contents + systemInstruction; return text."""
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        contents: list[dict[str, Any]] = []
        for m in messages:
            role = m.get("role", "user")
            if role == "system":
                continue
            # Gemini uses "model" where OpenAI uses "assistant"
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

        # Stash usage for RateLimiter / RunStats when present
        self.last_usage = None
        um = payload.get("usageMetadata") if isinstance(payload, dict) else None
        if isinstance(um, dict):
            self.last_usage = {
                "prompt_tokens": int(um.get("promptTokenCount") or 0),
                "completion_tokens": int(um.get("candidatesTokenCount") or 0),
                "total_tokens": int(um.get("totalTokenCount") or 0),
            }

        try:
            parts = payload["candidates"][0]["content"]["parts"]
            texts = [p.get("text", "") for p in parts if "text" in p]
            return "\n".join(texts).strip()
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"unexpected Gemini response: {payload!r}") from e


# --- Ollama (OpenAI-compatible) ---

class OllamaLLM:
    """Local Ollama via its OpenAI-compatible /v1/chat/completions endpoint."""

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        """base_url usually ends with /v1; api_key is ignored by Ollama but sent as Bearer."""
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "ollama"
        self.model = model
        self.last_usage: dict | None = None  # filled by complete() from usage if present

    def complete(self, messages: list[dict[str, str]], *, max_tokens: int, temperature: float) -> str:
        """POST chat completions; return the assistant message content."""
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
        # OpenAI-compat usage: prompt_tokens / completion_tokens
        self.last_usage = None
        usage = payload.get("usage") if isinstance(payload, dict) else None
        if isinstance(usage, dict):
            self.last_usage = {
                "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                "completion_tokens": int(usage.get("completion_tokens") or 0),
                "total_tokens": int(usage.get("total_tokens") or 0),
            }

        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"unexpected Ollama response: {payload!r}") from e


# --- factory ---

def make_llm(cfg: dict[str, Any]) -> LLMClient:
    """Build GeminiLLM or OllamaLLM from a loaded config dict (no mock)."""
    provider = str(cfg.get("provider", "gemini")).strip().lower()
    model = str(cfg.get("model", "gemini-3.5-flash-lite"))
    if provider in {"ollama", "local"}:
        return OllamaLLM(
            str(cfg.get("ollama_base_url") or cfg.get("base_url") or "http://127.0.0.1:11434/v1"),
            str(cfg.get("ollama_api_key") or cfg.get("api_key") or "ollama"),
            model,
        )
    return GeminiLLM(str(cfg.get("api_key") or ""), model)
