import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
import pyautogui
import psutil
from PIL import ImageGrab
import random
import time
import threading
import json
import os
import win32gui
import win32con

class Overlay(tk.Toplevel):
    def __init__(self, root):
        super().__init__(root)
        self.title("Click to set location")
        self.attributes('-fullscreen', True)
        self.attributes('-topmost', True)
        self.attributes('-alpha', 0.3)
        self.configure(bg='black')
        self.bind("<Button-1>", self.on_click)
        self.clicked_coords = None
        self.geometry("300x200")

    def on_click(self, event):
        self.clicked_coords = (event.x_root, event.y_root)
        self.destroy()

    def get_coords(self):
        self.wait_window(self)
        return self.clicked_coords

class BotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DeadLink's AQ3D Bot [Discord: DeadLink404]")
        self.root.attributes('-topmost', True)
        ctk.set_appearance_mode("dark")

        # Bot Settings
        self.aq3d_running = False
        self.health_box = None
        self.loot_button_location = None
        self.movement_keys = ['w', 'a', 's', 'd']
        self.movement_loops = 5
        self.player_health_box = None
        self.potion_hotkey = 'p'
        self.detect_revive_box = None
        self.revive_button_location = None
        self.collect_loot = tk.BooleanVar(value=True)
        self.jump_while_moving = tk.BooleanVar()
        self.jump_while_attacking = tk.BooleanVar()

        # Skill Settings
        self.skill_names = ["Basic Attack", "Skill 1", "Skill 2", "Skill 3", "Skill 4", "Cross Skill"]
        self.skill_keys = ['1', '2', '3', '4', '5', '6']
        self.skill_cooldowns = [0, 5, 10, 15, 20, 25]
        self.skill_enabled = [True, True, True, True, True, True]
        self.last_skill_use_time = [0] * len(self.skill_names)

        # Timeout Settings
        self.no_enemy_timeout_minutes = 5
        self.max_runtime_hours = 0

        # Bot State
        self.bot_start_time = 0
        self.bot_running = False
        self.last_enemy_detection_time = time.time()
        self.settings_modified = False

        # GUI Frames
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        frame_width = 300

        status_frame = ctk.CTkFrame(root, width=frame_width)
        status_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        location_frame = ctk.CTkFrame(root, width=frame_width)
        location_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        skill_settings_frame = ctk.CTkFrame(root, width=frame_width)
        skill_settings_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        settings_frame = ctk.CTkFrame(root, width=frame_width)
        settings_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

        action_frame = ctk.CTkFrame(root, width=frame_width)
        action_frame.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")

        log_frame = ctk.CTkFrame(root)
        log_frame.grid(row=0, column=1, rowspan=5, padx=10, pady=10, sticky="nsew")

        # Status Frame
        self.aq3d_status_label = ctk.CTkLabel(status_frame, text="Not Running")
        self.aq3d_status_label.grid(row=1, column=1, padx=5)
        ctk.CTkLabel(status_frame, text="AQ3D Status:").grid(row=1, column=0, padx=5)
        ctk.CTkButton(status_frame, text="Save All Settings",
                      command=self.save_all_settings).grid(row=2, column=0, columnspan=2, pady=5)

        # Location Frame
        self.health_location_label = ctk.CTkLabel(location_frame, text=f"Enemy Health Location: Not Set")
        self.health_location_label.grid(row=1, column=1, padx=5)
        ctk.CTkButton(location_frame, text="Set Enemy Health Location",
                     command=self.set_health_location).grid(row=1, column=0, padx=5)

        self.player_health_location_label = ctk.CTkLabel(location_frame,
                                                        text=f"Player Health Location: Not Set")
        self.player_health_location_label.grid(row=2, column=1, padx=5)
        ctk.CTkButton(location_frame, text="Set Player Health Location",
                     command=self.set_player_health_location).grid(row=2, column=0, padx=5)

        self.loot_location_label = ctk.CTkLabel(location_frame, text=f"Loot Button Location: Not Set")
        self.loot_location_label.grid(row=3, column=1, padx=5)
        ctk.CTkButton(location_frame, text="Set Loot Button Location",
                     command=self.set_loot_button_location).grid(row=3, column=0, padx=5)

        self.detect_revive_location_label = ctk.CTkLabel(location_frame,
                                                        text=f"Detect Revive Location: Not Set")
        self.detect_revive_location_label.grid(row=4, column=1, padx=5)
        ctk.CTkButton(location_frame, text="Set Detect Revive Location",
                     command=self.set_detect_revive_location).grid(row=4, column=0, padx=5)

        self.revive_button_location_label = ctk.CTkLabel(location_frame,
                                                        text=f"Revive Button Location: Not Set")
        self.revive_button_location_label.grid(row=5, column=1, padx=5)
        ctk.CTkButton(location_frame, text="Set Revive Button Location",
                     command=self.set_revive_button_location).grid(row=5, column=0, padx=5)

        # Skill Settings Frame
        self.skill_entries = []
        self.skill_cooldown_entries = []
        self.skill_enabled_vars = []
        ctk.CTkLabel(skill_settings_frame, text="Skill").grid(row=0, column=0, padx=5)
        ctk.CTkLabel(skill_settings_frame, text="Hotkey").grid(row=0, column=1, padx=5)
        ctk.CTkLabel(skill_settings_frame, text="Cooldown").grid(row=0, column=2, padx=5)
        ctk.CTkLabel(skill_settings_frame, text="Toggle Skill").grid(row=0, column=3, padx=5)
        for i, skill_name in enumerate(self.skill_names):
            ctk.CTkLabel(skill_settings_frame, text=f"{skill_name}:").grid(row=i + 1, column=0, padx=5, pady=2)

            skill_entry = ctk.CTkEntry(skill_settings_frame, width=50)
            skill_entry.grid(row=i + 1, column=1, padx=5, pady=2)
            skill_entry.insert(0, self.skill_keys[i])
            self.skill_entries.append(skill_entry)

            cooldown_entry = ctk.CTkEntry(skill_settings_frame, width=50)
            cooldown_entry.grid(row=i + 1, column=2, padx=5, pady=2)
            cooldown_entry.insert(0, self.skill_cooldowns[i])
            self.skill_cooldown_entries.append(cooldown_entry)

            skill_enabled_var = tk.BooleanVar(value=self.skill_enabled[i])
            skill_enabled_checkbox = ctk.CTkCheckBox(skill_settings_frame, text="Enabled",
                                                    variable=skill_enabled_var)
            skill_enabled_checkbox.grid(row=i + 1, column=3, padx=5, pady=2)
            self.skill_enabled_vars.append(skill_enabled_var)

        # Settings Frame
        ctk.CTkLabel(settings_frame, text="Movement Buttons:").grid(row=1, column=0)
        self.movement_buttons_entry = ctk.CTkEntry(settings_frame)
        self.movement_buttons_entry.grid(row=1, column=1)
        self.movement_buttons_entry.insert(0, ', '.join(self.movement_keys))

        ctk.CTkLabel(settings_frame, text="Movement Loops:").grid(row=2, column=0)
        self.movement_loops_entry = ctk.CTkEntry(settings_frame)
        self.movement_loops_entry.grid(row=2, column=1)
        self.movement_loops_entry.insert(0, str(self.movement_loops))

        ctk.CTkLabel(settings_frame, text="Potion Hotkey:").grid(row=3, column=0)
        self.potion_hotkey_entry = ctk.CTkEntry(settings_frame)
        self.potion_hotkey_entry.grid(row=3, column=1)
        self.potion_hotkey_entry.insert(0, self.potion_hotkey)

        ctk.CTkLabel(settings_frame, text="No Enemy Timeout (minutes):").grid(row=4, column=0)
        self.no_enemy_timeout_entry = ctk.CTkEntry(settings_frame)
        self.no_enemy_timeout_entry.grid(row=4, column=1)
        self.no_enemy_timeout_entry.insert(0, str(self.no_enemy_timeout_minutes))

        ctk.CTkLabel(settings_frame, text="Max Runtime (hours, 0=forever):").grid(row=5, column=0)
        self.max_runtime_entry = ctk.CTkEntry(settings_frame)
        self.max_runtime_entry.grid(row=5, column=1)
        self.max_runtime_entry.insert(0, str(self.max_runtime_hours))

        # Action Frame
        ctk.CTkCheckBox(action_frame, text="Jump While Moving",
                       variable=self.jump_while_moving).grid(row=0, column=0, columnspan=2)
        ctk.CTkCheckBox(action_frame, text="Jump While Attacking",
                       variable=self.jump_while_attacking).grid(row=1, column=0, columnspan=2)
        ctk.CTkCheckBox(action_frame, text="Collect Loot",
                       variable=self.collect_loot).grid(row=2, column=0, columnspan=2)
        ctk.CTkButton(action_frame, text="Start Bot", command=self.start_bot).grid(row=3, column=0, pady=5)
        self.stop_button = ctk.CTkButton(action_frame, text="Stop Bot", command=self.stop_bot, state="disabled")
        self.stop_button.grid(row=3, column=1, pady=5)

        # Log Frame
        self.log_text = ctk.CTkTextbox(log_frame, width=300, height=200, wrap="word")
        self.log_text.pack(expand=True, fill="both")

        self.timer_label = ctk.CTkLabel(log_frame, text="Bot Runtime: 00:00:00")
        self.timer_label.pack()

        self.load_settings()
        self.check_aq3d_status()
        self.update_gui_elements_from_settings()

    def log(self, message):
        current_time = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{current_time}] {message}\n")
        self.log_text.yview(tk.END)

    def check_aq3d_status(self):
        self.aq3d_running = any(proc.name() == "AQ3D.exe" for proc in psutil.process_iter())
        self.aq3d_status_label.configure(text="Running" if self.aq3d_running else "Not Running")
        self.log("Checked AQ3D status")

    def set_health_location(self):
        self.log("Click on the top-left and bottom-right corners of the enemy health bar")
        overlay = Overlay(self.root)
        top_left = overlay.get_coords()
        if top_left:
            overlay = Overlay(self.root)
            bottom_right = overlay.get_coords()
            if bottom_right:
                self.health_box = (*top_left, *bottom_right)
                self.health_location_label.configure(text=f"Enemy Health Location: {self.health_box}")
                self.log(f"Enemy health area set: {self.health_box}")
                self.settings_modified = True
            else:
                self.log("Operation cancelled")
        else:
            self.log("Operation cancelled")

    def set_player_health_location(self):
        self.log("Click on the top-left and bottom-right corners of the player health bar")
        overlay = Overlay(self.root)
        top_left = overlay.get_coords()
        if top_left:
            overlay = Overlay(self.root)
            bottom_right = overlay.get_coords()
            if bottom_right:
                self.player_health_box = (*top_left, *bottom_right)
                self.player_health_location_label.configure(text=f"Player Health Location: {self.player_health_box}")
                self.log(f"Player health area set: {self.player_health_box}")
                self.settings_modified = True
            else:
                self.log("Operation cancelled")
        else:
            self.log("Operation cancelled")

    def set_loot_button_location(self):
        self.log("Click on the loot button")
        overlay = Overlay(self.root)
        loot_location = overlay.get_coords()
        if loot_location:
            self.loot_button_location = loot_location
            self.loot_location_label.configure(text=f"Loot Button Location: {self.loot_button_location}")
            self.log(f"Loot button location set: {self.loot_button_location}")
            self.settings_modified = True
        else:
            self.log("Operation cancelled")

    def set_detect_revive_location(self):
        self.log("Click on the top-left and bottom-right corners of the area to detect revive button")
        overlay = Overlay(self.root)
        top_left = overlay.get_coords()
        if top_left:
            overlay = Overlay(self.root)
            bottom_right = overlay.get_coords()
            if bottom_right:
                self.detect_revive_box = (*top_left, *bottom_right)
                self.detect_revive_location_label.configure(text=f"Detect Revive Location: {self.detect_revive_box}")
                self.log(f"Detect revive area set: {self.detect_revive_box}")
                self.settings_modified = True
            else:
                self.log("Operation cancelled")
        else:
            self.log("Operation cancelled")

    def set_revive_button_location(self):
        self.log("Click on the revive button")
        overlay = Overlay(self.root)
        revive_location = overlay.get_coords()
        if revive_location:
            self.revive_button_location = revive_location
            self.revive_button_location_label.configure(text=f"Revive Button Location: {self.revive_button_location}")
            self.log(f"Revive button location set: {self.revive_button_location}")
            self.settings_modified = True
        else:
            self.log("Operation cancelled")

    def save_movement_buttons(self):
        self.movement_keys = [key.strip() for key in self.movement_buttons_entry.get().split(',')]
        self.settings_modified = True
        self.log(f"Movement buttons updated: {self.movement_keys}")

    def save_movement_loops(self):
        try:
            self.movement_loops = int(self.movement_loops_entry.get())
            self.settings_modified = True
            self.log(f"Movement loops updated: {self.movement_loops}")
        except ValueError:
            self.log("Invalid input for movement loops")

    def save_potion_hotkey(self):
        self.potion_hotkey = self.potion_hotkey_entry.get().strip()
        self.settings_modified = True
        self.log(f"Potion hotkey updated: {self.potion_hotkey}")

    def save_skill_settings(self):
        self.skill_keys = [entry.get().strip() for entry in self.skill_entries]
        self.skill_cooldowns = [int(entry.get()) if entry.get().isdigit() else 0 for entry in
                                self.skill_cooldown_entries]
        self.skill_enabled = [var.get() for var in self.skill_enabled_vars]
        self.settings_modified = True
        self.log("Skill settings updated.")

    def save_all_settings(self):
        self.save_movement_buttons()
        self.save_movement_loops()
        self.save_potion_hotkey()
        self.save_skill_settings()

        try:
            self.no_enemy_timeout_minutes = int(self.no_enemy_timeout_entry.get())
            self.max_runtime_hours = int(self.max_runtime_entry.get())
            self.settings_modified = True
        except ValueError:
            self.log("Invalid input for timeout or runtime")

        settings = {
            'health_box': self.health_box,
            'player_health_box': self.player_health_box,
            'loot_button_location': self.loot_button_location,
            'movement_keys': self.movement_keys,
            'movement_loops': self.movement_loops,
            'potion_hotkey': self.potion_hotkey,
            'detect_revive_box': self.detect_revive_box,
            'revive_button_location': self.revive_button_location,
            'collect_loot': self.collect_loot.get(),
            'jump_while_moving': self.jump_while_moving.get(),
            'jump_while_attacking': self.jump_while_attacking.get(),
            'skill_keys': self.skill_keys,
            'skill_cooldowns': self.skill_cooldowns,
            'skill_enabled': self.skill_enabled,
            'no_enemy_timeout_minutes': self.no_enemy_timeout_minutes,
            'max_runtime_hours': self.max_runtime_hours
        }
        with open('settings.json', 'w') as f:
            json.dump(settings, f)

        self.settings_modified = False
        self.log("All settings saved.")

    def load_settings(self):
        if os.path.exists('settings.json'):
            with open('settings.json', 'r') as f:
                settings = json.load(f)

            self.health_box = settings.get('health_box')
            self.player_health_box = settings.get('player_health_box')
            self.loot_button_location = settings.get('loot_button_location')
            self.movement_keys = settings.get('movement_keys', ['w', 'a', 's', 'd'])
            self.movement_loops = settings.get('movement_loops', 5)
            self.potion_hotkey = settings.get('potion_hotkey', 'p')
            self.detect_revive_box = settings.get('detect_revive_box')
            self.revive_button_location = settings.get('revive_button_location')
            self.collect_loot.set(settings.get('collect_loot', True))
            self.jump_while_moving.set(settings.get('jump_while_moving', False))
            self.jump_while_attacking.set(settings.get('jump_while_attacking', False))
            self.skill_keys = settings.get('skill_keys', ['1', '2', '3', '4', '5', '6'])
            self.skill_cooldowns = settings.get('skill_cooldowns', [0, 5, 10, 15, 20, 25])
            self.skill_enabled = settings.get('skill_enabled', [True, True, True, True, True, True])
            self.no_enemy_timeout_minutes = settings.get('no_enemy_timeout_minutes', 5)
            self.max_runtime_hours = settings.get('max_runtime_hours', 0)

            self.log("Settings loaded")
        else:
            self.log("No settings file found, using defaults")

    def update_gui_elements_from_settings(self):
        self.health_location_label.configure(
            text=f"Enemy Health Location: {self.health_box if self.health_box else 'Not Set'}")
        self.player_health_location_label.configure(
            text=f"Player Health Location: {self.player_health_box if self.player_health_box else 'Not Set'}")
        self.loot_location_label.configure(
            text=f"Loot Button Location: {self.loot_button_location if self.loot_button_location else 'Not Set'}")
        self.detect_revive_location_label.configure(
            text=f"Detect Revive Location: {self.detect_revive_box if self.detect_revive_box else 'Not Set'}")
        self.revive_button_location_label.configure(
            text=f"Revive Button Location: {self.revive_button_location if self.revive_button_location else 'Not Set'}")
        self.movement_buttons_entry.delete(0, tk.END)
        self.movement_buttons_entry.insert(0, ', '.join(self.movement_keys))
        self.movement_loops_entry.delete(0, tk.END)
        self.movement_loops_entry.insert(0, str(self.movement_loops))
        self.potion_hotkey_entry.delete(0, tk.END)
        self.potion_hotkey_entry.insert(0, self.potion_hotkey)
        for i, skill_key in enumerate(self.skill_keys):
            self.skill_entries[i].delete(0, tk.END)
            self.skill_entries[i].insert(0, skill_key)
        for i, cooldown in enumerate(self.skill_cooldowns):
            self.skill_cooldown_entries[i].delete(0, tk.END)
            self.skill_cooldown_entries[i].insert(0, cooldown)
        for i, enabled in enumerate(self.skill_enabled):
            self.skill_enabled_vars[i].set(enabled)
        self.no_enemy_timeout_entry.delete(0, tk.END)
        self.no_enemy_timeout_entry.insert(0, str(self.no_enemy_timeout_minutes))
        self.max_runtime_entry.delete(0, tk.END)
        self.max_runtime_entry.insert(0, str(self.max_runtime_hours))

    def start_bot(self):
        self.check_aq3d_status()
        if not self.aq3d_running:
            self.log("AQ3D is not running. Start the game before starting the bot.")
            return
        if not self.health_box or not self.loot_button_location or not self.detect_revive_box or not self.revive_button_location:
            self.log("Please set all required locations before starting the bot.")
            return

        if not self.bot_running:
            self.bot_running = True
            self.log("Bot started")
            self.stop_button.configure(state="normal")
            self.bot_thread = threading.Thread(target=self.bot_loop)
            self.bot_thread.daemon = True
            self.bot_thread.start()
            
            self.bot_start_time = time.time()
            self.last_enemy_detection_time = time.time()
            self.update_timer()
        else:
            self.log("Bot is already running.")

    def stop_bot(self):
        self.bot_running = False
        self.stop_button.configure(state="disabled")
        self.log("Bot stopped.")

    def update_timer(self):
        if self.bot_running:
            elapsed_time = int(time.time() - self.bot_start_time)
            hours, remainder = divmod(elapsed_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.timer_label.configure(text=f"Bot Runtime: {hours:02d}:{minutes:02d}:{seconds:02d}")

            if self.max_runtime_hours > 0 and elapsed_time > self.max_runtime_hours * 3600:
                self.log("Max runtime reached, stopping bot.")
                self.stop_bot()

            self.root.after(1000, self.update_timer)

    def bot_loop(self):
        while self.bot_running:
            self.check_aq3d_status()
            if not self.aq3d_running:
                self.log("AQ3D is not running. Stopping the bot.")
                self.stop_bot()
                break
            self.focus_aq3d()
            # Check timeout at the start of each loop iteration
            time_since_last_detection = time.time() - self.last_enemy_detection_time
            if time_since_last_detection > self.no_enemy_timeout_minutes * 60:
                self.log(f"No enemy detected for {self.no_enemy_timeout_minutes} minutes, stopping bot.")
                self.stop_bot()
                break  # Exit the loop if timed out
            self.check_and_handle_death()
            self.select_enemy()
            time.sleep(1)

    def focus_aq3d(self):
        try:
            hwnd = win32gui.FindWindow(None, "AQ3D")
            if not hwnd:
                raise Exception("AQ3D window not found")

            active_hwnd = win32gui.GetForegroundWindow()

            if hwnd != active_hwnd:
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                time.sleep(0.2)
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                win32gui.SetForegroundWindow(hwnd)
                win32gui.SetActiveWindow(hwnd)
                self.log("Focused AQ3D window.")
        except Exception as e:
            self.log(f"Error focusing AQ3D: {e}")

    def select_enemy(self):
        pyautogui.press('tab')
        time.sleep(0.5)
        if self.is_enemy_detected():
            self.attack_enemy()
        else:
            self.move_randomly()

    def is_enemy_detected(self):
        if self.health_box:
            x1, y1, x2, y2 = self.health_box
            screen = ImageGrab.grab(bbox=self.health_box)
            average_color = self.get_average_color(screen)
            target_color = (166, 4, 4)
            tolerance = 30

            if self.is_color_within_tolerance(average_color, target_color, tolerance):
                self.log("Enemy detected")
                self.last_enemy_detection_time = time.time() 
                return True
            else:
                return False
        else:
            return False

    def attack_enemy(self):
            self.log("Starting attack")
            while self.is_enemy_detected() and self.bot_running:
                skill_index = self.get_available_skill()
                if skill_index is not None:
                    # Shuffle available skills for random selection
                    random.shuffle(skill_index)
                    for idx in skill_index:
                        self.use_skill(idx)
                        if self.jump_while_attacking.get() and random.random() < 0.3:
                            pyautogui.press('space')
                            time.sleep(0.1)
                        # Break after using one skill to avoid spamming
                        break 
                else:
                    self.log("All skills on cooldown, using basic attack or waiting...")
                    time.sleep(random.uniform(0.5, 1.5))

                # Reset the timer after each successful enemy detection
                self.last_enemy_detection_time = time.time()

            if self.bot_running and not self.is_enemy_detected() and self.collect_loot.get():
                self.loot_enemy()

    def get_available_skill(self):
        now = time.time()
        available_skills = []
        for i, (cooldown, enabled) in enumerate(zip(self.skill_cooldowns, self.skill_enabled)):
            if enabled and (now - self.last_skill_use_time[i]) >= cooldown:
                available_skills.append(i)
        return available_skills if available_skills else None

    def use_skill(self, skill_index):
        key = self.skill_keys[skill_index]
        self.log(f"Using skill: {self.skill_names[skill_index]} (Key: {key})")
        pyautogui.press(key)
        self.last_skill_use_time[skill_index] = time.time()
        time.sleep(random.uniform(0.5, 1.5))

    def check_and_handle_death(self):
        if not self.is_player_alive():
            if self.is_revive_button_present():
                self.log("Revive button detected, clicking")
                pyautogui.click(self.revive_button_location)
            else:
                self.log("Player health low, using potion")
                pyautogui.press(self.potion_hotkey)
                time.sleep(1)
        else:
            self.log("Player health is good, continue fighting")

    def loot_enemy(self):
        self.log("Looting...")
        time.sleep(0.5)
        pyautogui.press('f')
        time.sleep(0.5)
        if self.loot_button_location:
            pyautogui.click(self.loot_button_location)
            time.sleep(0.5)
            pyautogui.press('esc')

    def is_player_alive(self):
        if self.player_health_box:
            x1, y1, x2, y2 = self.player_health_box
            screen = ImageGrab.grab(bbox=self.player_health_box)
            average_color = self.get_average_color(screen)

            full_health_color = (122, 10, 5)
            empty_health_color = (34, 20, 20)
            tolerance = 15

            if self.is_color_within_tolerance(average_color, full_health_color, tolerance):
                return True
            elif self.is_color_within_tolerance(average_color, empty_health_color, tolerance):
                return False
            else:
                return True
        else:
            return True

    def is_revive_button_present(self):
        if self.detect_revive_box:
            x1, y1, x2, y2 = self.detect_revive_box
            screen = ImageGrab.grab(bbox=self.detect_revive_box)
            average_color = self.get_average_color(screen)
            target_color = (88, 0, 0)
            tolerance = 10

            return self.is_color_within_tolerance(average_color, target_color, tolerance)
        else:
            return False

    def move_randomly(self):
        self.log("Moving randomly...")
        for _ in range(random.randint(1, self.movement_loops)):
            button = random.choice(self.movement_keys)
            pyautogui.keyDown(button)
            if self.jump_while_moving.get() and random.random() < 0.4:
                pyautogui.press('space')
            time.sleep(random.uniform(0.5, 1.5))
            pyautogui.keyUp(button)

    def get_average_color(self, image):
        pixels = list(image.getdata())
        r, g, b = zip(*pixels)
        return (int(sum(r) / len(r)), int(sum(g) / len(g)), int(sum(b) / len(b)))

    def is_color_within_tolerance(self, color, target_color, tolerance):
        return all(abs(color[i] - target_color[i]) <= tolerance for i in range(3))

def main():
    root = ctk.CTk() 
    app = BotApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
