from __future__ import annotations

import random
import time
from typing import Callable

import pyautogui

from ..models.profile import RotationStep, WAIT_STEP_INDEX
from ..models.skill import Skill
from .ocr import OCREngine


class TargetFinder:
    """Finds enemies by tab-targeting and reading the enemy name via OCR."""

    def __init__(self, ocr: OCREngine):
        self._ocr = ocr

    def find_target(
        self,
        enemy_name_bbox: tuple[int, int, int, int],
        filters: list[str],
        max_tabs: int = 10,
        is_running: Callable[[], bool] | None = None,
        log: Callable[[str, str], None] | None = None,
    ) -> str | None:
        """Tab-target through nearby enemies looking for a name match.

        Args:
            enemy_name_bbox: Screen region where the enemy name appears.
            filters: List of enemy name substrings to match (case-insensitive).
                     Empty list = accept any enemy.
            max_tabs: Maximum number of tab presses before giving up.
            is_running: Callable returning False if the bot has been stopped.
            log: Callable(message, level) for debug logging.

        Returns:
            The matched enemy name, or None if no match found.
        """
        lower_filters = [f.lower().strip() for f in filters if f.strip()]

        for i in range(max_tabs):
            if is_running and not is_running():
                return None

            pyautogui.press("tab")
            time.sleep(random.uniform(0.2, 0.4))

            if is_running and not is_running():
                return None

            name = self._ocr.read_enemy_name(enemy_name_bbox)

            if log:
                log(f"Tab {i+1}/{max_tabs}: OCR read = '{name or ''}'", "DEBUG")

            if not name:
                continue

            if not lower_filters or any(f in name.lower() for f in lower_filters):
                return name

        return None

    def is_target_alive(
        self, enemy_name_bbox: tuple[int, int, int, int]
    ) -> bool:
        """Check if a targeted enemy name is still visible."""
        return self._ocr.read_enemy_name(enemy_name_bbox) is not None


class SkillRotation:
    """Executes skills in a defined rotation sequence, waiting for cooldowns."""

    def __init__(self):
        self._index: int = 0
        self._last_use: dict[int, float] = {}  # skill_index > last use time

    def reset(self) -> None:
        """Reset rotation position and cooldown tracking."""
        self._index = 0
        self._last_use.clear()

    def execute_next_step(
        self,
        skills: list[Skill],
        rotation: list[RotationStep],
        delay_min: float,
        delay_max: float,
        is_running: Callable[[], bool],
    ) -> Skill | None:
        """Execute the next step in the rotation.

        Waits for the skill's cooldown if needed, then presses it.
        Wait steps sleep for the configured duration.
        Returns the skill that was used, or None if interrupted/skipped/wait.
        """
        if not rotation:
            return None

        step = rotation[self._index % len(rotation)]

        # Handle wait/pause steps
        if step.is_wait:
            self._advance(rotation)
            elapsed = 0.0
            while is_running() and elapsed < step.wait_seconds:
                time.sleep(min(0.1, step.wait_seconds - elapsed))
                elapsed += 0.1
            return None

        skill_idx = step.skill_index

        # Bounds check
        if skill_idx < 0 or skill_idx >= len(skills):
            self._advance(rotation)
            return None

        skill = skills[skill_idx]

        # Skip disabled skills
        if not skill.enabled:
            self._advance(rotation)
            return None

        # Wait for cooldown
        while is_running():
            remaining = self.get_cooldown_remaining(skill_idx, skill.cooldown)
            if remaining <= 0:
                break
            time.sleep(min(remaining, 0.1))

        if not is_running():
            return None

        # Press the skill
        pyautogui.press(skill.hotkey)
        self._last_use[skill_idx] = time.time()
        self._advance(rotation)

        # Random delay between steps
        time.sleep(random.uniform(delay_min, delay_max))
        return skill

    def get_cooldown_remaining(self, skill_index: int, cooldown: float) -> float:
        """Get seconds remaining on a skill's cooldown."""
        last = self._last_use.get(skill_index, 0.0)
        remaining = cooldown - (time.time() - last)
        return max(0.0, remaining)

    def get_cooldown_remaining_for_skill(self, skill_index: int, skills: list[Skill]) -> float:
        """Get seconds remaining given a skill index and skills list."""
        if skill_index < 0 or skill_index >= len(skills):
            return 0.0
        return self.get_cooldown_remaining(skill_index, skills[skill_index].cooldown)

    def _advance(self, rotation: list[RotationStep]) -> None:
        self._index = (self._index + 1) % len(rotation) if rotation else 0
