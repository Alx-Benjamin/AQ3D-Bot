from __future__ import annotations

import random
import time

import pyautogui
from PySide6.QtCore import QMutex, QThread, Signal

from ..models.profile import Profile
from ..models.settings import GlobalSettings
from .afk import AFKManager
from .combat import SkillRotation, TargetFinder
from .death import DeathHandler
from .game_window import AQ3DWindow
from .health import HealthMonitor
from .movement import RandomMover
from .ocr import OCREngine
from .states import BotState


class BotEngine(QThread):
    """Core bot engine running as a QThread with a state machine.

    Emits signals for UI updates — all communication with the UI is
    done through Qt signals (thread-safe).
    """

    # --- Signals ---
    state_changed = Signal(str)       # BotState.value
    enemy_detected = Signal(str)      # enemy name or ""
    health_updated = Signal(int)      # health % (0-100) or -1
    skill_used = Signal(int, float)   # skill slot index, cooldown duration
    log_message = Signal(str, str)    # message, level
    ocr_snapshot = Signal(str, object, str)  # region_name, PIL Image, ocr_text
    kill_count_updated = Signal(int)  # total kills
    bot_stopped = Signal(str)         # reason

    def __init__(
        self,
        settings: GlobalSettings,
        profile: Profile,
        parent=None,
    ):
        super().__init__(parent)
        self._settings = settings
        self._profile = profile

        # Subsystems
        self._ocr = OCREngine()
        self._game = AQ3DWindow()
        self._health = HealthMonitor(self._ocr)
        self._death = DeathHandler(self._ocr)
        self._target = TargetFinder(self._ocr)
        self._skills = SkillRotation()
        self._mover = RandomMover()
        self._afk = AFKManager()

        # State
        self._state = BotState.IDLE
        self._kill_count = 0
        self._last_enemy_time = 0.0
        self._start_time = 0.0

        # Thread-safe stop flag
        self._stop_mutex = QMutex()
        self._should_stop = False

    # --- Public API (called from UI thread) ---

    def update_profile(self, profile: Profile) -> None:
        """Hot-swap the active profile (thread-safe — data is read atomically)."""
        self._profile = profile

    def update_settings(self, settings: GlobalSettings) -> None:
        """Update global settings while running."""
        self._settings = settings

    def request_stop(self) -> None:
        """Request the bot to stop (thread-safe)."""
        self._stop_mutex.lock()
        self._should_stop = True
        self._stop_mutex.unlock()

    # --- Internal helpers ---

    def _is_running(self) -> bool:
        self._stop_mutex.lock()
        running = not self._should_stop
        self._stop_mutex.unlock()
        return running

    def _set_state(self, state: BotState) -> None:
        self._state = state
        self.state_changed.emit(state.value)

    def _log(self, message: str, level: str = "INFO") -> None:
        self.log_message.emit(message, level)

    def _emit_ocr_preview(self, region_name: str, bbox: tuple) -> None:
        """Capture and emit an OCR preview snapshot for the dashboard."""
        try:
            text, raw, processed = self._ocr.snapshot_region(bbox)
            self.ocr_snapshot.emit(region_name, raw, text)
        except Exception:
            pass

    # --- Main loop ---

    def run(self) -> None:
        """Main bot loop — runs in a separate thread."""
        self._should_stop = False
        self._kill_count = 0
        self._start_time = time.time()
        self._last_enemy_time = time.time()
        self._skills.reset()
        self._afk.reset()

        self._set_state(BotState.SEARCHING)
        self._log("Bot started.", "SUCCESS")

        # Startup diagnostics
        if self._ocr.is_ready:
            self._log(f"Tesseract: OK ({self._ocr.tesseract_path})", "INFO")
        else:
            self._log("Tesseract: NOT FOUND — OCR will not work!", "ERROR")

        if self._settings.enemy_name_box:
            self._log(f"Enemy name region: {self._settings.enemy_name_box}", "DEBUG")
        else:
            self._log("Enemy name region: NOT SET", "ERROR")

        try:
            while self._is_running():
                # --- Check AQ3D is running ---
                if not self._game.is_game_running():
                    self._log("AQ3D is no longer running. Stopping.", "ERROR")
                    self.bot_stopped.emit("AQ3D closed")
                    break

                # --- Focus window ---
                if self._settings.focus_aq3d_enabled:
                    if not self._game.focus():
                        self._log("Failed to focus AQ3D window. Retrying...", "WARNING")
                        time.sleep(3)
                        continue

                # --- Timeout checks ---
                if self._check_timeouts():
                    break

                # --- AFK check ---
                if self._afk.should_start_afk(self._settings.afk_interval_minutes):
                    self._handle_afk()
                    continue

                # --- State machine ---
                if self._state in (BotState.SEARCHING, BotState.MOVING):
                    self._do_search()
                elif self._state == BotState.ATTACKING:
                    self._do_attack()
                elif self._state == BotState.LOOTING:
                    self._do_loot()
                elif self._state == BotState.DEAD:
                    self._do_death()
                elif self._state == BotState.REVIVING:
                    self._do_revive()
                elif self._state == BotState.RUNNING_BACK:
                    self._do_run_back()
                else:
                    self._set_state(BotState.SEARCHING)

                time.sleep(random.uniform(0.1, 0.3))

        except Exception as e:
            self._log(f"CRITICAL ERROR: {e}", "ERROR")
            self.bot_stopped.emit(f"Error: {e}")
        finally:
            self._set_state(BotState.IDLE)
            self._log("Bot stopped.", "SUCCESS")

    # --- State handlers ---

    def _do_search(self) -> None:
        """SEARCHING: tab-target to find an enemy."""
        self._set_state(BotState.SEARCHING)
        profile = self._profile
        settings = self._settings

        if not settings.enemy_name_box:
            self._log("Enemy name area not configured.", "ERROR")
            self.bot_stopped.emit("Enemy name area not set")
            self.request_stop()
            return

        name = self._target.find_target(
            settings.enemy_name_box,
            profile.target_enemy_names,
            is_running=self._is_running,
            log=self._log,
        )

        # Emit OCR preview for the enemy name region
        self._emit_ocr_preview("enemy_name", settings.enemy_name_box)

        if name:
            self._log(f"Target '{name}' found. Attacking.", "INFO")
            self.enemy_detected.emit(name)
            self._last_enemy_time = time.time()
            self._set_state(BotState.ATTACKING)
        else:
            self._log("No matching enemy found. Moving.", "INFO")
            self.enemy_detected.emit("")
            self._set_state(BotState.MOVING)
            self._mover.move(
                settings.movement_keys,
                settings.movement_loops,
                settings.jump_while_moving,
                self._is_running,
            )
            self._set_state(BotState.SEARCHING)

    def _do_attack(self) -> None:
        """ATTACKING: use skills on the current target until it dies or is lost."""
        self._set_state(BotState.ATTACKING)
        profile = self._profile
        settings = self._settings
        start = time.time()
        attack_timeout = 90  # seconds

        while self._is_running() and (time.time() - start < attack_timeout):
            # Check if target is still alive
            if not self._target.is_target_alive(settings.enemy_name_box):
                self._log("Target defeated.", "SUCCESS")
                self._kill_count += 1
                self.kill_count_updated.emit(self._kill_count)
                self.enemy_detected.emit("")
                if profile.collect_loot:
                    self._set_state(BotState.LOOTING)
                else:
                    self._set_state(BotState.SEARCHING)
                return

            self._last_enemy_time = time.time()

            # Execute next rotation step
            skill = self._skills.execute_next_step(
                profile.skills,
                profile.rotation,
                profile.delay_min,
                profile.delay_max,
                self._is_running,
            )
            if skill:
                # Find the skill's slot index for the UI
                try:
                    skill_index = profile.skills.index(skill)
                except ValueError:
                    skill_index = 0
                self.skill_used.emit(skill_index, skill.cooldown)

            # Random jump while attacking
            if profile.jump_while_attacking and random.random() < 0.25:
                pyautogui.press("space")

            # Check for death mid-combat
            if self._death.is_dead(settings.revive_box):
                self._set_state(BotState.DEAD)
                return

            # Check health / potions
            health = self._health.use_potion_if_needed(
                settings.player_health_box,
                profile.potion_hotkey,
                profile.potion_health_threshold,
            )
            if health is not None:
                self.health_updated.emit(health)

            # Periodic OCR preview updates (every ~3 seconds)
            if int(time.time() - start) % 3 == 0:
                self._emit_ocr_preview("enemy_name", settings.enemy_name_box)
                if settings.player_health_box:
                    self._emit_ocr_preview("health", settings.player_health_box)

            time.sleep(random.uniform(0.1, 0.2))

        # Attack timed out — target lost
        self._log("Attack timed out. Target lost.", "WARNING")
        self.enemy_detected.emit("")
        self._set_state(BotState.SEARCHING)

    def _do_loot(self) -> None:
        """LOOTING: collect loot from a defeated enemy."""
        self._set_state(BotState.LOOTING)
        profile = self._profile
        settings = self._settings

        if profile.loot_hotkey:
            pyautogui.press(profile.loot_hotkey)
            time.sleep(0.3)
            pyautogui.press(profile.loot_hotkey)
            time.sleep(0.3)
            pyautogui.press("esc")
            time.sleep(0.3)

        if settings.menu_close_point:
            pyautogui.click(*settings.menu_close_point)
            time.sleep(0.2)

        self._set_state(BotState.SEARCHING)

    def _do_death(self) -> None:
        """DEAD: detected death, transition to reviving."""
        self._set_state(BotState.DEAD)
        self._log("Player died.", "WARNING")
        self.enemy_detected.emit("")

        profile = self._profile
        if profile.stop_bot_on_death:
            self._log("Stop-on-death enabled. Stopping.", "INFO")
            self.bot_stopped.emit("Player died")
            self.request_stop()
            return

        self._set_state(BotState.REVIVING)

    def _do_revive(self) -> None:
        """REVIVING: click the revive button."""
        self._set_state(BotState.REVIVING)
        settings = self._settings

        if not settings.revive_box:
            self._log("Revive area not configured. Stopping.", "ERROR")
            self.bot_stopped.emit("Revive area not set")
            self.request_stop()
            return

        self._log("Clicking revive...", "INFO")
        self._death.click_revive(settings.revive_box, is_running=self._is_running)

        profile = self._profile
        if profile.run_back_after_death:
            self._set_state(BotState.RUNNING_BACK)
        else:
            self._set_state(BotState.SEARCHING)

    def _do_run_back(self) -> None:
        """RUNNING_BACK: hold W to return to combat area."""
        self._set_state(BotState.RUNNING_BACK)
        profile = self._profile
        self._log(f"Running back for {profile.run_back_seconds}s...", "INFO")
        self._death.run_back(profile.run_back_seconds, is_running=self._is_running)
        self._set_state(BotState.SEARCHING)

    def _handle_afk(self) -> None:
        """Enter AFK mode for the configured duration.

        During AFK, if the player is attacked (enemy name visible or health drops),
        the bot fights back using the normal rotation until the enemy is dead,
        then resumes AFK.
        """
        self._set_state(BotState.AFK)
        duration = min(self._settings.afk_duration_minutes, 15)
        self._log(f"Entering AFK for {duration} minutes.", "INFO")

        settings = self._settings
        profile = self._profile
        end_time = time.time() + duration * 60
        revive_pending = False

        while self._is_running() and time.time() < end_time:
            # Check for death
            if settings.revive_box and self._death.is_dead(settings.revive_box):
                self._death.click_revive(settings.revive_box, is_running=self._is_running)
                revive_pending = True

            # Check if being attacked (enemy name visible)
            under_attack = False
            if settings.enemy_name_box:
                name = self._ocr.read_enemy_name(settings.enemy_name_box)
                if name:
                    under_attack = True

            # Also check health dropping as a secondary signal
            if not under_attack and settings.player_health_box:
                health = self._health.get_health_percentage(settings.player_health_box)
                if health is not None and health < 95:
                    under_attack = True

            if under_attack:
                self._log("Under attack during AFK! Fighting back.", "WARNING")
                self._set_state(BotState.ATTACKING)
                self._afk_combat()
                self._set_state(BotState.AFK)
                self._log("Combat over, resuming AFK.", "INFO")

            time.sleep(1)

        self._afk.finish_afk()
        self._log("AFK period ended.", "INFO")

        if revive_pending and profile.run_back_after_death:
            self._log("Performing deferred run-back after AFK.", "INFO")
            self._death.run_back(profile.run_back_seconds, is_running=self._is_running)

        self._set_state(BotState.SEARCHING)

    def _afk_combat(self) -> None:
        """Fight back during AFK — use rotation until the enemy is dead."""
        profile = self._profile
        settings = self._settings
        start = time.time()
        attack_timeout = 60

        while self._is_running() and (time.time() - start < attack_timeout):
            if not self._target.is_target_alive(settings.enemy_name_box):
                self._log("AFK threat neutralized.", "SUCCESS")
                self._kill_count += 1
                self.kill_count_updated.emit(self._kill_count)
                self.enemy_detected.emit("")
                return

            skill = self._skills.execute_next_step(
                profile.skills, profile.rotation,
                profile.delay_min, profile.delay_max,
                self._is_running,
            )
            if skill:
                try:
                    idx = profile.skills.index(skill)
                except ValueError:
                    idx = 0
                self.skill_used.emit(idx, skill.cooldown)

            if self._death.is_dead(settings.revive_box):
                self._do_death()
                return

            health = self._health.use_potion_if_needed(
                settings.player_health_box, profile.potion_hotkey,
                profile.potion_health_threshold,
            )
            if health is not None:
                self.health_updated.emit(health)

            time.sleep(random.uniform(0.1, 0.2))

        self.enemy_detected.emit("")

    def _check_timeouts(self) -> bool:
        """Check runtime and no-enemy timeouts. Returns True if bot should stop."""
        settings = self._settings
        elapsed = time.time() - self._start_time

        # Max runtime
        if settings.max_runtime_hours > 0:
            max_seconds = settings.max_runtime_hours * 3600
            if elapsed >= max_seconds:
                self._log(f"Max runtime ({settings.max_runtime_hours}h) reached. Stopping.", "INFO")
                self.bot_stopped.emit("Max runtime reached")
                self.request_stop()
                return True

        # No enemy timeout
        if settings.no_enemy_timeout_minutes > 0:
            timeout_seconds = settings.no_enemy_timeout_minutes * 60
            if (time.time() - self._last_enemy_time) > timeout_seconds:
                self._log(f"No enemy timeout ({settings.no_enemy_timeout_minutes}m) reached. Stopping.", "WARNING")
                self.bot_stopped.emit("No enemy timeout")
                self.request_stop()
                return True

        return False
