"""Migrate old settings formats to the new split (GlobalSettings + Profile) format.

Handles two known legacy schemas:
  - v1: flat settings.json with skill_keys/skill_cooldowns/skill_enabled arrays
  - v0: profiles/default.json with potion_hotkeys array, 10 skills, attack_delay
"""

from __future__ import annotations

import json
import os
import shutil

from .profile import Profile, RotationStep, _default_rotation
from .settings import GlobalSettings
from .skill import NUM_SKILL_SLOTS, Skill


# Slot type mapping for old skill indices
_OLD_SLOT_TYPES = [
    "auto_attack",  # 0: Basic Attack
    "class",        # 1-4: Class Skills
    "class",
    "class",
    "class",
    "cross",        # 5-8: Cross Skills
    "cross",
    "cross",
    "cross",
]


def needs_migration(settings_path: str = "settings.json", profiles_dir: str = "profiles") -> bool:
    """Check if migration is needed (old settings exist but no new-format profiles)."""
    if not os.path.exists(settings_path):
        return False

    # If the profiles directory already has new-format profiles, skip
    if os.path.isdir(profiles_dir):
        for f in os.listdir(profiles_dir):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(profiles_dir, f), "r") as fh:
                        data = json.load(fh)
                    # New-format profiles have a "skills" key with dicts that have slot_type
                    if "skills" in data and isinstance(data["skills"], list):
                        if data["skills"] and isinstance(data["skills"][0], dict):
                            if "slot_type" in data["skills"][0]:
                                return False
                except Exception:
                    continue

    # Check if settings.json is old format (has skill_keys instead of new structure)
    try:
        with open(settings_path, "r") as f:
            data = json.load(f)
        return "skill_keys" in data or "health_box" in data
    except Exception:
        return False


def migrate(settings_path: str = "settings.json", profiles_dir: str = "profiles") -> tuple[GlobalSettings, Profile]:
    """Migrate old settings to new format.

    Returns the new (GlobalSettings, default Profile).
    Backs up the old settings file.
    """
    with open(settings_path, "r") as f:
        old = json.load(f)

    # Detect which schema variant we have
    if "potion_hotkeys" in old:
        settings, profile = _migrate_v0(old)
    else:
        settings, profile = _migrate_v1(old)

    # Also check for old-format profiles/default.json
    old_profile_path = os.path.join(profiles_dir, "default.json")
    if os.path.exists(old_profile_path):
        try:
            with open(old_profile_path, "r") as f:
                old_profile_data = json.load(f)
            if "potion_hotkeys" in old_profile_data or "skill_keys" in old_profile_data:
                _, alt_profile = _migrate_v0(old_profile_data)
                # Merge: prefer the alt profile's skill data if it has more skills
                if len(alt_profile.skills) > len(profile.skills):
                    profile = alt_profile
                # Backup old profile
                shutil.copy2(old_profile_path, old_profile_path + ".v0.bak")
        except Exception:
            pass

    # Save new format
    settings.save(settings_path + ".new")
    profile.save(profiles_dir)

    # Backup old and swap
    backup_path = settings_path + ".v1.bak"
    if not os.path.exists(backup_path):
        shutil.copy2(settings_path, backup_path)
    os.replace(settings_path + ".new", settings_path)

    return settings, profile


def _build_skills(old: dict) -> list[Skill]:
    """Build a list of Skill objects from old format arrays."""
    skill_keys = old.get("skill_keys", [])
    skill_cooldowns = old.get("skill_cooldowns", [])
    skill_enabled = old.get("skill_enabled", [])

    skill_names = [
        "Auto Attack", "Class Skill 1", "Class Skill 2", "Class Skill 3",
        "Class Skill 4", "Cross Skill 1", "Cross Skill 2", "Cross Skill 3",
        "Cross Skill 4",
    ]

    skills = []
    count = min(len(skill_keys), NUM_SKILL_SLOTS)
    for i in range(count):
        slot_type = _OLD_SLOT_TYPES[i] if i < len(_OLD_SLOT_TYPES) else "class"
        skills.append(Skill(
            name=skill_names[i] if i < len(skill_names) else f"Skill {i}",
            hotkey=skill_keys[i] if i < len(skill_keys) else str(i + 1),
            cooldown=float(skill_cooldowns[i]) if i < len(skill_cooldowns) else 0.0,
            enabled=skill_enabled[i] if i < len(skill_enabled) else True,
            slot_type=slot_type,
        ))

    return skills


