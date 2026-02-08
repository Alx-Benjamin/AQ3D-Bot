from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QProgressBar,
)

from ..widgets.cooldown_bar import CooldownPanel
from ..widgets.log_viewer import LogViewer
from ..widgets.ocr_preview import OCRPreviewPanel


# State → (display text, color)
STATE_STYLES = {
    "Idle": ("#6c7086", "Idle"),
    "Searching": ("#f9e2af", "Searching"),
    "Attacking": ("#a6e3a1", "Attacking"),
    "Looting": ("#89b4fa", "Looting"),
    "Moving": ("#cba6f7", "Moving"),
    "Dead": ("#f38ba8", "Dead"),
    "Reviving": ("#fab387", "Reviving"),
    "Running Back": ("#fab387", "Running Back"),
    "AFK": ("#9399b2", "AFK"),
}


class DashboardPage(QWidget):
    """Live dashboard showing bot state, enemy, health, skills, OCR previews, and logs."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # --- Top status row ---
        status_frame = QFrame()
        status_frame.setObjectName("card")
        status_layout = QHBoxLayout(status_frame)
        status_layout.setSpacing(24)

        # Bot state
        state_col = QVBoxLayout()
        state_col.setSpacing(2)
        state_col.addWidget(QLabel("Bot State"))
        self._state_label = QLabel("Idle")
        self._state_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #6c7086;")
        state_col.addWidget(self._state_label)
        status_layout.addLayout(state_col)

        # Enemy name
        enemy_col = QVBoxLayout()
        enemy_col.setSpacing(2)
        enemy_col.addWidget(QLabel("Enemy"))
        self._enemy_label = QLabel("—")
        self._enemy_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        enemy_col.addWidget(self._enemy_label)
        status_layout.addLayout(enemy_col)

        # Health
        health_col = QVBoxLayout()
        health_col.setSpacing(2)
        health_col.addWidget(QLabel("Player HP"))
        self._health_bar = QProgressBar()
        self._health_bar.setObjectName("health_bar")
        self._health_bar.setRange(0, 100)
        self._health_bar.setValue(100)
        self._health_bar.setFormat("%v%")
        self._health_bar.setFixedHeight(24)
        self._health_bar.setFixedWidth(150)
        health_col.addWidget(self._health_bar)
        status_layout.addLayout(health_col)

        # Kills
        kills_col = QVBoxLayout()
        kills_col.setSpacing(2)
        kills_col.addWidget(QLabel("Kills"))
        self._kills_label = QLabel("0")
        self._kills_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #a6e3a1;")
        kills_col.addWidget(self._kills_label)
        status_layout.addLayout(kills_col)

        # Runtime
        runtime_col = QVBoxLayout()
        runtime_col.setSpacing(2)
        runtime_col.addWidget(QLabel("Runtime"))
        self._runtime_label = QLabel("00:00:00")
        self._runtime_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        runtime_col.addWidget(self._runtime_label)
        status_layout.addLayout(runtime_col)

        status_layout.addStretch()
        layout.addWidget(status_frame)

        # --- Skill cooldowns ---
        self.cooldown_panel = CooldownPanel()
        layout.addWidget(self.cooldown_panel)

        # --- OCR previews ---
        self.ocr_panel = OCRPreviewPanel()
        layout.addWidget(self.ocr_panel)

        # --- Logs ---
        self.log_viewer = LogViewer()
        layout.addWidget(self.log_viewer, stretch=1)

        # --- Runtime timer ---
        self._start_time: float = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_runtime)

    # --- Public slots (connected to engine signals) ---

    @Slot(str)
    def on_state_changed(self, state: str) -> None:
        color, text = STATE_STYLES.get(state, ("#6c7086", state))
        self._state_label.setText(text)
        self._state_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color};")

    @Slot(str)
    def on_enemy_detected(self, name: str) -> None:
        self._enemy_label.setText(name if name else "—")

    @Slot(int)
    def on_health_updated(self, health: int) -> None:
        if health < 0:
            self._health_bar.setValue(0)
            self._health_bar.setFormat("?")
        else:
            self._health_bar.setValue(min(health, 100))
            self._health_bar.setFormat(f"{health}%")

    @Slot(int)
    def on_kill_count_updated(self, count: int) -> None:
        self._kills_label.setText(str(count))

    def start_runtime_timer(self) -> None:
        self._start_time = time.time()
        self._kills_label.setText("0")
        self._timer.start(1000)

    def stop_runtime_timer(self) -> None:
        self._timer.stop()

    def reset_dashboard(self) -> None:
        self.on_state_changed("Idle")
        self.on_enemy_detected("")
        self.on_health_updated(100)
        self._kills_label.setText("0")
        self._runtime_label.setText("00:00:00")

    def _update_runtime(self) -> None:
        elapsed = int(time.time() - self._start_time)
        hrs, rem = divmod(elapsed, 3600)
        mins, secs = divmod(rem, 60)
        self._runtime_label.setText(f"{hrs:02d}:{mins:02d}:{secs:02d}")
