from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QCheckBox, QSizePolicy,
)

from ...models.skill import Skill


# Slot type display labels
_TYPE_LABELS = {
    "auto_attack": "Auto",
    "class": "Class",
    "cross": "Cross",
}

_TYPE_COLORS = {
    "auto_attack": "#f9e2af",
    "class": "#89b4fa",
    "cross": "#cba6f7",
}


class SkillCard(QFrame):
    """Fixed skill config row showing type, name, hotkey, cooldown, and enabled toggle.

    Emits `changed` whenever any field is modified.
    """

    changed = Signal()

    def __init__(self, skill: Skill, slot_index: int, parent=None):
        super().__init__(parent)
        self.setObjectName("skill_card")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(56)

        self._skill = skill
        self._slot_index = slot_index

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Slot type label
        type_text = _TYPE_LABELS.get(skill.slot_type, "Class")
        type_color = _TYPE_COLORS.get(skill.slot_type, "#89b4fa")
        self._type_label = QLabel(type_text)
        self._type_label.setFixedWidth(40)
        self._type_label.setStyleSheet(f"color: {type_color}; font-size: 11px; font-weight: bold;")
        layout.addWidget(self._type_label)

        # Name
        self._name_edit = QLineEdit(skill.name)
        self._name_edit.setPlaceholderText("Skill Name")
        self._name_edit.setMinimumWidth(100)
        self._name_edit.textChanged.connect(self._on_changed)
        layout.addWidget(self._name_edit, stretch=2)

        # Lock the name for Auto Attack (slot 0)
        if skill.slot_type == "auto_attack":
            self._name_edit.setReadOnly(True)
            self._name_edit.setStyleSheet("color: #f9e2af;")

        # Hotkey
        hotkey_label = QLabel("Key:")
        hotkey_label.setStyleSheet("color: #a6adc8;")
        layout.addWidget(hotkey_label)
        self._hotkey_edit = QLineEdit(skill.hotkey)
        self._hotkey_edit.setFixedWidth(40)
        self._hotkey_edit.setMaxLength(3)
        self._hotkey_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hotkey_edit.textChanged.connect(self._on_changed)
        layout.addWidget(self._hotkey_edit)

        # Cooldown
        cd_label = QLabel("CD:")
        cd_label.setStyleSheet("color: #a6adc8;")
        layout.addWidget(cd_label)
        self._cooldown_spin = QSpinBox()
        self._cooldown_spin.setRange(0, 999)
        self._cooldown_spin.setSuffix("s")
        self._cooldown_spin.setValue(int(skill.cooldown))
        self._cooldown_spin.setFixedWidth(85)
        self._cooldown_spin.valueChanged.connect(self._on_changed)
        layout.addWidget(self._cooldown_spin)

        # Enabled checkbox
        self._enabled_check = QCheckBox("On")
        self._enabled_check.setChecked(skill.enabled)
        self._enabled_check.stateChanged.connect(self._on_changed)
        layout.addWidget(self._enabled_check)

    @property
    def slot_index(self) -> int:
        return self._slot_index

    def get_skill(self) -> Skill:
        """Return the current Skill data from the card's fields."""
        return Skill(
            name=self._name_edit.text(),
            hotkey=self._hotkey_edit.text(),
            cooldown=float(self._cooldown_spin.value()),
            enabled=self._enabled_check.isChecked(),
            slot_type=self._skill.slot_type,
        )

    def set_enabled_state(self, enabled: bool) -> None:
        """Enable/disable all input fields (for when bot is running)."""
        if self._skill.slot_type != "auto_attack":
            self._name_edit.setEnabled(enabled)
        self._hotkey_edit.setEnabled(enabled)
        self._cooldown_spin.setEnabled(enabled)
        self._enabled_check.setEnabled(enabled)

    def _on_changed(self) -> None:
        self.changed.emit()
