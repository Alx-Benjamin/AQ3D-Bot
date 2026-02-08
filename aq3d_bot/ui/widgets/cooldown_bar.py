from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout


class CooldownBar(QWidget):
    """Single skill cooldown indicator showing name, hotkey, and a progress bar."""

    def __init__(self, name: str = "", hotkey: str = "", enabled: bool = True, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._label = QLabel(f"[{hotkey}] {name}")
        self._label.setFixedWidth(140)
        self._label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self._label)

        self._bar = QProgressBar()
        self._bar.setObjectName("cooldown_bar")
        self._bar.setRange(0, 100)
        self._bar.setValue(100)
        self._bar.setTextVisible(True)
        self._bar.setFormat("READY")
        self._bar.setFixedHeight(20)
        layout.addWidget(self._bar, stretch=1)

        self._cooldown_total: float = 0
        self._cooldown_start: float = 0
        self._enabled = enabled

        if not enabled:
            self._label.setStyleSheet("font-size: 12px; color: #585b70;")
            self._bar.setFormat("OFF")
            self._bar.setValue(0)

    def set_skill_info(self, name: str, hotkey: str, enabled: bool = True) -> None:
        self._label.setText(f"[{hotkey}] {name}")
        self._enabled = enabled
        if not enabled:
            self._label.setStyleSheet("font-size: 12px; color: #585b70;")
            self._bar.setFormat("OFF")
            self._bar.setValue(0)
        else:
            self._label.setStyleSheet("font-size: 12px;")

    def trigger_cooldown(self, cooldown_seconds: float) -> None:
        """Start a cooldown countdown."""
        if not self._enabled:
            return
        self._cooldown_total = cooldown_seconds
        self._cooldown_start = time.time()

    def update_display(self) -> None:
        """Call periodically to update the progress bar."""
        if not self._enabled:
            return

        if self._cooldown_total <= 0:
            self._bar.setValue(100)
            self._bar.setFormat("READY")
            return

        elapsed = time.time() - self._cooldown_start
        remaining = self._cooldown_total - elapsed

        if remaining <= 0:
            self._bar.setValue(100)
            self._bar.setFormat("READY")
            self._cooldown_total = 0
        else:
            pct = int((elapsed / self._cooldown_total) * 100)
            self._bar.setValue(pct)
            self._bar.setFormat(f"{remaining:.1f}s")


class CooldownPanel(QWidget):
    """Panel showing cooldown bars for all 9 skill slots."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)

        self._bars: list[CooldownBar] = []

        # Update timer — refreshes cooldown displays
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_all)
        self._timer.start(100)  # 10 fps

    def set_skills(self, skills: list) -> None:
        """Rebuild the cooldown bars from a list of Skill objects.

        Always shows all skills (including disabled ones, shown greyed out).
        """
        # Clear existing
        for bar in self._bars:
            self._layout.removeWidget(bar)
            bar.deleteLater()
        self._bars.clear()

        for skill in skills:
            bar = CooldownBar(skill.name, skill.hotkey, skill.enabled)
            self._layout.addWidget(bar)
            self._bars.append(bar)

    def on_skill_used(self, skill_index: int, cooldown: float) -> None:
        """Trigger cooldown for the skill at the given slot index."""
        if 0 <= skill_index < len(self._bars):
            self._bars[skill_index].trigger_cooldown(cooldown)

    def _update_all(self) -> None:
        for bar in self._bars:
            bar.update_display()
