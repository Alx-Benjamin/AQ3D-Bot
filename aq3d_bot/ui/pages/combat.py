from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel, QScrollArea, QTextEdit,
)

from ...models.profile import Profile
from ...models.skill import NUM_SKILL_SLOTS
from ..widgets.skill_card import SkillCard
from ..widgets.rotation_builder import RotationBuilder


class CombatPage(QWidget):
    """Combat configuration page with Skills, Rotation, and Targeting tabs."""

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._notify = lambda *_: self.settings_changed.emit()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # --- Skills tab (fixed 9 slots) ---
        self._skills_tab = QWidget()
        skills_layout = QVBoxLayout(self._skills_tab)

        skills_header = QLabel("Configure your 9 skill slots (1 Auto Attack + 4 Class + 4 Cross)")
        skills_header.setObjectName("subheading")
        skills_layout.addWidget(skills_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        skills_layout.addWidget(scroll)

        self._skills_container = QWidget()
        self._skills_inner_layout = QVBoxLayout(self._skills_container)
        self._skills_inner_layout.setContentsMargins(4, 4, 4, 4)
        self._skills_inner_layout.setSpacing(4)
        self._skills_inner_layout.addStretch()
        scroll.setWidget(self._skills_container)

        self._skill_cards: list[SkillCard] = []
        self._tabs.addTab(self._skills_tab, "Skills")

        # --- Rotation tab ---
        self._rotation_tab = QWidget()
        rotation_layout = QVBoxLayout(self._rotation_tab)

        self.rotation_builder = RotationBuilder()
        self.rotation_builder.rotation_changed.connect(self._notify)
        rotation_layout.addWidget(self.rotation_builder)

        self._tabs.addTab(self._rotation_tab, "Rotation")

        # --- Targeting tab ---
        self._targeting_tab = QWidget()
        targeting_layout = QVBoxLayout(self._targeting_tab)

        targeting_header = QLabel("Target enemies by name (one per line, partial match):")
        targeting_header.setObjectName("subheading")
        targeting_header.setWordWrap(True)
        targeting_layout.addWidget(targeting_header)

        self._target_names_edit = QTextEdit()
        self._target_names_edit.setPlaceholderText("Leave empty to target all enemies")
        self._target_names_edit.textChanged.connect(self._notify)
        targeting_layout.addWidget(self._target_names_edit)

        self._tabs.addTab(self._targeting_tab, "Targeting")

    def load_profile(self, profile: Profile) -> None:
        """Populate skill cards, rotation, and targeting from a profile."""
        self._build_skill_cards(profile)
        self.rotation_builder.set_skills(profile.skills)
        self.rotation_builder.set_rotation(profile.rotation)
        self.rotation_builder.set_delays(profile.delay_min, profile.delay_max)
        self._target_names_edit.setPlainText("\n".join(profile.target_enemy_names))

    def save_to_profile(self, profile: Profile) -> Profile:
        """Write skills, rotation, and targeting back into a profile."""
        profile.skills = [card.get_skill() for card in self._skill_cards]
        profile.rotation = self.rotation_builder.get_rotation()
        profile.delay_min = self.rotation_builder.get_delay_min()
        profile.delay_max = self.rotation_builder.get_delay_max()
        profile.target_enemy_names = [
            line.strip()
            for line in self._target_names_edit.toPlainText().splitlines()
            if line.strip()
        ]
        return profile

    def set_enabled_state(self, enabled: bool) -> None:
        """Enable/disable all inputs (for when bot is running)."""
        for card in self._skill_cards:
            card.set_enabled_state(enabled)
        self.rotation_builder.set_enabled_state(enabled)
        self._target_names_edit.setEnabled(enabled)

    def _build_skill_cards(self, profile: Profile) -> None:
        """Build the fixed 9 skill cards from a profile."""
        for card in self._skill_cards:
            self._skills_inner_layout.removeWidget(card)
            card.deleteLater()
        self._skill_cards.clear()

        for i, skill in enumerate(profile.skills[:NUM_SKILL_SLOTS]):
            card = SkillCard(skill, slot_index=i)
            card.changed.connect(self._on_skill_changed)
            self._skills_inner_layout.insertWidget(self._skills_inner_layout.count() - 1, card)
            self._skill_cards.append(card)

    def _on_skill_changed(self) -> None:
        """When a skill card changes, update the rotation builder palette."""
        skills = [card.get_skill() for card in self._skill_cards]
        self.rotation_builder.set_skills(skills)
        self.settings_changed.emit()
