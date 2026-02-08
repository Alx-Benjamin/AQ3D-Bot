from __future__ import annotations

import time
from typing import Callable

import pyautogui

from .ocr import OCREngine


class DeathHandler:
    """Detects player death (revive button) and handles revival + run-back."""

    def __init__(self, ocr: OCREngine):
        self._ocr = ocr

    def is_dead(self, revive_bbox: tuple[int, int, int, int] | None) -> bool:
        """Check if the revive button is visible on screen."""
        if not revive_bbox or not self._ocr.is_ready:
            return False
        return self._ocr.read_revive_text(revive_bbox)

    def click_revive(
        self,
        revive_bbox: tuple[int, int, int, int],
        delay_before: float = 5.0,
        is_running: Callable[[], bool] | None = None,
    ) -> None:
        """Wait, then click the center of the revive button region."""
        # Interruptible delay before clicking
        elapsed = 0.0
        while elapsed < delay_before:
            if is_running and not is_running():
                return
            time.sleep(min(0.2, delay_before - elapsed))
            elapsed += 0.2

        cx = revive_bbox[0] + (revive_bbox[2] - revive_bbox[0]) / 2
        cy = revive_bbox[1] + (revive_bbox[3] - revive_bbox[1]) / 2
        pyautogui.click(cx, cy)

        # Interruptible post-click delay
        elapsed = 0.0
        while elapsed < 3.0:
            if is_running and not is_running():
                return
            time.sleep(0.2)
            elapsed += 0.2

    def run_back(
        self,
        seconds: int,
        is_running: Callable[[], bool] | None = None,
    ) -> None:
        """Hold W to run back toward the combat area after reviving."""
        if seconds <= 0:
            return
        pyautogui.keyDown("w")
        try:
            elapsed = 0.0
            while elapsed < seconds:
                if is_running and not is_running():
                    break
                time.sleep(min(0.2, seconds - elapsed))
                elapsed += 0.2
        finally:
            pyautogui.keyUp("w")
