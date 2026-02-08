from __future__ import annotations

import time


class AFKManager:
    """Manages periodic AFK breaks to avoid detection."""

    def __init__(self):
        self._last_afk_time: float = 0.0
        self._in_afk: bool = False

    def reset(self) -> None:
        """Reset AFK state (call when bot starts)."""
        self._last_afk_time = time.time()
        self._in_afk = False

    def should_start_afk(self, interval_minutes: int) -> bool:
        """Check if it's time to enter AFK mode."""
        if interval_minutes <= 0 or self._in_afk:
            return False
        return (time.time() - self._last_afk_time) >= (interval_minutes * 60)

    def finish_afk(self) -> None:
        """End AFK mode and reset the timer."""
        self._in_afk = False
        self._last_afk_time = time.time()