def _build_rotation(skills: list[Skill]) -> list[RotationStep]:
    """Build a default rotation from enabled skills."""
    rotation = [RotationStep(i) for i in range(len(skills)) if skills[i].enabled]
    return rotation if rotation else _default_rotation()


def _migrate_v1(old: dict) -> tuple[GlobalSettings, Profile]:
    """Migrate v1 format (flat settings.json with skill_keys arrays)."""
    settings = GlobalSettings(
        enemy_name_box=_to_tuple(old.get("health_box"), 4),
        player_health_box=_to_tuple(old.get("player_health_box"), 4),
        menu_close_point=_to_tuple(old.get("menu_close_location"), 2),
        revive_box=_to_tuple(old.get("detect_revive_box"), 4),
        movement_keys=old.get("movement_keys", {"w": True, "a": True, "s": True, "d": True}),
        movement_loops=old.get("movement_loops", 5),
        jump_while_moving=old.get("jump_while_moving", False),
        no_enemy_timeout_minutes=old.get("no_enemy_timeout_minutes", 5),
        max_runtime_hours=old.get("max_runtime_hours", 0),
        afk_interval_minutes=old.get("afk_interval_minutes", 0),
        afk_duration_minutes=old.get("afk_duration_minutes", 0),
        focus_aq3d_enabled=old.get("focus_aq3d_enabled", True),
    )

    skills = _build_skills(old)
    rotation = _build_rotation(skills)

    profile = Profile(
        name="Default",
        skills=skills,
        rotation=rotation,
        potion_hotkey=old.get("potion_hotkey", "p"),
        potion_health_threshold=old.get("potion_health_threshold", 50),
        collect_loot=old.get("collect_loot", True),
        loot_hotkey=old.get("loot_hotkey", "l"),
        jump_while_attacking=old.get("jump_while_attacking", False),
        stop_bot_on_death=old.get("stop_bot_on_death", False),
        run_back_after_death=old.get("run_back_after_death", False),
        run_back_seconds=old.get("run_back_seconds", 5),
        target_enemy_names=old.get("target_enemy_names_list", []),
    )

    return settings, profile


def _migrate_v0(old: dict) -> tuple[GlobalSettings, Profile]:
    """Migrate v0 format (profiles/default.json with potion arrays, 10 skills)."""
    settings = GlobalSettings(
        enemy_name_box=_to_tuple(old.get("health_box"), 4),
        player_health_box=_to_tuple(old.get("player_health_box"), 4),
        menu_close_point=_to_tuple(old.get("menu_close_location"), 2),
        revive_box=_to_tuple(old.get("detect_revive_box"), 4),
        no_enemy_timeout_minutes=old.get("no_enemy_timeout_minutes", 5),
        max_runtime_hours=old.get("max_runtime_hours", 0),
        afk_interval_minutes=old.get("afk_interval_minutes", 0),
        afk_duration_minutes=old.get("afk_duration_minutes", 0),
        focus_aq3d_enabled=old.get("focus_aq3d_enabled", True),
    )

    skills = _build_skills(old)
    rotation = _build_rotation(skills)

    # Use first enabled potion hotkey
    potion_hotkeys = old.get("potion_hotkeys", ["p"])
    potion_enabled = old.get("potion_enabled", [True])
    potion_thresholds = old.get("potion_health_thresholds", [50])
    potion_hotkey = "p"
    potion_threshold = 50
    for idx, enabled in enumerate(potion_enabled):
        if enabled and idx < len(potion_hotkeys) and potion_hotkeys[idx]:
            potion_hotkey = potion_hotkeys[idx]
            potion_threshold = potion_thresholds[idx] if idx < len(potion_thresholds) else 50
            break

    profile = Profile(
        name="Default",
        skills=skills,
        rotation=rotation,
        potion_hotkey=potion_hotkey,
        potion_health_threshold=potion_threshold,
        collect_loot=True,
        loot_hotkey=old.get("loot_hotkey", "l"),
        stop_bot_on_death=old.get("stop_bot_on_death", False),
        target_enemy_names=old.get("target_enemy_names", []),
    )

    return settings, profile


def _to_tuple(val, length: int):
    """Convert a list to a tuple of the expected length, or None."""
    if val and isinstance(val, (list, tuple)) and len(val) == length:
        return tuple(val)
    return None
