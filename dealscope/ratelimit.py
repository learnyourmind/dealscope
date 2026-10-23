"""Small in-process sliding-window limiter (spec §5.5, §7 P0-8).

State is per process: on serverless or multi-worker hosts the effective limit is per
instance. Put an edge limiter in front before heavy public exposure.
"""

import re
import threading
import time
from collections import deque
from typing import Deque, Dict, Optional, Tuple

_UNITS = {"second": 1, "minute": 60, "hour": 3600}
MAX_KEYS = 10_000


def parse_rate(spec: str) -> Optional[Tuple[int, int]]:
    """'20/minute' -> (20, 60). Empty or malformed disables limiting."""
    match = re.fullmatch(r"\s*(\d{1,6})\s*/\s*(second|minute|hour)\s*", spec or "")
    if not match:
        return None
    return int(match.group(1)), _UNITS[match.group(2)]


class RateLimiter:
    def __init__(self, limit: int, window_s: int):
        self.limit, self.window_s = limit, window_s
        self._hits: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, now: Optional[float] = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            if len(self._hits) > MAX_KEYS:
                self._hits.clear()
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= self.window_s:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True
