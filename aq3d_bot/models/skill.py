from dataclasses import dataclass


@dataclass
class Skill:
    """Represents a single combat skill with its configuration.

    There are exactly 9 fixed skill slots:
      Slot 0: Auto Attack (name locked)
      Slots 1-4: Class Skills
      Slots 5-8: Cross Skills
    """

    name: str = "Skill"
    hotkey: str = "1"
    cooldown: float = 0.0
    enabled: bool = True
    slot_type: str = "class"  # "auto_attack", "class", or "cross"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "hotkey": self.hotkey,
            "cooldown": self.cooldown,
            "enabled": self.enabled,
            "slot_type": self.slot_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Skill":
        return cls(
            name=data.get("name", "Skill"),
            hotkey=data.get("hotkey", "1"),
            cooldown=data.get("cooldown", 0.0),
            enabled=data.get("enabled", True),
            slot_type=data.get("slot_type", "class"),
        )


NUM_SKILL_SLOTS = 9

DEFAULT_SKILLS = [
    Skill("Auto Attack", "1", 0.0, True, "auto_attack"),
    Skill("Class Skill 1", "2", 5.0, True, "class"),
    Skill("Class Skill 2", "3", 10.0, True, "class"),
    Skill("Class Skill 3", "4", 15.0, True, "class"),
    Skill("Class Skill 4", "5", 20.0, True, "class"),
    Skill("Cross Skill 1", "6", 30.0, True, "cross"),
    Skill("Cross Skill 2", "7", 30.0, True, "cross"),
    Skill("Cross Skill 3", "8", 30.0, True, "cross"),
    Skill("Cross Skill 4", "9", 60.0, True, "cross"),
]
