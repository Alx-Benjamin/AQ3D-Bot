from __future__ import annotations

import random
import time
from collections.abc import Callable

import pyautogui


class RandomMover:
    """Handles random movement when no enemies are found."""

    def move(
        self,
        movement_keys: dict[str, bool],
        loops: int,
        jump_while_moving: bool,
        is_running: Callable[[], bool],
    ) -> None:
        """Perform random movement using the enabled WASD keys.

        Args:
            movement_keys: {"w": True, "a": True, ...} — which keys are enabled.
            loops: Number of movement bursts to perform.
            jump_while_moving: Whether to randomly press space during movement.
            is_running: Callable that returns False if the bot has been stopped.
        """
        keys = [k for k, enabled in movement_keys.items() if enabled]
        if not keys:
            time.sleep(1)
            return

        for _ in range(random.randint(1, loops)):
            if not is_running():
                break

            key = random.choice(keys)
            duration = random.uniform(0.15, 0.55)

            pyautogui.keyDown(key)

            if jump_while_moving:
                start = time.time()
                while time.time() - start < duration:
                    if random.random() < 0.1:
                        pyautogui.press("space")
                    time.sleep(0.05)
            else:
                time.sleep(duration)

            pyautogui.keyUp(key)
            time.sleep(random.uniform(0.05, 0.15))
