from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QDoubleSpinBox, QGroupBox, QFrame,
)

from ...models.profile import RotationStep, WAIT_STEP_INDEX
from ...models.skill import Skill, NUM_SKILL_SLOTS


# Colors for skill types in the palette
_TYPE_COLORS = {
    "auto_attack": "#f9e2af",
    "class": "#89b4fa",
    "cross": "#cba6f7",
}

_WAIT_COLOR = "#9399b2"

_ITEM_HEIGHT = 40


class _RotationItemWidget(QFrame):
    """Card-like widget for a rotation list item with drag handle and delete button."""

    delete_clicked = Signal(int)  # row index

    def __init__(self, text: str, color: str, row: int, parent=None):
        super().__init__(parent)
        self._row = row
        self.setObjectName("rotation_item")
        self.setFrameShape(QFrame.Shape.NoFrame)

        # Card style with colored left accent and hover effect
        self.setStyleSheet(f"""
            #rotation_item {{
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 6px;
                border-left: 3px solid {color};
            }}
            #rotation_item:hover {{
                background-color: #1e1e2e;
                border-color: #585b70;
                border-left: 3px solid {color};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 6, 4)
        layout.setSpacing(8)

        _clear = "background: transparent; border: none;"

        # Drag handle grip
        grip = QLabel("\u2807\u2807")
        grip.setStyleSheet(f"color: #585b70; font-size: 16px; {_clear}")
        grip.setFixedWidth(18)
        grip.setCursor(Qt.CursorShape.OpenHandCursor)
        layout.addWidget(grip)

        # Skill label
        label = QLabel(text)
        label.setStyleSheet(f"color: {color}; font-size: 13px; {_clear}")
        layout.addWidget(label, stretch=1)

        # Delete button — subtle until hovered
        del_btn = QPushButton("\u2715")
        del_btn.setFixedSize(24, 24)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #585b70; border: none; "
            "font-size: 14px; border-radius: 4px; padding: 0; }"
            "QPushButton:hover { background-color: #f38ba8; color: #1e1e2e; }"
        )
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(self._row))
        layout.addWidget(del_btn)

    def set_row(self, row: int) -> None:
        self._row = row


class RotationBuilder(QWidget):
    """Rotation builder with a skill palette and an ordered rotation list.

    Left: Skill palette — 9 buttons (one per skill slot) + Wait button.
    Right: Rotation sequence list — drag-drop reorder, per-item delete.
    Bottom: Delay min/max configuration.
    """

    rotation_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._skills: list[Skill] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # --- Left panel: Skill palette ---
        palette_group = QGroupBox("Skill Palette")
        palette_layout = QVBoxLayout(palette_group)
        palette_layout.setSpacing(4)

        palette_layout.addWidget(QLabel("Click to add to rotation:"))

        self._palette_buttons: list[QPushButton] = []

        # Auto Attack section
        auto_label = QLabel("Auto Attack")
        auto_label.setStyleSheet("color: #f9e2af; font-weight: bold; font-size: 11px;")
        palette_layout.addWidget(auto_label)
        btn = QPushButton("Auto Attack [1]")
        btn.clicked.connect(lambda checked=False, idx=0: self._add_to_rotation(idx))
        palette_layout.addWidget(btn)
        self._palette_buttons.append(btn)

        # Class Skills section (slots 1-4)
        class_label = QLabel("Class Skills")
        class_label.setStyleSheet("color: #89b4fa; font-weight: bold; font-size: 11px;")
        palette_layout.addWidget(class_label)
        for i in range(1, 5):
            btn = QPushButton(f"Class Skill {i} [{i + 1}]")
            btn.clicked.connect(lambda checked=False, idx=i: self._add_to_rotation(idx))
            palette_layout.addWidget(btn)
            self._palette_buttons.append(btn)

        # Cross Skills section (slots 5-8)
        cross_label = QLabel("Cross Skills")
        cross_label.setStyleSheet("color: #cba6f7; font-weight: bold; font-size: 11px;")
        palette_layout.addWidget(cross_label)
        for i in range(5, 9):
            btn = QPushButton(f"Cross Skill {i - 4} [{i + 1}]")
            btn.clicked.connect(lambda checked=False, idx=i: self._add_to_rotation(idx))
            palette_layout.addWidget(btn)
            self._palette_buttons.append(btn)

        # Wait/Pause button
        palette_layout.addSpacing(8)
        wait_label = QLabel("Utility")
        wait_label.setStyleSheet("color: #9399b2; font-weight: bold; font-size: 11px;")
        palette_layout.addWidget(wait_label)

        wait_row = QHBoxLayout()
        self._wait_btn = QPushButton("Add Wait")
        self._wait_btn.clicked.connect(self._add_wait_step)
        wait_row.addWidget(self._wait_btn)
        self._wait_spin = QDoubleSpinBox()
        self._wait_spin.setRange(0.1, 30.0)
        self._wait_spin.setSingleStep(0.5)
        self._wait_spin.setSuffix("s")
        self._wait_spin.setValue(1.0)
        self._wait_spin.setFixedWidth(70)
        wait_row.addWidget(self._wait_spin)
        palette_layout.addLayout(wait_row)

        palette_layout.addStretch()
        layout.addWidget(palette_group)

        # --- Right panel: Rotation list + controls ---
        right_panel = QVBoxLayout()
        right_panel.setSpacing(8)

        right_panel.addWidget(QLabel("Rotation Sequence (executes top to bottom, loops):"))

        self._rotation_list = QListWidget()
        self._rotation_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._rotation_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._rotation_list.setSpacing(4)
        self._rotation_list.setStyleSheet(
            "QListWidget::item:selected { background-color: transparent; }"
        )
        self._rotation_list.model().rowsMoved.connect(self._on_reorder)
        right_panel.addWidget(self._rotation_list, stretch=1)

        # Clear All button
        list_btns = QHBoxLayout()
        list_btns.addStretch()
        self._clear_btn = QPushButton("Clear All")
        self._clear_btn.setStyleSheet("background-color: #f38ba8; color: #1e1e2e;")
        self._clear_btn.clicked.connect(self._clear_rotation)
        list_btns.addWidget(self._clear_btn)
        right_panel.addLayout(list_btns)

        # Delay config
        delay_frame = QFrame()
        delay_frame.setObjectName("card")
        delay_layout = QHBoxLayout(delay_frame)
        delay_layout.setContentsMargins(8, 8, 8, 8)

        delay_layout.addWidget(QLabel("Delay between skills:"))

        delay_layout.addWidget(QLabel("Min:"))
        self._delay_min_spin = QDoubleSpinBox()
        self._delay_min_spin.setRange(0.0, 5.0)
        self._delay_min_spin.setSingleStep(0.05)
        self._delay_min_spin.setSuffix("s")
        self._delay_min_spin.setValue(0.1)
        self._delay_min_spin.valueChanged.connect(self._on_delay_changed)
        delay_layout.addWidget(self._delay_min_spin)

        delay_layout.addWidget(QLabel("Max:"))
        self._delay_max_spin = QDoubleSpinBox()
        self._delay_max_spin.setRange(0.0, 5.0)
        self._delay_max_spin.setSingleStep(0.05)
        self._delay_max_spin.setSuffix("s")
        self._delay_max_spin.setValue(0.3)
        self._delay_max_spin.valueChanged.connect(self._on_delay_changed)
        delay_layout.addWidget(self._delay_max_spin)

        delay_layout.addStretch()
        right_panel.addWidget(delay_frame)

        layout.addLayout(right_panel, stretch=1)

    # --- Public API ---

    def set_skills(self, skills: list[Skill]) -> None:
        """Update the skill list (refreshes palette button labels)."""
        self._skills = skills
        self._update_palette_labels()
        self._rebuild_item_widgets()

    def set_rotation(self, rotation: list[RotationStep]) -> None:
        """Load a rotation into the list."""
        self._rotation_list.clear()
        for step in rotation:
            self._add_list_item(step)
        self._rebuild_item_widgets()

    def get_rotation(self) -> list[RotationStep]:
        """Return the current rotation as a list of RotationSteps."""
        steps = []
        for i in range(self._rotation_list.count()):
            item = self._rotation_list.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            if data is None:
                continue
            skill_idx, wait_secs = data
            steps.append(RotationStep(skill_index=skill_idx, wait_seconds=wait_secs))
        return steps

    def set_delays(self, delay_min: float, delay_max: float) -> None:
        self._delay_min_spin.setValue(delay_min)
        self._delay_max_spin.setValue(delay_max)

    def get_delay_min(self) -> float:
        return self._delay_min_spin.value()

    def get_delay_max(self) -> float:
        return self._delay_max_spin.value()

    def set_enabled_state(self, enabled: bool) -> None:
        """Enable/disable all controls."""
        for btn in self._palette_buttons:
            btn.setEnabled(enabled)
        self._wait_btn.setEnabled(enabled)
        self._wait_spin.setEnabled(enabled)
        self._rotation_list.setEnabled(enabled)
        self._clear_btn.setEnabled(enabled)
        self._delay_min_spin.setEnabled(enabled)
        self._delay_max_spin.setEnabled(enabled)

    # --- Internal ---

    def _update_palette_labels(self) -> None:
        """Refresh palette button text with current skill names."""
        for i, btn in enumerate(self._palette_buttons):
            if i < len(self._skills):
                skill = self._skills[i]
                btn.setText(f"{skill.name} [{skill.hotkey}]")
            else:
                btn.setText(f"Slot {i + 1}")

    def _add_to_rotation(self, skill_index: int) -> None:
        """Add a skill to the end of the rotation."""
        step = RotationStep(skill_index=skill_index)
        self._add_list_item(step)
        self._rebuild_item_widgets()
        self.rotation_changed.emit()

    def _add_wait_step(self) -> None:
        """Add a wait/pause step to the rotation."""
        wait_secs = self._wait_spin.value()
        step = RotationStep(skill_index=WAIT_STEP_INDEX, wait_seconds=wait_secs)
        self._add_list_item(step)
        self._rebuild_item_widgets()
        self.rotation_changed.emit()

    def _add_list_item(self, step: RotationStep) -> None:
        """Add an item to the rotation list widget."""
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, (step.skill_index, step.wait_seconds))
        item.setSizeHint(QSize(0, _ITEM_HEIGHT))
        self._rotation_list.addItem(item)

    def _step_display(self, step: RotationStep) -> tuple[str, str]:
        """Return (display_text, color) for a rotation step."""
        if step.is_wait:
            return (f"Wait {step.wait_seconds:.1f}s", _WAIT_COLOR)

        idx = step.skill_index
        if 0 <= idx < len(self._skills):
            skill = self._skills[idx]
            text = f"{skill.name}  [{skill.hotkey}]"
            color = _TYPE_COLORS.get(skill.slot_type, "#cdd6f4")
        else:
            text = f"Slot {idx + 1}"
            color = "#cdd6f4"
        return (text, color)

    def _rebuild_item_widgets(self) -> None:
        """Rebuild all item widgets (needed after drag-drop or data changes)."""
        for i in range(self._rotation_list.count()):
            item = self._rotation_list.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            if data is None:
                continue
            skill_idx, wait_secs = data
            step = RotationStep(skill_index=skill_idx, wait_seconds=wait_secs)
            text, color = self._step_display(step)

            widget = _RotationItemWidget(text, color, i)
            widget.delete_clicked.connect(self._delete_row)
            item.setSizeHint(QSize(0, _ITEM_HEIGHT))
            self._rotation_list.setItemWidget(item, widget)

    def _delete_row(self, row: int) -> None:
        """Remove the item at the given row."""
        if 0 <= row < self._rotation_list.count():
            self._rotation_list.takeItem(row)
            self._rebuild_item_widgets()
            self.rotation_changed.emit()

    def _clear_rotation(self) -> None:
        """Remove all items from the rotation."""
        self._rotation_list.clear()
        self.rotation_changed.emit()

    def _on_reorder(self) -> None:
        self._rebuild_item_widgets()
        self.rotation_changed.emit()

    def _on_delay_changed(self) -> None:
        if self._delay_min_spin.value() > self._delay_max_spin.value():
            self._delay_max_spin.setValue(self._delay_min_spin.value())
        self.rotation_changed.emit()
