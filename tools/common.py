"""Shared mechanism for the tool services: one HTTP client, one way to fail.

Rule of Repair: a tool that cannot answer returns 502/503/404 with the reason.
It never returns an empty success body.
"""
from __future__ import annotations

import os
import time

import httpx
from fastapi import HTTPException

UA = os.environ.get("TOOLS_USER_AGENT", "cargo-recovery-agent/0.1 (hackathon prototype)")
TIMEOUT = float(os.environ.get("TOOLS_HTTP_TIMEOUT", "15"))


def client() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT, headers={"User-Agent": UA}, follow_redirects=True)


def upstream_error(source: str, detail: str, status: int = 502) -> HTTPException:
    return HTTPException(status_code=status, detail={"source": source, "error": detail})


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class TTLCache:
    """Tiny per-process cache. Upstream feeds change slowly; do not hammer them."""

    def __init__(self, ttl_s: float) -> None:
        self.ttl = ttl_s
        self._d: dict[str, tuple[float, object]] = {}

    def get(self, key: str):
        hit = self._d.get(key)
        if hit and time.time() - hit[0] < self.ttl:
            return hit[1]
        return None

    def put(self, key: str, value: object) -> None:
        self._d[key] = (time.time(), value)
