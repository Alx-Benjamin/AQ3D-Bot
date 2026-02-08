from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass
class GlobalSettings:
    """Global bot settings — screen regions, movement, timeouts, AFK.

    These are independent of the active class/profile.
    """

    # Screen regions (None = not configured)
    enemy_name_box: tuple[int, int, int, int] | None = None
    player_health_box: tuple[int, int, int, int] | None = None
    menu_close_point: tuple[int, int] | None = None
    revive_box: tuple[int, int, int, int] | None = None

    # Movement
    movement_keys: dict[str, bool] = field(
        default_factory=lambda: {"w": True, "a": True, "s": True, "d": True}
    )
    movement_loops: int = 5
    jump_while_moving: bool = False

    # Timeouts
    no_enemy_timeout_minutes: int = 5
    max_runtime_hours: int = 0  # 0 = unlimited

    # AFK
    afk_interval_minutes: int = 0  # 0 = disabled
    afk_duration_minutes: int = 0  # capped at 15

    # Window management
    focus_aq3d_enabled: bool = True
    stay_on_top: bool = False
    minimize_to_tray_on_close: bool = True

    # --- Serialization ---

    def to_dict(self) -> dict:
        return {
            "enemy_name_box": list(self.enemy_name_box) if self.enemy_name_box else None,
            "player_health_box": list(self.player_health_box) if self.player_health_box else None,
            "menu_close_point": list(self.menu_close_point) if self.menu_close_point else None,
            "revive_box": list(self.revive_box) if self.revive_box else None,
            "movement_keys": self.movement_keys,
            "movement_loops": self.movement_loops,
            "jump_while_moving": self.jump_while_moving,
            "no_enemy_timeout_minutes": self.no_enemy_timeout_minutes,
            "max_runtime_hours": self.max_runtime_hours,
            "afk_interval_minutes": self.afk_interval_minutes,
            "afk_duration_minutes": min(self.afk_duration_minutes, 15),
            "focus_aq3d_enabled": self.focus_aq3d_enabled,
            "stay_on_top": self.stay_on_top,
            "minimize_to_tray_on_close": self.minimize_to_tray_on_close,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GlobalSettings:
        def _tuple_or_none(val, length):
            if val and len(val) == length:
                return tuple(val)
            return None

        return cls(
            enemy_name_box=_tuple_or_none(data.get("enemy_name_box"), 4),
            player_health_box=_tuple_or_none(data.get("player_health_box"), 4),
            menu_close_point=_tuple_or_none(data.get("menu_close_point"), 2),
            revive_box=_tuple_or_none(data.get("revive_box"), 4),
            movement_keys=data.get("movement_keys", {"w": True, "a": True, "s": True, "d": True}),
            movement_loops=data.get("movement_loops", 5),
            jump_while_moving=data.get("jump_while_moving", False),
            no_enemy_timeout_minutes=data.get("no_enemy_timeout_minutes", 5),
            max_runtime_hours=data.get("max_runtime_hours", 0),
            afk_interval_minutes=data.get("afk_interval_minutes", 0),
            afk_duration_minutes=min(data.get("afk_duration_minutes", 0), 15),
            focus_aq3d_enabled=data.get("focus_aq3d_enabled", True),
            stay_on_top=data.get("stay_on_top", False),
            minimize_to_tray_on_close=data.get("minimize_to_tray_on_close", True),
        )

    def save(self, path: str = "settings.json") -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=4)

    @classmethod
    def load(cls, path: str = "settings.json") -> GlobalSettings:
        if not os.path.exists(path):
            return cls()
        with open(path, "r") as f:
            return cls.from_dict(json.load(f))
