"""desktop-mini-bot v0.2.3 — minimal Chromium CDP client (stdlib only).

Raw WebSocket + HTTP to talk to --remote-debugging-port; no Playwright/pip.
Part of the lightweight no-vision Linux CUA (stdlib only).
MIT / jor-teron.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import ssl
import struct
import subprocess
import time
import urllib.request
from typing import Any
from urllib.parse import urlparse


class CdpError(RuntimeError):
    """CDP handshake, socket, or protocol failure."""
    pass


# --- WebSocket (client frames) ---

def _ws_connect(url: str, timeout: float = 10.0) -> socket.socket:
    """Open a TCP(/TLS) socket and complete the HTTP Upgrade to websocket."""
    u = urlparse(url)
    host, port = u.hostname or "127.0.0.1", u.port or (443 if u.scheme == "wss" else 80)
    path = u.path or "/"
    if u.query:
        path += "?" + u.query
    raw = socket.create_connection((host, port), timeout=timeout)
    sock: socket.socket = ssl.create_default_context().wrap_socket(raw, server_hostname=host) if u.scheme == "wss" else raw
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall(
        f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n".encode()
    )
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            raise CdpError("CDP websocket handshake failed")
        buf += chunk
    if b"101" not in buf.split(b"\r\n", 1)[0]:
        raise CdpError(f"CDP handshake rejected: {buf[:200]!r}")
    return sock


def _ws_send(sock: socket.socket, data: bytes) -> None:
    """Send a masked text frame (clients must mask per RFC 6455)."""
    mask = os.urandom(4)
    ln = len(data)
    hdr = bytearray([0x81])  # FIN + text opcode
    if ln < 126:
        hdr.append(0x80 | ln)
    elif ln < 65536:
        hdr.append(0x80 | 126)
        hdr.extend(struct.pack("!H", ln))
    else:
        hdr.append(0x80 | 127)
        hdr.extend(struct.pack("!Q", ln))
    hdr.extend(mask)
    sock.sendall(bytes(hdr) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))


def _ws_recv(sock: socket.socket) -> bytes:
    """Read one websocket frame payload; reply to pings; error on close."""
    def read(n: int) -> bytes:
        out = b""
        while len(out) < n:
            chunk = sock.recv(n - len(out))
            if not chunk:
                raise CdpError("CDP socket closed")
            out += chunk
        return out

    b1, b2 = read(2)
    masked = b2 & 0x80
    ln = b2 & 0x7F
    if ln == 126:
        ln = struct.unpack("!H", read(2))[0]
    elif ln == 127:
        ln = struct.unpack("!Q", read(8))[0]
    mask = read(4) if masked else b""
    payload = read(ln)
    if masked:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    opcode = b1 & 0x0F
    if opcode == 0x8:
        raise CdpError("CDP websocket closed")
    if opcode == 0x9:  # ping -> pong (reuse send; simplistic)
        _ws_send(sock, payload)
        return _ws_recv(sock)
    return payload


# --- CDP session ---

class Cdp:
    """One WebSocket session to a Chromium page target; sequential JSON-RPC calls."""

    def __init__(self, ws_url: str) -> None:
        self._sock = _ws_connect(ws_url)
        self._id = 0  # monotonically increasing request id

    def close(self) -> None:
        """Close the underlying socket (best-effort)."""
        try:
            self._sock.close()
        except Exception:
            pass

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Send a CDP method and wait for the matching id result (skip events)."""
        self._id += 1
        msg_id = self._id
        _ws_send(self._sock, json.dumps({"id": msg_id, "method": method, "params": params or {}}).encode())
        while True:
            data = json.loads(_ws_recv(self._sock).decode())
            if data.get("id") == msg_id:
                if "error" in data:
                    raise CdpError(str(data["error"]))
                return data.get("result")


# --- launch Chromium ---

def find_chromium() -> str:
    """Locate a system Chromium/Chrome binary on PATH."""
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome"):
        from shutil import which
        p = which(name)
        if p:
            return p
    raise CdpError("No Chromium/Chrome found (sudo apt install chromium)")


def launch_chromium(port: int = 9222, headless: bool = False, url: str = "about:blank") -> subprocess.Popen:
    """Start Chromium with remote debugging on port and a dedicated AI user-data-dir.

    Uses app/chrome-data/ only — never the user's personal Chrome profile.
    When not headless, adds --start-maximized for a full window on Linux.
    """
    from .paths import chrome_dir
    bin_path = find_chromium()
    profile = str(chrome_dir())
    args = [
        bin_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
    ]
    if headless:
        args += ["--headless=new", "--disable-gpu"]
    else:
        args.append("--start-maximized")
    args.append(url)
    return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_ws_url(port: int = 9222, timeout: float = 15.0) -> str:
    """Poll /json/list until a page target websocket URL appears (not browser-level)."""
    deadline = time.time() + timeout
    list_url = f"http://127.0.0.1:{port}/json/list"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(list_url, timeout=1) as r:
                tabs = json.loads(r.read().decode())
            for tab in tabs:
                if tab.get("type") == "page" and tab.get("webSocketDebuggerUrl"):
                    return tab["webSocketDebuggerUrl"]
            # No page yet — ask Chromium to open about:blank
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/json/new?about:blank", timeout=1).read()
            except Exception:
                pass
        except Exception:
            time.sleep(0.2)
            continue
        time.sleep(0.2)
    raise CdpError(f"Chromium page CDP not up on :{port}")
