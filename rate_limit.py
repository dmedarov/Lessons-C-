from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock

from fastapi import HTTPException, Request


@dataclass(frozen=True)
class RateLimitRule:
    attempts: int
    window_seconds: int


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, rule: RateLimitRule) -> None:
        now = time.monotonic()
        cutoff = now - rule.window_seconds

        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= rule.attempts:
                raise HTTPException(
                    status_code=429,
                    detail="Твърде много опити. Изчакай малко и опитай отново.",
                )
            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = InMemoryRateLimiter()


def client_ip(request: Request) -> str:
    if request.client:
        return request.client.host
    return "unknown"
