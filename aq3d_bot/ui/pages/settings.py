from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QSpinBox, QCheckBox,
    QHBoxLayout, QTabWidget, QPushButton, QLineEdit, QTextEdit,
)

from ...models.profile import Profile
from ...models.settings import GlobalSettings
from ..widgets.overlay import OverlayWindow


class SettingsPage(QWidget):
    """Consolidated settings page with 5 tabs.

    Handles both GlobalSettings and per-Profile settings.
    """

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._notify = lambda *_: self.settings_changed.emit()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._build_screen_regions_tab()
        self._build_combat_actions_tab()
        self._build_movement_tab()
        self._build_timers_tab()
        self._build_window_tab()

    # ------------------------------------------------------------------ #
    # Tab 1: Screen Regions (GlobalSettings)
    # ------------------------------------------------------------------ #

    def _build_screen_regions_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        desc = QLabel(
            "Click each button to open a fullscreen overlay, then drag to select "
            "the region or click to select a point. Press Escape to cancel."
        )
        desc.setWordWrap(True)
        desc.setObjectName("subheading")
        layout.addWidget(desc)

        grid = QGridLayout()
        grid.setSpacing(10)
        layout.addLayout(grid)

        self._locations: dict[str, dict] = {}
        self._location_buttons: list[QPushButton] = []

        regions = [
            ("enemy_name_box", "Set Enemy Name Area", "area"),
            ("player_health_box", "Set Player Health Area", "area"),
            ("menu_close_point", "Set Menu Close Position", "point"),
            ("revive_box", "Set Revive Button Area", "area"),
        ]

        for row, (key, text, mode) in enumerate(regions):
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked=False, k=key, m=mode: self._pick_location(k, m))
            grid.addWidget(btn, row, 0)
            self._location_buttons.append(btn)

            label = QLabel("Not Set")
            label.setStyleSheet("color: #a6adc8;")
            grid.addWidget(label, row, 1)

            self._locations[key] = {"label": label, "value": None, "mode": mode}

        layout.addStretch()
        self._tabs.addTab(tab, "Screen Regions")

    # ------------------------------------------------------------------ #
    # Tab 2: Combat & Actions (Profile + GlobalSettings mix)
    # ------------------------------------------------------------------ #

    def _build_combat_actions_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        # Jumping section
        jump_label = QLabel("Jumping")
        jump_label.setStyleSheet("font-weight: bold; color: #89b4fa;")
        layout.addWidget(jump_label)

        self._jump_attacking_check = QCheckBox("Jump While Attacking")
        self._jump_attacking_check.stateChanged.connect(self._notify)
        layout.addWidget(self._jump_attacking_check)

        self._jump_moving_check = QCheckBox("Jump While Moving")
        self._jump_moving_check.stateChanged.connect(self._notify)
        layout.addWidget(self._jump_moving_check)

        # Potions section
        potion_label = QLabel("Potions")
        potion_label.setStyleSheet("font-weight: bold; color: #89b4fa;")
        layout.addWidget(potion_label)

        potion_row = QHBoxLayout()
        potion_row.addWidget(QLabel("Potion Hotkey:"))
        self._potion_hotkey_edit = QLineEdit("p")
        self._potion_hotkey_edit.setFixedWidth(40)
        self._potion_hotkey_edit.setMaxLength(3)
        self._potion_hotkey_edit.textChanged.connect(self._notify)
        potion_row.addWidget(self._potion_hotkey_edit)
        potion_row.addWidget(QLabel("Use below"))
        self._potion_threshold_spin = QSpinBox()
        self._potion_threshold_spin.setRange(1, 100)
        self._potion_threshold_spin.setSuffix("%")
        self._potion_threshold_spin.setValue(50)
        self._potion_threshold_spin.valueChanged.connect(self._notify)
        potion_row.addWidget(self._potion_threshold_spin)
        potion_row.addStretch()
        layout.addLayout(potion_row)

        # Loot section
        loot_label = QLabel("Loot")
        loot_label.setStyleSheet("font-weight: bold; color: #89b4fa;")
        layout.addWidget(loot_label)

        self._collect_loot_check = QCheckBox("Collect Loot")
        self._collect_loot_check.stateChanged.connect(self._notify)
        layout.addWidget(self._collect_loot_check)

        loot_row = QHBoxLayout()
        loot_row.addWidget(QLabel("Loot Hotkey:"))
        self._loot_hotkey_edit = QLineEdit("l")
        self._loot_hotkey_edit.setFixedWidth(40)
        self._loot_hotkey_edit.setMaxLength(3)
        self._loot_hotkey_edit.textChanged.connect(self._notify)
        loot_row.addWidget(self._loot_hotkey_edit)
        loot_row.addStretch()
        layout.addLayout(loot_row)

        # Death section
        death_label = QLabel("Death")
        death_label.setStyleSheet("font-weight: bold; color: #89b4fa;")
        layout.addWidget(death_label)

        self._stop_on_death_check = QCheckBox("Stop Bot on Death")
        self._stop_on_death_check.stateChanged.connect(self._notify)
        layout.addWidget(self._stop_on_death_check)

        run_back_row = QHBoxLayout()
        self._run_back_check = QCheckBox("Run back after death for")
        self._run_back_check.stateChanged.connect(self._toggle_run_back)
        self._run_back_check.stateChanged.connect(self._notify)
        run_back_row.addWidget(self._run_back_check)
        self._run_back_spin = QSpinBox()
        self._run_back_spin.setRange(1, 60)
        self._run_back_spin.setSuffix(" seconds")
        self._run_back_spin.setValue(5)
        self._run_back_spin.valueChanged.connect(self._notify)
        run_back_row.addWidget(self._run_back_spin)
        run_back_row.addStretch()
        layout.addLayout(run_back_row)

        layout.addStretch()
        self._tabs.addTab(tab, "Combat & Actions")

    # ------------------------------------------------------------------ #
    # Tab 3: Movement (GlobalSettings)
    # ------------------------------------------------------------------ #

    def _build_movement_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        grid = QGridLayout()
        grid.setSpacing(10)
        layout.addLayout(grid)
        row = 0

        grid.addWidget(QLabel("Movement Loops:"), row, 0)
        self._movement_loops_spin = QSpinBox()
        self._movement_loops_spin.setRange(1, 50)
        self._movement_loops_spin.setValue(5)
        self._movement_loops_spin.valueChanged.connect(self._notify)
        grid.addWidget(self._movement_loops_spin, row, 1)
        row += 1

        grid.addWidget(QLabel("Movement Keys:"), row, 0)
        keys_frame = QHBoxLayout()
        self._movement_key_checks: dict[str, QCheckBox] = {}
        for key in ["w", "a", "s", "d"]:
            cb = QCheckBox(key.upper())
            cb.setChecked(True)
            cb.stateChanged.connect(self._notify)
            keys_frame.addWidget(cb)
            self._movement_key_checks[key] = cb
        keys_frame.addStretch()
        grid.addLayout(keys_frame, row, 1)

        layout.addStretch()
        self._tabs.addTab(tab, "Movement")

    # ------------------------------------------------------------------ #
    # Tab 4: Timers & AFK (GlobalSettings)
    # ------------------------------------------------------------------ #

    def _build_timers_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        grid = QGridLayout()
        grid.setSpacing(10)
        layout.addLayout(grid)
        row = 0

        grid.addWidget(QLabel("No Enemy Timeout:"), row, 0)
        self._no_enemy_spin = QSpinBox()
        self._no_enemy_spin.setRange(0, 999)
        self._no_enemy_spin.setSuffix(" min")
        self._no_enemy_spin.setValue(5)
        self._no_enemy_spin.setSpecialValueText("Disabled")
        self._no_enemy_spin.valueChanged.connect(self._notify)
        grid.addWidget(self._no_enemy_spin, row, 1)
        row += 1

        grid.addWidget(QLabel("Max Runtime:"), row, 0)
        self._max_runtime_spin = QSpinBox()
        self._max_runtime_spin.setRange(0, 999)
        self._max_runtime_spin.setSuffix(" hrs")
        self._max_runtime_spin.setValue(0)
        self._max_runtime_spin.setSpecialValueText("Unlimited")
        self._max_runtime_spin.valueChanged.connect(self._notify)
        grid.addWidget(self._max_runtime_spin, row, 1)
        row += 1

        grid.addWidget(QLabel("Go AFK Every:"), row, 0)
        self._afk_interval_spin = QSpinBox()
        self._afk_interval_spin.setRange(0, 999)
        self._afk_interval_spin.setSuffix(" min")
        self._afk_interval_spin.setValue(0)
        self._afk_interval_spin.setSpecialValueText("Disabled")
        self._afk_interval_spin.valueChanged.connect(self._notify)
        grid.addWidget(self._afk_interval_spin, row, 1)
        row += 1

        grid.addWidget(QLabel("AFK Duration:"), row, 0)
        self._afk_duration_spin = QSpinBox()
        self._afk_duration_spin.setRange(0, 15)
        self._afk_duration_spin.setSuffix(" min")
        self._afk_duration_spin.setValue(0)
        self._afk_duration_spin.setSpecialValueText("Disabled")
        self._afk_duration_spin.valueChanged.connect(self._notify)
        grid.addWidget(self._afk_duration_spin, row, 1)

        layout.addStretch()
        self._tabs.addTab(tab, "Timers & AFK")

    # ------------------------------------------------------------------ #
    # Tab 5: Window (GlobalSettings)
    # ------------------------------------------------------------------ #

    def _build_window_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        self._focus_check = QCheckBox("Focus AQ3D Window (bring to front when bot acts)")
        self._focus_check.setChecked(True)
        self._focus_check.stateChanged.connect(self._notify)
        layout.addWidget(self._focus_check)

        self._stay_on_top_check = QCheckBox("Keep Bot Window On Top")
        self._stay_on_top_check.stateChanged.connect(self._notify)
        layout.addWidget(self._stay_on_top_check)

        self._minimize_to_tray_check = QCheckBox("Minimize to System Tray on Close (instead of exiting)")
        self._minimize_to_tray_check.setChecked(True)
        self._minimize_to_tray_check.stateChanged.connect(self._notify)
        layout.addWidget(self._minimize_to_tray_check)

        # Tesseract status (read-only)
        tess_label = QLabel("Tesseract OCR")
        tess_label.setStyleSheet("font-weight: bold; color: #89b4fa;")
        layout.addWidget(tess_label)

        self._tesseract_status = QLabel("Checking...")
        layout.addWidget(self._tesseract_status)

        layout.addStretch()
        self._tabs.addTab(tab, "Window")

    # ------------------------------------------------------------------ #
    # Public API — Load / Save
    # ------------------------------------------------------------------ #

    def load_settings(self, settings: GlobalSettings) -> None:
        """Load GlobalSettings fields into the UI."""
        # Screen regions
        mapping = {
            "enemy_name_box": settings.enemy_name_box,
            "player_health_box": settings.player_health_box,
            "menu_close_point": settings.menu_close_point,
            "revive_box": settings.revive_box,
        }
        for key, value in mapping.items():
            self._locations[key]["value"] = value
            self._locations[key]["label"].setText(str(value) if value else "Not Set")

        # Movement
        self._movement_loops_spin.setValue(settings.movement_loops)
        for key, cb in self._movement_key_checks.items():
            cb.setChecked(settings.movement_keys.get(key, True))
        self._jump_moving_check.setChecked(settings.jump_while_moving)

        # Timers
        self._no_enemy_spin.setValue(settings.no_enemy_timeout_minutes)
        self._max_runtime_spin.setValue(settings.max_runtime_hours)
        self._afk_interval_spin.setValue(settings.afk_interval_minutes)
        self._afk_duration_spin.setValue(settings.afk_duration_minutes)

        # Window
        self._focus_check.setChecked(settings.focus_aq3d_enabled)
        self._stay_on_top_check.setChecked(settings.stay_on_top)
        self._minimize_to_tray_check.setChecked(settings.minimize_to_tray_on_close)

    def load_profile(self, profile: Profile) -> None:
        """Load per-Profile fields into the UI."""
        self._jump_attacking_check.setChecked(profile.jump_while_attacking)
        self._potion_hotkey_edit.setText(profile.potion_hotkey)
        self._potion_threshold_spin.setValue(profile.potion_health_threshold)
        self._collect_loot_check.setChecked(profile.collect_loot)
        self._loot_hotkey_edit.setText(profile.loot_hotkey)
        self._stop_on_death_check.setChecked(profile.stop_bot_on_death)
        self._run_back_check.setChecked(profile.run_back_after_death)
        self._run_back_spin.setValue(profile.run_back_seconds)
        self._toggle_run_back()

    def save_to_settings(self, settings: GlobalSettings) -> GlobalSettings:
        """Write GlobalSettings fields back from the UI."""
        # Screen regions
        settings.enemy_name_box = self._locations["enemy_name_box"]["value"]
        settings.player_health_box = self._locations["player_health_box"]["value"]
        settings.menu_close_point = self._locations["menu_close_point"]["value"]
        settings.revive_box = self._locations["revive_box"]["value"]

        # Movement
        settings.movement_loops = self._movement_loops_spin.value()
        settings.movement_keys = {k: cb.isChecked() for k, cb in self._movement_key_checks.items()}
        settings.jump_while_moving = self._jump_moving_check.isChecked()

        # Timers
        settings.no_enemy_timeout_minutes = self._no_enemy_spin.value()
        settings.max_runtime_hours = self._max_runtime_spin.value()
        settings.afk_interval_minutes = self._afk_interval_spin.value()
        settings.afk_duration_minutes = self._afk_duration_spin.value()

        # Window
        settings.focus_aq3d_enabled = self._focus_check.isChecked()
        settings.stay_on_top = self._stay_on_top_check.isChecked()
        settings.minimize_to_tray_on_close = self._minimize_to_tray_check.isChecked()

        return settings

    def save_to_profile(self, profile: Profile) -> Profile:
        """Write per-Profile fields back from the UI."""
        profile.jump_while_attacking = self._jump_attacking_check.isChecked()
        profile.potion_hotkey = self._potion_hotkey_edit.text()
        profile.potion_health_threshold = self._potion_threshold_spin.value()
        profile.collect_loot = self._collect_loot_check.isChecked()
        profile.loot_hotkey = self._loot_hotkey_edit.text()
        profile.stop_bot_on_death = self._stop_on_death_check.isChecked()
        profile.run_back_after_death = self._run_back_check.isChecked()
        profile.run_back_seconds = self._run_back_spin.value()
        return profile

    def set_tesseract_status(self, path: str | None) -> None:
        """Show the tesseract status on the Window tab."""
        if path:
            self._tesseract_status.setText(f"Found: {path}")
            self._tesseract_status.setStyleSheet("color: #a6e3a1;")
        else:
            self._tesseract_status.setText("Not Found — install Tesseract-OCR or place tesseract.exe in resources/tesseract/")
            self._tesseract_status.setStyleSheet("color: #f38ba8;")

    def set_enabled_state(self, enabled: bool) -> None:
        """Enable/disable all inputs (for when bot is running)."""
        for btn in self._location_buttons:
            btn.setEnabled(enabled)
        self._jump_attacking_check.setEnabled(enabled)
        self._jump_moving_check.setEnabled(enabled)
        self._potion_hotkey_edit.setEnabled(enabled)
        self._potion_threshold_spin.setEnabled(enabled)
        self._collect_loot_check.setEnabled(enabled)
        self._loot_hotkey_edit.setEnabled(enabled)
        self._stop_on_death_check.setEnabled(enabled)
        self._run_back_check.setEnabled(enabled)
        self._run_back_spin.setEnabled(enabled and self._run_back_check.isChecked())
        self._movement_loops_spin.setEnabled(enabled)
        for cb in self._movement_key_checks.values():
            cb.setEnabled(enabled)
        self._no_enemy_spin.setEnabled(enabled)
        self._max_runtime_spin.setEnabled(enabled)
        self._afk_interval_spin.setEnabled(enabled)
        self._afk_duration_spin.setEnabled(enabled)
        self._focus_check.setEnabled(enabled)
        self._stay_on_top_check.setEnabled(enabled)
        self._minimize_to_tray_check.setEnabled(enabled)

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _toggle_run_back(self) -> None:
        self._run_back_spin.setEnabled(self._run_back_check.isChecked())

    def _pick_location(self, key: str, mode: str) -> None:
        """Open the overlay and capture coordinates."""
        main_window = self.window()
        main_window.hide()

        overlay = OverlayWindow()
        if mode == "area":
            result = overlay.get_area()
        else:
            result = overlay.get_point()

        main_window.show()
        main_window.raise_()

        if result is not None:
            self._locations[key]["value"] = result
            self._locations[key]["label"].setText(str(result))
            self.settings_changed.emit()
