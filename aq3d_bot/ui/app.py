from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt, QObject, QTimer, Signal, Slot
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QComboBox, QStackedWidget, QMessageBox, QSystemTrayIcon, QMenu,
    QApplication,
)


class _HotkeyBridge(QObject):
    """Thread-safe bridge for hotkey callbacks.

    The keyboard module fires callbacks from its own thread.
    QTimer.singleShot doesn't work from non-Qt threads.
    Qt signals ARE thread-safe — emitting from any thread queues
    delivery to the receiver's event loop.
    """

    start_requested = Signal()
    stop_requested = Signal()

from ..core.engine import BotEngine
from ..core.game_window import AQ3DWindow
from ..core.ocr import OCREngine
from ..models.migration import migrate, needs_migration
from ..models.profile import Profile
from ..models.settings import GlobalSettings
from .pages.about import AboutPage
from .pages.combat import CombatPage
from .pages.dashboard import DashboardPage
from .pages.profiles import ProfilesPage
from .pages.settings import SettingsPage


def _resource_path(relative: str) -> str:
    """Resolve a resource path for both dev and PyInstaller."""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


class MainWindow(QMainWindow):
    """Main application window with sidebar navigation and profile switching."""

    APP_VERSION = "4.0.0"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"DeadLink's AQ3D Bot [v{self.APP_VERSION}]")
        self.setMinimumSize(800, 550)
        self.resize(900, 600)

        # Load icon
        icon_path = _resource_path(os.path.join("resources", "icons", "logo.ico"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Load stylesheet
        qss_path = _resource_path(os.path.join("ui", "styles", "theme.qss"))
        if os.path.exists(qss_path):
            with open(qss_path, "r") as f:
                self.setStyleSheet(f.read())

        # --- Data ---
        self._profiles_dir = "profiles"
        self._settings_path = "settings.json"
        self._settings = GlobalSettings()
        self._current_profile = Profile()
        self._settings_modified = False
        self._engine: BotEngine | None = None
        self._game = AQ3DWindow()
        self._hotkey_listener = None

        # --- Run migration if needed ---
        self._run_migration()

        # --- Load data ---
        self._settings = GlobalSettings.load(self._settings_path)
        profiles = Profile.list_profiles(self._profiles_dir)
        if profiles:
            self._current_profile = Profile.load(profiles[0], self._profiles_dir)
        else:
            self._current_profile = Profile(name="Default")
            self._current_profile.save(self._profiles_dir)

        # --- Build UI ---
        self._build_ui()

        # --- Load data into UI ---
        self._load_all_into_ui()

        # --- Apply stay on top from saved settings ---
        self._apply_stay_on_top(self._settings.stay_on_top)

        # --- Tesseract status ---
        self._check_tesseract()

        # --- Hotkeys ---
        self._setup_hotkeys()

        # --- System tray ---
        self._setup_tray()

        # --- AQ3D status check timer ---
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._check_aq3d_status)
        self._status_timer.start(5000)
        self._check_aq3d_status()

    # --- UI Construction ---

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Sidebar ---
        sidebar = QWidget()
        sidebar.setObjectName("nav_frame")
        sidebar.setFixedWidth(180)
        nav_layout = QVBoxLayout(sidebar)
        nav_layout.setContentsMargins(10, 10, 10, 10)
        nav_layout.setSpacing(6)

        title = QLabel("AQ3D Bot")
        title.setObjectName("nav_title")
        nav_layout.addWidget(title)

        # Profile selector
        nav_layout.addWidget(QLabel("Profile:"))
        self._profile_combo = QComboBox()
        self._profile_combo.currentTextChanged.connect(self._on_profile_switched)
        nav_layout.addWidget(self._profile_combo)
        self._refresh_profile_combo()

        # Start / Stop / Save
        self._start_btn = QPushButton("Start (F5)")
        self._start_btn.setObjectName("btn_start")
        self._start_btn.clicked.connect(self._start_bot)
        nav_layout.addWidget(self._start_btn)

        self._stop_btn = QPushButton("Stop (F6)")
        self._stop_btn.setObjectName("btn_stop")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_bot)
        nav_layout.addWidget(self._stop_btn)

        self._save_btn = QPushButton("Save Settings")
        self._save_btn.setObjectName("btn_save")
        self._save_btn.clicked.connect(self._save_all)
        nav_layout.addWidget(self._save_btn)

        # AQ3D status
        self._aq3d_status = QLabel("AQ3D: —")
        self._aq3d_status.setStyleSheet("font-size: 11px; color: #6c7086;")
        nav_layout.addWidget(self._aq3d_status)

        nav_layout.addSpacing(8)

        # Navigation buttons — 5 pages
        self._nav_buttons: dict[str, QPushButton] = {}
        pages = ["Dashboard", "Combat", "Settings", "Profiles", "About"]
        for name in pages:
            btn = QPushButton(name)
            btn.setObjectName("nav_button")
            btn.clicked.connect(lambda checked=False, n=name: self._show_page(n))
            nav_layout.addWidget(btn)
            self._nav_buttons[name] = btn

        nav_layout.addStretch()
        main_layout.addWidget(sidebar)

        # --- Content area ---
        self._stack = QStackedWidget()
        main_layout.addWidget(self._stack, stretch=1)

        # Create pages
        self._dashboard_page = DashboardPage()
        self._combat_page = CombatPage()
        self._settings_page = SettingsPage()
        self._profiles_page = ProfilesPage(self._profiles_dir)
        self._about_page = AboutPage()

        content_wrapper_margin = 16
        for page in [
            self._dashboard_page, self._combat_page,
            self._settings_page, self._profiles_page, self._about_page,
        ]:
            wrapper = QWidget()
            wrapper_layout = QVBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(
                content_wrapper_margin, content_wrapper_margin,
                content_wrapper_margin, content_wrapper_margin
            )
            wrapper_layout.addWidget(page)
            self._stack.addWidget(wrapper)

        # Connect settings_changed signals
        self._combat_page.settings_changed.connect(self._mark_modified)
        self._settings_page.settings_changed.connect(self._mark_modified)
        self._profiles_page.profile_switched.connect(self._on_profile_switched)
        self._profiles_page.profiles_list_changed.connect(self._refresh_profile_combo)

        self._show_page("Dashboard")

    # --- Navigation ---

    def _show_page(self, name: str) -> None:
        page_map = {
            "Dashboard": 0, "Combat": 1, "Settings": 2,
            "Profiles": 3, "About": 4,
        }
        idx = page_map.get(name, 0)
        self._stack.setCurrentIndex(idx)

        for btn_name, btn in self._nav_buttons.items():
            btn.setProperty("active", btn_name == name)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # --- Profile Management ---

    def _refresh_profile_combo(self) -> None:
        self._profile_combo.blockSignals(True)
        self._profile_combo.clear()
        names = Profile.list_profiles(self._profiles_dir)
        for name in names:
            self._profile_combo.addItem(name)
        idx = self._profile_combo.findText(self._current_profile.name)
        if idx >= 0:
            self._profile_combo.setCurrentIndex(idx)
        self._profile_combo.blockSignals(False)

    @Slot(str)
    def _on_profile_switched(self, name: str) -> None:
        if not name or name == self._current_profile.name:
            return

        if self._settings_modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f"Save changes to profile '{self._current_profile.name}' before switching?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                self._refresh_profile_combo()
                return
            if reply == QMessageBox.StandardButton.Yes:
                self._save_all()

        self._current_profile = Profile.load(name, self._profiles_dir)
        self._combat_page.load_profile(self._current_profile)
        self._settings_page.load_profile(self._current_profile)
        self._dashboard_page.cooldown_panel.set_skills(self._current_profile.skills)
        self._refresh_profile_combo()
        self._profiles_page.refresh_list(name)
        self._settings_modified = False
        self._update_save_button()

        if self._engine and self._engine.isRunning():
            self._engine.update_profile(self._current_profile)

        self._dashboard_page.log_viewer.append_log(
            f"Switched to profile: {name}", "SUCCESS"
        )

    # --- Settings Management ---

    def _mark_modified(self) -> None:
        self._settings_modified = True
        self._update_save_button()

    def _update_save_button(self) -> None:
        if self._settings_modified:
            self._save_btn.setText("Save Settings *")
            self._save_btn.setProperty("modified", True)
        else:
            self._save_btn.setText("Save Settings")
            self._save_btn.setProperty("modified", False)
        self._save_btn.style().unpolish(self._save_btn)
        self._save_btn.style().polish(self._save_btn)

    def _save_all(self) -> None:
        # Gather from pages
        self._settings = self._settings_page.save_to_settings(self._settings)
        self._current_profile = self._settings_page.save_to_profile(self._current_profile)
        self._current_profile = self._combat_page.save_to_profile(self._current_profile)

        # Save to disk
        self._settings.save(self._settings_path)
        self._current_profile.save(self._profiles_dir)

        self._settings_modified = False
        self._update_save_button()

        # Apply stay on top
        self._apply_stay_on_top(self._settings.stay_on_top)

        # Update engine if running
        if self._engine and self._engine.isRunning():
            self._engine.update_settings(self._settings)
            self._engine.update_profile(self._current_profile)

        self._dashboard_page.log_viewer.append_log("Settings saved.", "SUCCESS")

    def _load_all_into_ui(self) -> None:
        self._settings_page.load_settings(self._settings)
        self._settings_page.load_profile(self._current_profile)
        self._combat_page.load_profile(self._current_profile)
        self._profiles_page.refresh_list(self._current_profile.name)
        self._dashboard_page.cooldown_panel.set_skills(self._current_profile.skills)

    # --- Stay On Top ---

    def _apply_stay_on_top(self, enabled: bool) -> None:
        """Toggle the WindowStaysOnTopHint flag."""
        flags = self.windowFlags()
        if enabled:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    # --- Bot Control ---

    def _start_bot(self) -> None:
        if self._engine and self._engine.isRunning():
            return

        if not self._settings.enemy_name_box:
            QMessageBox.warning(self, "Missing Config", "Set the Enemy Name Area first (Settings > Screen Regions).")
            return

        if self._settings_modified:
            reply = QMessageBox.question(
                self, "Unsaved Settings", "Save settings before starting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._save_all()

        if not self._game.is_game_running():
            QMessageBox.warning(self, "AQ3D Not Running", "AQ3D is not running. Start the game first.")
            return

        self._set_inputs_enabled(False)
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)

        self._engine = BotEngine(self._settings, self._current_profile)
        self._engine.state_changed.connect(self._dashboard_page.on_state_changed)
        self._engine.enemy_detected.connect(self._dashboard_page.on_enemy_detected)
        self._engine.health_updated.connect(self._dashboard_page.on_health_updated)
        self._engine.skill_used.connect(self._dashboard_page.cooldown_panel.on_skill_used)
        self._engine.log_message.connect(self._dashboard_page.log_viewer.append_log)
        self._engine.ocr_snapshot.connect(self._dashboard_page.ocr_panel.on_ocr_snapshot)
        self._engine.kill_count_updated.connect(self._dashboard_page.on_kill_count_updated)
        self._engine.bot_stopped.connect(self._on_bot_stopped)
        self._engine.finished.connect(self._on_engine_finished)

        self._engine.start()
        self._dashboard_page.start_runtime_timer()
        self._show_page("Dashboard")

    def _stop_bot(self) -> None:
        if self._engine and self._engine.isRunning():
            self._engine.request_stop()

    @Slot(str)
    def _on_bot_stopped(self, reason: str) -> None:
        self._dashboard_page.log_viewer.append_log(
            f"Bot stopped: {reason}", "WARNING"
        )

    @Slot()
    def _on_engine_finished(self) -> None:
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._set_inputs_enabled(True)
        self._dashboard_page.stop_runtime_timer()
        self._engine = None

    def _set_inputs_enabled(self, enabled: bool) -> None:
        self._combat_page.set_enabled_state(enabled)
        self._settings_page.set_enabled_state(enabled)
        self._profile_combo.setEnabled(enabled)

    # --- AQ3D Status ---

    def _check_aq3d_status(self) -> None:
        running = self._game.is_game_running()
        if running:
            self._aq3d_status.setText("AQ3D: Running")
            self._aq3d_status.setStyleSheet("font-size: 11px; color: #a6e3a1;")
        else:
            self._aq3d_status.setText("AQ3D: Not Running")
            self._aq3d_status.setStyleSheet("font-size: 11px; color: #f38ba8;")

    # --- Tesseract Status ---

    def _check_tesseract(self) -> None:
        """Check if tesseract is available and update the settings page."""
        ocr = OCREngine()
        if ocr.is_ready:
            path = ocr.tesseract_path
            self._settings_page.set_tesseract_status(path)
        else:
            self._settings_page.set_tesseract_status(None)

    # --- Hotkeys ---

    def _setup_hotkeys(self) -> None:
        """Register F5/F6 global hotkeys using the keyboard module.

        Uses a QObject signal bridge because keyboard callbacks fire
        from a non-Qt thread where QTimer.singleShot doesn't work.
        """
        try:
            import keyboard

            self._hotkey_bridge = _HotkeyBridge(self)
            self._hotkey_bridge.start_requested.connect(self._start_bot)
            self._hotkey_bridge.stop_requested.connect(self._stop_bot)

            keyboard.unhook_all()
            keyboard.add_hotkey("f5", self._hotkey_bridge.start_requested.emit)
            keyboard.add_hotkey("f6", self._hotkey_bridge.stop_requested.emit)
            self._dashboard_page.log_viewer.append_log(
                "Hotkeys F5 (Start) / F6 (Stop) registered.", "INFO"
            )
        except Exception as e:
            self._dashboard_page.log_viewer.append_log(
                f"Failed to register hotkeys: {e}. Try running as administrator.", "ERROR"
            )

    # --- System Tray ---

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self._tray = QSystemTrayIcon(self)
        icon_path = _resource_path(os.path.join("resources", "icons", "logo.ico"))
        if os.path.exists(icon_path):
            self._tray.setIcon(QIcon(icon_path))

        menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self._show_from_tray)
        menu.addAction(show_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_from_tray)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_from_tray(self) -> None:
        if self._engine and self._engine.isRunning():
            reply = QMessageBox.question(
                self, "Bot Running",
                "Bot is still running. Stop and quit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            self._stop_bot()
            self._engine.wait(3000)

        self._cleanup()
        QApplication.quit()

    # --- Migration ---

    def _run_migration(self) -> None:
        if needs_migration(self._settings_path, self._profiles_dir):
            try:
                settings, profile = migrate(self._settings_path, self._profiles_dir)
                self._settings = settings
                self._current_profile = profile
                self._dashboard_page.log_viewer.append_log(
                    "Migration complete: old settings converted to new format.", "SUCCESS"
                )
            except Exception as e:
                self._dashboard_page.log_viewer.append_log(
                    f"Migration failed: {e}", "ERROR"
                )

    # --- Close handling ---

    def closeEvent(self, event) -> None:
        if self._settings.minimize_to_tray_on_close and hasattr(self, "_tray") and self._tray.isVisible():
            event.ignore()
            self.hide()
            self._tray.showMessage(
                "AQ3D Bot",
                "Bot minimized to system tray. Double-click to restore.",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
        else:
            self._handle_close(event)

    def _handle_close(self, event=None) -> None:
        if self._engine and self._engine.isRunning():
            reply = QMessageBox.question(
                self, "Bot Running",
                "Bot is running. Stop and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                if event:
                    event.ignore()
                return
            self._stop_bot()
            self._engine.wait(3000)

        if self._settings_modified:
            reply = QMessageBox.question(
                self, "Unsaved Settings", "Save settings before closing?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._save_all()

        self._cleanup()
        if event:
            event.accept()

    def _cleanup(self) -> None:
        try:
            import keyboard
            keyboard.unhook_all()
        except Exception:
            pass
        if hasattr(self, "_tray"):
            self._tray.hide()
