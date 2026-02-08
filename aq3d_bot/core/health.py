from __future__ import annotations

import time

import pyautogui

from .ocr import OCREngine


class HealthMonitor:
    """Monitors player health via OCR and handles potion usage."""

    def __init__(self, ocr: OCREngine):
        self._ocr = ocr
        self._last_potion_time: float = 0.0
        self._potion_cooldown: float = 1.0  # minimum seconds between potions

    def get_health_percentage(
        self, bbox: tuple[int, int, int, int]
    ) -> int | None:
        """Read the player's current health percentage.

        Returns 0-100 or None if OCR fails.
        """
        if not self._ocr.is_ready:
            return None
        return self._ocr.read_health_percentage(bbox)

    def use_potion_if_needed(
        self,
        health_bbox: tuple[int, int, int, int] | None,
        potion_hotkey: str,
        threshold: int,
    ) -> int | None:
        """Check health and use a potion if below threshold.

        Returns the current health percentage (or None if unreadable).
        """
        if not health_bbox or not potion_hotkey:
            return None

        health = self.get_health_percentage(health_bbox)
        if health is None:
            return None

        if health < threshold:
            now = time.time()
            if now - self._last_potion_time >= self._potion_cooldown:
                pyautogui.press(potion_hotkey)
                self._last_potion_time = now

        return health
