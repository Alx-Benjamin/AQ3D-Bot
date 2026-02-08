from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from .skill import DEFAULT_SKILLS, NUM_SKILL_SLOTS, Skill


def _sanitize_filename(name: str) -> str:
    """Convert a profile name to a safe filename (alphanumeric, spaces, hyphens)."""
    safe = re.sub(r"[^\w\s\-]", "", name).strip()
    return safe if safe else "Default"


WAIT_STEP_INDEX = -1  # sentinel value for wait/pause steps


@dataclass
class RotationStep:
    """A single step in a combat rotation.

    skill_index 0-8 = press that skill slot.
    skill_index -1  = wait/pause for `wait_seconds`.
    """

    skill_index: int = 0
    wait_seconds: float = 0.0  # only used when skill_index == WAIT_STEP_INDEX

    @property
    def is_wait(self) -> bool:
        return self.skill_index == WAIT_STEP_INDEX

    def to_dict(self) -> dict:
        d: dict = {"skill_index": self.skill_index}
        if self.wait_seconds > 0:
            d["wait_seconds"] = self.wait_seconds
        return d

    @classmethod
    def from_dict(cls, data: dict) -> RotationStep:
        return cls(
            skill_index=data.get("skill_index", 0),
            wait_seconds=data.get("wait_seconds", 0.0),
        )


def _default_rotation() -> list[RotationStep]:
    """Default rotation: all 9 skill slots in order."""
    return [RotationStep(i) for i in range(NUM_SKILL_SLOTS)]


def _default_skills() -> list[Skill]:
    """Deep-copy the default skill list."""
    return [Skill(**s.__dict__) for s in DEFAULT_SKILLS]


def _slot_type_for_index(i: int) -> str:
    """Return the correct slot_type for a given skill slot index."""
    if i == 0:
        return "auto_attack"
    elif i <= 4:
        return "class"
    else:
        return "cross"


def _pad_skills(skills: list[Skill]) -> list[Skill]:
    """Ensure the skill list has exactly NUM_SKILL_SLOTS entries with correct slot types."""
    if len(skills) >= NUM_SKILL_SLOTS:
        skills = skills[:NUM_SKILL_SLOTS]
    else:
        for i in range(len(skills), NUM_SKILL_SLOTS):
            skills.append(Skill(**DEFAULT_SKILLS[i].__dict__))
    # Enforce correct slot_type based on position (handles imported profiles)
    for i, skill in enumerate(skills):
        skill.slot_type = _slot_type_for_index(i)
    return skills


@dataclass
class Profile:
    """Per-class profile storing skills, rotation, potions, loot, and combat preferences."""

    name: str = "Default"
    skills: list[Skill] = field(default_factory=_default_skills)

    # Rotation
    rotation: list[RotationStep] = field(default_factory=_default_rotation)
    delay_min: float = 0.1
    delay_max: float = 0.3

    # Combat settings
    potion_hotkey: str = "p"
    potion_health_threshold: int = 50
    collect_loot: bool = True
    loot_hotkey: str = "l"
    jump_while_attacking: bool = False
    stop_bot_on_death: bool = False
    run_back_after_death: bool = False
    run_back_seconds: int = 5
    target_enemy_names: list[str] = field(default_factory=list)

    # --- Serialization ---

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "skills": [s.to_dict() for s in self.skills],
            "rotation": [r.to_dict() for r in self.rotation],
            "delay_min": self.delay_min,
            "delay_max": self.delay_max,
            "potion_hotkey": self.potion_hotkey,
            "potion_health_threshold": self.potion_health_threshold,
            "collect_loot": self.collect_loot,
            "loot_hotkey": self.loot_hotkey,
            "jump_while_attacking": self.jump_while_attacking,
            "stop_bot_on_death": self.stop_bot_on_death,
            "run_back_after_death": self.run_back_after_death,
            "run_back_seconds": self.run_back_seconds,
            "target_enemy_names": self.target_enemy_names,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Profile:
        skills_data = data.get("skills", [])
        skills = [Skill.from_dict(s) for s in skills_data] if skills_data else _default_skills()
        skills = _pad_skills(skills)

        rotation_data = data.get("rotation", [])
        rotation = (
            [RotationStep.from_dict(r) for r in rotation_data]
            if rotation_data
            else _default_rotation()
        )

        return cls(
            name=data.get("name", "Default"),
            skills=skills,
            rotation=rotation,
            delay_min=data.get("delay_min", 0.1),
            delay_max=data.get("delay_max", 0.3),
            potion_hotkey=data.get("potion_hotkey", "p"),
            potion_health_threshold=data.get("potion_health_threshold", 50),
            collect_loot=data.get("collect_loot", True),
            loot_hotkey=data.get("loot_hotkey", "l"),
            jump_while_attacking=data.get("jump_while_attacking", False),
            stop_bot_on_death=data.get("stop_bot_on_death", False),
            run_back_after_death=data.get("run_back_after_death", False),
            run_back_seconds=data.get("run_back_seconds", 5),
            target_enemy_names=data.get("target_enemy_names", []),
        )

    # --- File Operations ---

    def _filepath(self, profiles_dir: str) -> str:
        return os.path.join(profiles_dir, f"{_sanitize_filename(self.name)}.json")

    def save(self, profiles_dir: str = "profiles") -> None:
        os.makedirs(profiles_dir, exist_ok=True)
        with open(self._filepath(profiles_dir), "w") as f:
            json.dump(self.to_dict(), f, indent=4)

    def delete(self, profiles_dir: str = "profiles") -> bool:
        path = self._filepath(profiles_dir)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def rename(self, new_name: str, profiles_dir: str = "profiles") -> None:
        old_path = self._filepath(profiles_dir)
        self.name = new_name
        new_path = self._filepath(profiles_dir)
        if os.path.exists(old_path) and old_path != new_path:
            os.rename(old_path, new_path)
        else:
            self.save(profiles_dir)

    def duplicate(self, new_name: str) -> Profile:
        data = self.to_dict()
        data["name"] = new_name
        return Profile.from_dict(data)

    @classmethod
    def load(cls, name: str, profiles_dir: str = "profiles") -> Profile:
        path = os.path.join(profiles_dir, f"{_sanitize_filename(name)}.json")
        if not os.path.exists(path):
            return cls(name=name)
        with open(path, "r") as f:
            return cls.from_dict(json.load(f))

    @classmethod
    def list_profiles(cls, profiles_dir: str = "profiles") -> list[str]:
        if not os.path.isdir(profiles_dir):
            return []
        names = []
        for filename in sorted(os.listdir(profiles_dir)):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(profiles_dir, filename), "r") as f:
                        data = json.load(f)
                    names.append(data.get("name", filename[:-5]))
                except (json.JSONDecodeError, KeyError):
                    names.append(filename[:-5])
        return names

    # --- Export / Import ---

    def export_to_file(self, path: str) -> None:
        """Export this profile to a standalone JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=4)

    @classmethod
    def import_from_file(cls, path: str) -> Profile:
        """Import a profile from a standalone JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)
