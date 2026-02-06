import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
import pyautogui
import psutil
from PIL import ImageGrab, Image, ImageEnhance, ImageOps
import random
import time
import threading
import json
import os
import re
import win32gui
import win32con
import pytesseract
import webbrowser
import keyboard

import subprocess
import sys

# --- Prevent Tesseract from spawning console windows (Windows only) ---
if sys.platform.startswith("win"):
    _original_popen = subprocess.Popen

    def _silent_popen(*args, **kwargs):
        kwargs.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
        return _original_popen(*args, **kwargs)

    subprocess.Popen = _silent_popen

# --- Tesseract Configuration & Validation ---
TESSERACT_CONFIGURED = False
TESSERACT_PATH = None
try:
    tesseract_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]
    tesseract_found = False
    for path in tesseract_paths:
        if os.path.exists(path):
            try:
                pytesseract.pytesseract.tesseract_cmd = path
                version_info = pytesseract.get_tesseract_version()
                print(f"Tesseract found and verified at: {path} (Version: {version_info})")
                TESSERACT_PATH = path
                TESSERACT_CONFIGURED = True
                tesseract_found = True
                break
            except Exception as e:
                print(f"Found Tesseract at {path}, but verification failed: {e}")

    if not tesseract_found:
        try:
            version_info = pytesseract.get_tesseract_version()
            print(f"Tesseract found in system PATH and verified (Version: {version_info})")
            TESSERACT_CONFIGURED = True
            tesseract_found = True
        except pytesseract.TesseractNotFoundError:
            raise Exception("Tesseract executable not found in common paths or system PATH.")
        except Exception as e:
             print(f"Tesseract found in PATH, but verification failed: {e}")

except Exception as e:
    error_message = f"Tesseract configuration failed.\nError: {e}\nPlease ensure Tesseract-OCR is installed correctly and its path is configured.\n\nOCR features will be disabled."
    print(error_message)
# --- End Tesseract Configuration ---


# --- Overlay Class ---
class Overlay(tk.Toplevel):
    def __init__(self, root):
        super().__init__(root); self.title("Define Area/Point"); self.attributes('-fullscreen', True); self.attributes('-topmost', True)
        self.attributes('-alpha', 0.3); self.configure(bg='black'); self.config(cursor="crosshair")
        self.start_screen_x=None; self.start_screen_y=None; self.start_canvas_x=None; self.start_canvas_y=None
        self.current_rect_id=None; self.result_coords=None; self.mode=None
        self.canvas = tk.Canvas(self, bg='black', highlightthickness=0); self.canvas.pack(fill="both", expand=True); self.canvas.config(cursor="crosshair")
        self.canvas.bind("<ButtonPress-1>", self.on_press); self.canvas.bind("<B1-Motion>", self.on_motion); self.canvas.bind("<ButtonRelease-1>", self.on_release); self.bind("<Escape>", self.on_cancel)
    def on_press(self, event):
        self.start_screen_x=event.x_root; self.start_screen_y=event.y_root; self.start_canvas_x=event.x; self.start_canvas_y=event.y
        if self.mode == 'area':
            if self.current_rect_id: self.canvas.delete(self.current_rect_id)
            self.current_rect_id=self.canvas.create_rectangle(self.start_canvas_x, self.start_canvas_y, self.start_canvas_x, self.start_canvas_y, outline='red', width=2)
    def on_motion(self, event):
        if self.mode == 'area' and self.start_canvas_x is not None:
            cur_canvas_x=event.x; cur_canvas_y=event.y
            if self.current_rect_id: self.canvas.coords(self.current_rect_id, self.start_canvas_x, self.start_canvas_y, cur_canvas_x, cur_canvas_y)
    def on_release(self, event):
        if self.start_screen_x is None: return
        end_screen_x=event.x_root; end_screen_y=event.y_root
        if self.mode == 'point': self.result_coords = (end_screen_x, end_screen_y)
        elif self.mode == 'area':
            x1=min(self.start_screen_x,end_screen_x); y1=min(self.start_screen_y,end_screen_y); x2=max(self.start_screen_x,end_screen_x); y2=max(self.start_screen_y,end_screen_y)
            min_size=1; x2=x1+min_size if x2-x1<min_size else x2; y2=y1+min_size if y2-y1<min_size else y2
            self.result_coords = (x1, y1, x2, y2)
        self.destroy(); self.start_screen_x=None; self.start_screen_y=None; self.start_canvas_x=None; self.start_canvas_y=None; self.current_rect_id=None
    def on_cancel(self, event=None): self.result_coords = None; self.destroy()
    def get_coords(self, mode='area'): self.mode=mode; self.grab_set(); self.wait_window(); return self.result_coords
# --- End Overlay Class ---


class BotApp:
    LOG_LEVELS = ["DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR"]
    LOG_COLORS = { "TIME": "#AAAAAA", "DEBUG": "#BEBEBE", "INFO": "#E0E0E0", "SUCCESS": "#00E676", "WARNING": "#FFAB00", "ERROR": "#FF5252" }
    MAX_LOG_LINES = 500

    def __init__(self, root):
        self.root = root
        self.root.title("DeadLink's AQ3D Bot [v3.0.0]")
        self.root.geometry("700x500") 
        self.root.minsize(600, 400)

        icon_path = 'logo.ico'
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)
        else:
            print(f"Warning: Icon '{icon_path}' not found.")

        self.root.attributes('-topmost', True)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._default_button_text_color = ctk.ThemeManager.theme["CTkButton"]["text_color"]

        # --- Bot Settings & State ---
        self.aq3d_running = False
        self.health_box = None
        self.menu_close_location = None
        self.movement_keys = {'w': True, 'a': True, 's': True, 'd': True}
        self.movement_loops = 5
        self.player_health_box = None
        self.potion_hotkey = 'p'
        self.potion_health_threshold = 50
        self.loot_hotkey = 'l'
        self.detect_revive_box = None
        self.collect_loot = tk.BooleanVar(value=True)
        self.jump_while_moving = tk.BooleanVar()
        self.jump_while_attacking = tk.BooleanVar()
        self.stop_bot_on_death = tk.BooleanVar()
        self.run_back_after_death = tk.BooleanVar(value=False)
        self.focus_aq3d_enabled = tk.BooleanVar(value=True)
        self.run_back_seconds = 5
        self.target_enemy_names_list = []
        self.skill_names = ["Basic Attack", "Skill 1", "Skill 2", "Skill 3", "Skill 4", "Cross Skill 1", "Cross Skill 2", "Cross Skill 3"]
        self.skill_keys = ['1','2','3','4','5','6','7','8']
        self.skill_cooldowns = [0,5,10,15,20,25,30,30]
        self.skill_enabled = [True]*len(self.skill_names)
        self.last_skill_use_time = [0]*len(self.skill_names)
        self.no_enemy_timeout_minutes = 5
        self.max_runtime_hours = 0
        self.bot_start_time = 0
        self.bot_running = False
        self.last_enemy_detection_time = time.time()
        self.settings_modified = False
        self.log_line_count = 0
        self.input_widgets_to_disable = []
        self.afk_interval_minutes = 0
        self.afk_duration_minutes = 0
        self.last_afk_time = time.time()
        self._afk_revive_pending = False
        self._in_afk_mode = False

        # --- NEW UI Setup ---
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # Navigation Frame
        self.nav_frame = ctk.CTkFrame(self.root, width=150, corner_radius=0)
        self.nav_frame.grid(row=0, column=0, sticky="nsw")
        self.nav_frame.grid_rowconfigure(4, weight=1)

        self.nav_title = ctk.CTkLabel(self.nav_frame, text="AQ3D Bot", font=ctk.CTkFont(size=20, weight="bold"))
        self.nav_title.grid(row=0, column=0, padx=12, pady=(12, 8))

        self.nav_start_button = ctk.CTkButton(self.nav_frame, text="Start (F5)", command=self.start_bot, height=36)
        self.nav_start_button.grid(row=1, column=0, padx=12, pady=(0,6), sticky="ew")
        self.nav_stop_button = ctk.CTkButton(self.nav_frame, text="Stop (F6)", command=self.stop_bot, state="disabled", height=36)
        self.nav_stop_button.grid(row=2, column=0, padx=12, pady=(0,8), sticky="ew")
        self.nav_save_button = ctk.CTkButton(self.nav_frame, text="Save Settings", command=self.save_all_settings, height=36)
        self.nav_save_button.grid(row=3, column=0, padx=12, pady=(0,10), sticky="ew")
        self.nav_timer_label = ctk.CTkLabel(self.nav_frame, text="Runtime: 00:00:00")
        self.nav_timer_label.grid(row=4, column=0, padx=12, pady=(0,12), sticky="w")

        # Backwards-compatible aliases for older code that expects these attribute names
        # I will clean this up in the next version.. to lazy right now
        self.start_button = self.nav_start_button
        self.stop_button = self.nav_stop_button
        self.timer_label = self.nav_timer_label
        self.save_button = self.nav_save_button

        self.nav_frame.grid_rowconfigure(5, weight=1)

        # Navigation Buttons
        self.nav_buttons = {}
        nav_items = ["Dashboard", "Combat", "Locations", "Settings", "About"]
        for i, item in enumerate(nav_items):
            button = ctk.CTkButton(self.nav_frame, text=item, corner_radius=0, height=40,
                                   fg_color="transparent", text_color=("gray10", "gray90"),
                                   hover_color=("gray70", "gray30"), anchor="w",
                                   command=lambda page=item: self.show_page(page))
            row = i + 5 if item != "About" else 10
            button.grid(row=row, column=0, sticky="ew", padx=10, pady=2)
            self.nav_buttons[item] = button

        # Content Frames Container
        self.main_content_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_content_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(0, weight=1)

        self.pages = {}
        for page_name in nav_items:
            frame = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
            self.pages[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.create_dashboard_page()
        self.create_combat_page()
        self.create_locations_page()
        self.create_settings_page()
        self.create_about_page()
        self.load_settings()
        self.check_aq3d_status()
        self.setup_hotkeys()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.show_page("Dashboard")

    # --- Page Creation Methods ---
    def create_dashboard_page(self):
        page = self.pages["Dashboard"]
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(0, weight=0)
        page.grid_rowconfigure(1, weight=1) 

        # Top Frame for Controls / Status
        top_frame = ctk.CTkFrame(page, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 0))
        top_frame.grid_columnconfigure(0, weight=1)

        # Status Frame
        status_frame = ctk.CTkFrame(top_frame)
        status_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        status_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(status_frame, text="AQ3D Status:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=15, pady=10, sticky="w")
        self.aq3d_status_label = ctk.CTkLabel(status_frame, text="Not Running", text_color="red")
        self.aq3d_status_label.grid(row=0, column=1, padx=15, pady=10, sticky="w")

        # Full-width Logs under status
        log_frame = ctk.CTkFrame(page)
        log_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 0), pady=(10,0))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(log_frame, text="Logs", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=10, pady=6, sticky="w")
        self.log_text = ctk.CTkTextbox(log_frame, wrap="word", state="disabled", text_color="#E0E0E0")
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10))
        for level, color in self.LOG_COLORS.items():
            self.log_text.tag_config(level, foreground=color)

    def create_combat_page(self):
        page = self.pages["Combat"]
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        # --- Sub-navigation using Segmented Button ---
        self.combat_page_frames = {}
        combat_nav_items = ["Skills", "Actions", "Targeting"]
        nav_container = ctk.CTkFrame(page, fg_color="transparent")
        nav_container.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        nav_container.grid_columnconfigure(0, weight=1)

        segmented_button = ctk.CTkSegmentedButton(
            nav_container,
            values=combat_nav_items,
            command=self.show_combat_sub_page,
            height=35,
            font=ctk.CTkFont(size=14)
        )
        segmented_button.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        segmented_button.set("Skills")

        sub_page_container = ctk.CTkFrame(page, fg_color="transparent")
        sub_page_container.grid(row=1, column=0, sticky="nsew")
        sub_page_container.grid_columnconfigure(0, weight=1)
        sub_page_container.grid_rowconfigure(0, weight=1)
        for item in combat_nav_items:
            frame = ctk.CTkFrame(sub_page_container, fg_color="transparent")
            frame.grid(row=0, column=0, sticky="nsew")
            self.combat_page_frames[item] = frame

        # --- Populate Skills Frame ---
        skills_frame = self.combat_page_frames["Skills"]
        skills_frame.grid_columnconfigure(1, weight=1)
        skills_frame.grid_columnconfigure(2, weight=1)

        self.skill_entries, self.skill_cooldown_entries, self.skill_enabled_vars = [], [], []
        headers = ["Skill", "Hotkey", "Cooldown(s)", "Enabled"]
        for i, header in enumerate(headers):
            ctk.CTkLabel(skills_frame, text=header, font=ctk.CTkFont(weight="bold")).grid(row=0, column=i, padx=10, pady=10)

        for i, name in enumerate(self.skill_names):
            ctk.CTkLabel(skills_frame, text=f"{name}:").grid(row=i + 1, column=0, padx=10, pady=5, sticky="w")
            se = ctk.CTkEntry(skills_frame); se.grid(row=i + 1, column=1, padx=5, pady=5, sticky="ew"); se.insert(0, self.skill_keys[i]); se.bind("<KeyRelease>", self.mark_settings_modified); self.skill_entries.append(se)
            ce = ctk.CTkEntry(skills_frame); ce.grid(row=i + 1, column=2, padx=5, pady=5, sticky="ew"); ce.insert(0, str(self.skill_cooldowns[i])); ce.bind("<KeyRelease>", self.mark_settings_modified); self.skill_cooldown_entries.append(ce)
            sv = tk.BooleanVar(value=self.skill_enabled[i])
            sc = ctk.CTkCheckBox(skills_frame, text="", variable=sv, command=self.mark_settings_modified); sc.grid(row=i + 1, column=3, padx=10, pady=5)
            self.skill_enabled_vars.append(sv)
            self.input_widgets_to_disable.extend([se, ce, sc])

        # --- Populate Actions Frame ---
        actions_frame = self.combat_page_frames["Actions"]
        actions_frame.grid_columnconfigure(0, weight=1)

        cb1 = ctk.CTkCheckBox(actions_frame, text="Jump While Moving", variable=self.jump_while_moving, command=self.mark_settings_modified); cb1.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        cb2 = ctk.CTkCheckBox(actions_frame, text="Collect Loot", variable=self.collect_loot, command=self.mark_settings_modified); cb2.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        cb3 = ctk.CTkCheckBox(actions_frame, text="Jump While Attacking", variable=self.jump_while_attacking, command=self.mark_settings_modified); cb3.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        cb4 = ctk.CTkCheckBox(actions_frame, text="Stop Bot on Death", variable=self.stop_bot_on_death, command=self.mark_settings_modified); cb4.grid(row=3, column=0, padx=10, pady=10, sticky="w")
        
        run_back_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
        run_back_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=10)
        cb_runback = ctk.CTkCheckBox(run_back_frame, text="Run back after death for", variable=self.run_back_after_death, command=self.mark_settings_modified)
        cb_runback.grid(row=0, column=0, sticky="w")
        self.run_back_seconds_entry = ctk.CTkEntry(run_back_frame, width=50)
        self.run_back_seconds_entry.grid(row=0, column=1, sticky="w", padx=5)
        self.run_back_seconds_entry.insert(0, str(self.run_back_seconds))
        self.run_back_seconds_entry.bind("<KeyRelease>", self.mark_settings_modified)
        ctk.CTkLabel(run_back_frame, text="seconds").grid(row=0, column=2, sticky="w")
        
        def toggle_run_back_entry():
            state = "normal" if self.run_back_after_death.get() else "disabled"
            self.run_back_seconds_entry.configure(state=state)
        self.run_back_after_death.trace_add('write', lambda *args: toggle_run_back_entry())
        toggle_run_back_entry()
        self.input_widgets_to_disable.extend([cb1, cb2, cb3, cb4, cb_runback, self.run_back_seconds_entry])

        # --- AFK Controls ---
        afk_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
        afk_frame.grid(row=5, column=0, sticky="ew", padx=10, pady=(0,10))
        ctk.CTkLabel(afk_frame, text="Go AFK after (minutes):").grid(row=0, column=0, sticky="w")
        self.afk_interval_entry = ctk.CTkEntry(afk_frame, width=80)
        self.afk_interval_entry.grid(row=0, column=1, sticky="w", padx=8)
        self.afk_interval_entry.insert(0, str(self.afk_interval_minutes))
        self.afk_interval_entry.bind("<KeyRelease>", self.mark_settings_modified)

        ctk.CTkLabel(afk_frame, text="AFK duration (min, max 15):").grid(row=1, column=0, sticky="w", pady=(6,0))
        self.afk_duration_entry = ctk.CTkEntry(afk_frame, width=80)
        self.afk_duration_entry.grid(row=1, column=1, sticky="w", padx=8, pady=(6,0))
        self.afk_duration_entry.insert(0, str(self.afk_duration_minutes))
        self.afk_duration_entry.bind("<KeyRelease>", self.mark_settings_modified)

        self.input_widgets_to_disable.extend([self.afk_interval_entry, self.afk_duration_entry])

        # --- Populate Targeting Frame ---
        targeting_frame = self.combat_page_frames["Targeting"]
        targeting_frame.grid_columnconfigure(0, weight=1)
        targeting_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(targeting_frame, text="Target Enemies (one per line, partial match)", wraplength=400).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.target_enemy_names_textbox = ctk.CTkTextbox(targeting_frame);
        self.target_enemy_names_textbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.target_enemy_names_textbox.bind("<KeyRelease>", self.mark_settings_modified)
        self.input_widgets_to_disable.append(self.target_enemy_names_textbox)

        self.show_combat_sub_page("Skills")

    def create_locations_page(self):
        page = self.pages["Locations"]
        page.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(page, text="Define Screen Coordinates", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=(0, 15), sticky="w")
        
        loc_btn1 = ctk.CTkButton(page, text="Set Enemy Name Area", command=self.set_health_location); loc_btn1.grid(row=1, column=0, padx=10, pady=8, sticky="ew")
        self.health_location_label = ctk.CTkLabel(page, text="Not Set", anchor="w"); self.health_location_label.grid(row=1, column=1, padx=10, pady=8, sticky="ew")
        
        loc_btn2 = ctk.CTkButton(page, text="Set Player Health Area", command=self.set_player_health_location); loc_btn2.grid(row=2, column=0, padx=10, pady=8, sticky="ew")
        self.player_health_location_label = ctk.CTkLabel(page, text="Not Set", anchor="w"); self.player_health_location_label.grid(row=2, column=1, padx=10, pady=8, sticky="ew")
        
        loc_btn3 = ctk.CTkButton(page, text="Set Menu Close Position", command=self.set_menu_close_location); loc_btn3.grid(row=3, column=0, padx=10, pady=8, sticky="ew")
        self.menu_close_location_label = ctk.CTkLabel(page, text="Not Set", anchor="w"); self.menu_close_location_label.grid(row=3, column=1, padx=10, pady=8, sticky="ew")
        
        loc_btn4 = ctk.CTkButton(page, text="Set Revive Button Area", command=self.set_detect_revive_location); loc_btn4.grid(row=4, column=0, padx=10, pady=8, sticky="ew")
        self.detect_revive_location_label = ctk.CTkLabel(page, text="Not Set", anchor="w"); self.detect_revive_location_label.grid(row=4, column=1, padx=10, pady=8, sticky="ew")
        
        self.input_widgets_to_disable.extend([loc_btn1, loc_btn2, loc_btn3, loc_btn4])

    def create_settings_page(self):
        page = self.pages["Settings"]
        page.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(page, text="General Bot Settings", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=(0, 15), sticky="w")
        settings_map = {
            "Movement Loops:": "movement_loops_entry",
            "Potion Hotkey:": "potion_hotkey_entry",
            "Loot Hotkey:": "loot_hotkey_entry",
            "Use Potion Below (%):": "potion_threshold_entry",
            "No Enemy Timeout (min):": "no_enemy_timeout_entry",
            "Max Runtime (hrs, 0=inf):": "max_runtime_entry"
        }
        
        row_counter = 1
        for label_text, attr_name in settings_map.items():
            ctk.CTkLabel(page, text=label_text).grid(row=row_counter, column=0, sticky="w", padx=10, pady=8)
            entry = ctk.CTkEntry(page)
            entry.grid(row=row_counter, column=1, sticky="ew", padx=10, pady=8)
            entry.bind("<KeyRelease>", self.mark_settings_modified)
            setattr(self, attr_name, entry)
            self.input_widgets_to_disable.append(entry)
            row_counter += 1

        # Movement Keys
        ctk.CTkLabel(page, text="Movement Keys:").grid(row=row_counter, column=0, sticky="w", padx=10, pady=8)
        movement_frame = ctk.CTkFrame(page, fg_color="transparent")
        movement_frame.grid(row=row_counter, column=1, sticky="ew", padx=10, pady=8)

        self.movement_key_vars = {}
        keys = ['w', 'a', 's', 'd']
        key_positions = {
            'w': (0, 0),
            's': (0, 1),
            'a': (1, 0),
            'd': (1, 1)
        }

        for key in keys:
            self.movement_key_vars[key] = tk.BooleanVar(value=self.movement_keys.get(key, True))
            row, col = key_positions[key]
            cb_move = ctk.CTkCheckBox(
                movement_frame,
                text=key.upper(),
                variable=self.movement_key_vars[key],
                command=self.mark_settings_modified
            )
            cb_move.grid(row=row, column=col, padx=5, pady=2, sticky="w")
            self.input_widgets_to_disable.append(cb_move)

        row_counter += 1

        # Focus AQ3D
        ctk.CTkLabel(page, text="Focus AQ3D Window:").grid(row=row_counter, column=0, sticky="w", padx=10, pady=8)
        self.focus_aq3d_checkbox = ctk.CTkCheckBox(page, text="Enabled", variable=self.focus_aq3d_enabled, command=self.mark_settings_modified)
        self.focus_aq3d_checkbox.grid(row=row_counter, column=1, sticky="w", padx=10, pady=8)
        self.input_widgets_to_disable.append(self.focus_aq3d_checkbox)

    def create_about_page(self):
        page = self.pages["About"]
        page.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(page, text="About This Bot", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkLabel(page, text="A simple, customizable bot for AQ3D.", wraplength=500).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        links_frame = ctk.CTkFrame(page)
        links_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=20)
        links_frame.grid_columnconfigure((0,1,2), weight=1)

        self.source_button = ctk.CTkButton(links_frame, text="Source Code", command=lambda: self._open_link("https://github.com/Alx-Benjamin/AQ3D-Bot"))
        self.source_button.grid(row=0, column=0, padx=5, pady=10, sticky="ew")
        self.discord_button = ctk.CTkButton(links_frame, text="Discord", command=lambda: self._open_link("https://discord.gg/MfW5Mt7KUe"))
        self.discord_button.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.donate_button = ctk.CTkButton(links_frame, text="Donate", command=lambda: self._open_link("https://buymeacoffee.com/deadlink"))
        self.donate_button.grid(row=0, column=2, padx=5, pady=10, sticky="ew")

    # --- UI Management ---
    def show_page(self, page_name):
        """Hides all pages and shows the requested one."""
        for name, frame in self.pages.items():
            frame.grid_remove()
        
        self.pages[page_name].grid()
        for name, button in self.nav_buttons.items():
            if name == page_name:
                button.configure(fg_color=("gray75", "gray25"))
            else:
                button.configure(fg_color="transparent")

    def show_combat_sub_page(self, page_name):
        """Shows the selected frame within the combat page."""
        for frame in self.combat_page_frames.values():
            frame.grid_remove()
        self.combat_page_frames[page_name].grid(row=0, column=0, sticky="nsew", padx=5, pady=5)


    # --- Hotkey Methods ---
    def setup_hotkeys(self):
        try:
            keyboard.unhook_all()
            keyboard.add_hotkey('f5', lambda: self.root.after(0, self._try_start_bot))
            keyboard.add_hotkey('f6', lambda: self.root.after(0, self._try_stop_bot))
            self.log("Hotkeys F5 (Start) / F6 (Stop) registered.", "INFO")
        except Exception as e:
             self.log(f"Failed to set up hotkeys: {e}. Try running as administrator.", "ERROR")

    def _try_start_bot(self):
        if not self.bot_running: self.log("F5 pressed - Starting bot...", "INFO"); self.start_bot()
        else: self.log("F5 pressed - Bot already running.", "DEBUG")

    def _try_stop_bot(self):
        if self.bot_running: self.log("F6 pressed - Stopping bot...", "INFO"); self.stop_bot()
        else: self.log("F6 pressed - Bot not running.", "DEBUG")

    def unhook_hotkeys(self):
        try: keyboard.unhook_all(); self.log("Hotkeys unhooked.", "INFO")
        except Exception as e: self.log(f"Error unhooking hotkeys: {e}", "WARNING")

    # --- Input Control Methods ---
    def _set_input_widgets_state(self, state, exclude=None):
        """Set state for widgets tracked in self.input_widgets_to_disable.

        exclude: optional iterable of widget objects to skip (keeps Stop button enabled).
        """
        exclude = set(w for w in (exclude or []) if w)
        for widget in self.input_widgets_to_disable:
            try:
                if not widget or (widget in exclude):
                    continue
                if not getattr(widget, 'winfo_exists', lambda: False)():
                    continue
                if isinstance(widget, ctk.CTkTextbox):
                    widget.configure(state=state)
                elif hasattr(widget, 'configure'):
                    widget.configure(state=state)
            except Exception as e:
                try:
                    self.log(f"Error changing state for widget {widget}: {e}", "WARNING")
                except Exception:
                    print(f"Error changing state for widget {widget}: {e}")

    def _disable_inputs(self):
        excludes = [getattr(self, 'stop_button', None), getattr(self, 'nav_stop_button', None)]
        self.log("Disabling settings inputs.", "DEBUG")
        self._set_input_widgets_state(tk.DISABLED, exclude=excludes)

    def _enable_inputs(self):
        self.log("Enabling settings inputs.", "DEBUG")
        self._set_input_widgets_state(tk.NORMAL)

    # --- Tesseract Check ---
    def _is_tesseract_ready(self):
        global TESSERACT_CONFIGURED
        if not TESSERACT_CONFIGURED:
             try:
                 pytesseract.get_tesseract_version(); TESSERACT_CONFIGURED = True
             except Exception: return False
        try:
            pytesseract.get_tesseract_version(); return True
        except Exception: return False

    # --- Other Methods ---
    def _open_link(self, url):
        try: webbrowser.open_new_tab(url); self.log(f"Opened link: {url}", "INFO")
        except Exception as e: self.log(f"Failed to open link {url}: {e}", "ERROR"); messagebox.showerror("Link Error", f"Could not open link:\n{url}\n\nError: {e}")

    def mark_settings_modified(self, event=None):
        if not self.settings_modified: self.settings_modified=True; self.nav_save_button.configure(text="Save All Settings *", text_color="orange")

    # --- LOG FUNCTION ---
    def log(self, message, level="INFO"):
        if level not in self.LOG_LEVELS: level = "INFO"
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        print(log_entry.strip())
        if self.root and self.root.winfo_exists():
            self.root.after(0, self._update_log_textbox, log_entry, level)

    def _update_log_textbox(self, log_entry, level):
        try:
            log_widget = getattr(self, 'log_text', None)
            if not log_widget or not log_widget.winfo_exists():
                return
            log_widget.configure(state="normal")
            tag_start_index = log_widget.index(tk.END + "-1c linestart")
            log_widget.insert(tk.END, log_entry)
            log_widget.tag_add(level, tag_start_index, tk.END + "-1c")
            self.log_line_count += 1
            if self.log_line_count > self.MAX_LOG_LINES:
                 lines_to_delete = self.log_line_count - self.MAX_LOG_LINES
                 log_widget.delete("1.0", f"{lines_to_delete + 1}.0")
                 self.log_line_count = self.MAX_LOG_LINES
            log_widget.configure(state="disabled")
            #auto-scroll
            try:
                log_widget.yview(tk.END)
            except Exception:
                pass
        except Exception as e:
            print(f"[Log Error] Unhandled exception in _update_log_textbox: {e}")

    # --- Core Bot Logic ---
    def check_aq3d_status(self):
        try: self.aq3d_running = any(p.name()=="AQ3D.exe" for p in psutil.process_iter(['name']))
        except Exception as e: self.log(f"Error checking AQ3D process: {e}", "WARNING"); self.aq3d_running = False
        status = "Running" if self.aq3d_running else "Not Running"; color = "green" if self.aq3d_running else "red"
        if self.root and self.root.winfo_exists() and self.aq3d_status_label and self.aq3d_status_label.winfo_exists():
             self.root.after(0, lambda: self.aq3d_status_label.configure(text=status, text_color=color))

    def _get_overlay_coords(self, prompt, mode):
        self.log(prompt, "INFO");
        if not self.root or not self.root.winfo_exists(): return None
        self.root.attributes('-topmost', False); self.root.lift(); self.root.focus_force()
        self.root.withdraw(); time.sleep(0.2); coords = None
        try:
            overlay = Overlay(self.root); coords = overlay.get_coords(mode=mode)
        except Exception as e: self.log(f"Overlay error: {e}", "ERROR")
        finally:
            if self.root and self.root.winfo_exists():
                if not self.root.winfo_viewable(): self.root.deiconify()
                self.root.attributes('-topmost', True); time.sleep(0.1)
                self.root.lift(); self.root.focus_force()
        return coords

    def set_health_location(self):
        coords = self._get_overlay_coords("Define ENEMY NAME Area (Drag Box)", 'area')
        if coords: self.health_box=coords; self.health_location_label.configure(text=f"Set: {coords}"); self.log(f"Enemy name area set: {self.health_box}", "SUCCESS"); self.mark_settings_modified()
        else: self.log("Enemy name area selection cancelled.", "WARNING")

    def set_player_health_location(self):
        coords = self._get_overlay_coords("Define PLAYER HEALTH TEXT Area (Drag Box)", 'area')
        if coords: self.player_health_box=coords; self.player_health_location_label.configure(text=f"Set: {coords}"); self.log(f"Player health area set: {self.player_health_box}", "SUCCESS"); self.mark_settings_modified()
        else: self.log("Player health area selection cancelled.", "WARNING")

    def set_menu_close_location(self):
        coords = self._get_overlay_coords("Define 'Menu Close' Button Position (Click Point)", 'point')
        if coords: self.menu_close_location=coords; self.menu_close_location_label.configure(text=f"Set: {coords}"); self.log(f"Menu close position set: {self.menu_close_location}", "SUCCESS"); self.mark_settings_modified()
        else: self.log("Menu close position selection cancelled.", "WARNING")

    def set_detect_revive_location(self):
        coords = self._get_overlay_coords("Define REVIVE Button Area (Drag Box)", 'area')
        if coords: self.detect_revive_box=coords; self.detect_revive_location_label.configure(text=f"Set: {coords}"); self.log(f"Revive button area set: {self.detect_revive_box}", "SUCCESS"); self.mark_settings_modified()
        else: self.log("Revive button area selection cancelled.", "WARNING")

    def save_all_settings(self):
        self.run_back_seconds = int(self.run_back_seconds_entry.get()) if self.run_back_seconds_entry.get().isdigit() else 5
        self.loot_hotkey = self.loot_hotkey_entry.get()
        self.movement_loops = int(self.movement_loops_entry.get()) if self.movement_loops_entry.get().isdigit() else 5
        self.potion_hotkey = self.potion_hotkey_entry.get()
        self.potion_health_threshold = int(self.potion_threshold_entry.get()) if self.potion_threshold_entry.get().isdigit() else 50
        self.no_enemy_timeout_minutes = int(self.no_enemy_timeout_entry.get()) if self.no_enemy_timeout_entry.get().isdigit() else 5
        self.max_runtime_hours = int(self.max_runtime_entry.get()) if self.max_runtime_entry.get().isdigit() else 0
        self.target_enemy_names_list = [line.strip() for line in self.target_enemy_names_textbox.get("1.0", "end").splitlines() if line.strip()]
        self.skill_keys = [entry.get() for entry in self.skill_entries]
        self.skill_cooldowns = [int(entry.get()) if entry.get().isdigit() else 0 for entry in self.skill_cooldown_entries]
        self.skill_enabled = [var.get() for var in self.skill_enabled_vars]
        self.movement_keys = {k: var.get() for k, var in self.movement_key_vars.items()}
        try:
            self.afk_interval_minutes = int(self.afk_interval_entry.get()) if self.afk_interval_entry.get().isdigit() else 0
        except Exception:
            self.afk_interval_minutes = 0
        try:
            self.afk_duration_minutes = int(self.afk_duration_entry.get()) if self.afk_duration_entry.get().isdigit() else 0
        except Exception:
            self.afk_duration_minutes = 0
        if self.afk_duration_minutes > 15: self.afk_duration_minutes = 15
        settings = {
                'health_box': self.health_box, 'player_health_box': self.player_health_box,
                'menu_close_location': self.menu_close_location, 'detect_revive_box': self.detect_revive_box,
                'movement_keys': self.movement_keys, 'movement_loops': self.movement_loops,
                'potion_hotkey': self.potion_hotkey, 'loot_hotkey': self.loot_hotkey,
                'potion_health_threshold': self.potion_health_threshold,
                'no_enemy_timeout_minutes': self.no_enemy_timeout_minutes,
                'max_runtime_hours': self.max_runtime_hours,
                'target_enemy_names_list': self.target_enemy_names_list,
                'skill_keys': self.skill_keys, 'skill_cooldowns': self.skill_cooldowns,
                'skill_enabled': self.skill_enabled, 'collect_loot': self.collect_loot.get(),
                'jump_while_moving': self.jump_while_moving.get(),
                'jump_while_attacking': self.jump_while_attacking.get(),
                'stop_bot_on_death': self.stop_bot_on_death.get(),
                'run_back_after_death': self.run_back_after_death.get(),
                'run_back_seconds': self.run_back_seconds,
                'afk_interval_minutes': self.afk_interval_minutes,
                'afk_duration_minutes': self.afk_duration_minutes,
                'focus_aq3d_enabled': self.focus_aq3d_enabled.get()
            }
        try:
            with open('settings.json', 'w') as f: json.dump(settings, f, indent=4)
            self.settings_modified = False
            self.nav_save_button.configure(text="Save All Settings", text_color=self._default_button_text_color)
            self.log("Settings saved successfully.", "SUCCESS")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save settings.\n\n{e}", parent=self.root)
            self.log(f"Error saving settings: {e}", "ERROR")

    def load_settings(self):
        self.log("Loading settings...", "INFO")
        if os.path.exists('settings.json'):
            try:
                with open('settings.json', 'r') as f:
                    settings = json.load(f)
                self.log("Settings file found and loaded.", "INFO")
            except Exception as e:
                self.log(f"Error loading settings.json: {e}. Using defaults.", "ERROR")
                settings = {}
        else:
            self.log("No settings file found. Using default settings.", "WARNING")
            settings = {}

        self.health_box = settings.get('health_box')
        self.player_health_box = settings.get('player_health_box')
        self.menu_close_location = settings.get('menu_close_location')
        self.detect_revive_box = settings.get('detect_revive_box')
        self.movement_keys = settings.get('movement_keys', {'w': True, 'a': True, 's': True, 'd': True})
        self.movement_loops = settings.get('movement_loops', 5)
        self.potion_hotkey = settings.get('potion_hotkey', 'p')
        self.loot_hotkey = settings.get('loot_hotkey', 'l')
        self.potion_health_threshold = settings.get('potion_health_threshold', 50)
        self.no_enemy_timeout_minutes = settings.get('no_enemy_timeout_minutes', 5)
        self.max_runtime_hours = settings.get('max_runtime_hours', 0)
        self.target_enemy_names_list = settings.get('target_enemy_names_list', [])
        self.skill_keys = settings.get('skill_keys', ['1','2','3','4','5','6','7','8'])
        self.skill_cooldowns = settings.get('skill_cooldowns', [0,5,10,15,20,25,30,30])
        self.skill_enabled = settings.get('skill_enabled', [True]*len(self.skill_names))
        self.collect_loot.set(settings.get('collect_loot', True))
        self.jump_while_moving.set(settings.get('jump_while_moving', False))
        self.jump_while_attacking.set(settings.get('jump_while_attacking', False))
        self.stop_bot_on_death.set(settings.get('stop_bot_on_death', False))
        self.run_back_after_death.set(settings.get('run_back_after_death', False))
        self.run_back_seconds = settings.get('run_back_seconds', 5)
        self.afk_interval_minutes = settings.get('afk_interval_minutes', 0)
        self.afk_duration_minutes = settings.get('afk_duration_minutes', 0)
        self.focus_aq3d_enabled.set(settings.get('focus_aq3d_enabled', True))

        self.settings_modified = False
        self.nav_save_button.configure(text="Save All Settings", text_color=self._default_button_text_color)
        self.update_gui_elements_from_settings()

    def update_gui_elements_from_settings(self):
        try:
            # Location Labels
            self.health_location_label.configure(text=f"{self.health_box}" if self.health_box else "Not Set")
            self.player_health_location_label.configure(text=f"{self.player_health_box}" if self.player_health_box else "Not Set")
            self.menu_close_location_label.configure(text=f"{self.menu_close_location}" if self.menu_close_location else "Not Set")
            self.detect_revive_location_label.configure(text=f"{self.detect_revive_box}" if self.detect_revive_box else "Not Set")
            
            # Entries
            self.movement_loops_entry.delete(0, tk.END); self.movement_loops_entry.insert(0, str(self.movement_loops))
            self.potion_hotkey_entry.delete(0, tk.END); self.potion_hotkey_entry.insert(0, self.potion_hotkey)
            self.loot_hotkey_entry.delete(0, tk.END); self.loot_hotkey_entry.insert(0, self.loot_hotkey)
            self.potion_threshold_entry.delete(0, tk.END); self.potion_threshold_entry.insert(0, str(self.potion_health_threshold))
            self.no_enemy_timeout_entry.delete(0, tk.END); self.no_enemy_timeout_entry.insert(0, str(self.no_enemy_timeout_minutes))
            self.max_runtime_entry.delete(0, tk.END); self.max_runtime_entry.insert(0, str(self.max_runtime_hours))
            self.run_back_seconds_entry.delete(0, tk.END); self.run_back_seconds_entry.insert(0, str(self.run_back_seconds))

            # AFK entries
            if hasattr(self, 'afk_interval_entry'):
                self.afk_interval_entry.delete(0, tk.END); self.afk_interval_entry.insert(0, str(self.afk_interval_minutes))
            if hasattr(self, 'afk_duration_entry'):
                self.afk_duration_entry.delete(0, tk.END); self.afk_duration_entry.insert(0, str(self.afk_duration_minutes))

            self.target_enemy_names_textbox.delete("1.0", tk.END); self.target_enemy_names_textbox.insert("1.0", "\n".join(self.target_enemy_names_list))
            
            # Skills
            for i in range(len(self.skill_names)):
                self.skill_entries[i].delete(0, tk.END); self.skill_entries[i].insert(0, self.skill_keys[i])
                self.skill_cooldown_entries[i].delete(0, tk.END); self.skill_cooldown_entries[i].insert(0, str(self.skill_cooldowns[i]))
                self.skill_enabled_vars[i].set(self.skill_enabled[i])
            
            # Movement Keys
            for key, var in self.movement_key_vars.items(): var.set(self.movement_keys.get(key, True))
        except Exception as e:
            self.log(f"Error updating GUI elements from settings: {e}", "ERROR")

    def start_bot(self):
        if not self._is_tesseract_ready():
             messagebox.showerror("OCR Error", "Tesseract OCR not ready.", parent=self.root); return
        self.check_aq3d_status()
        if not self.aq3d_running:
            messagebox.showerror("Error", "AQ3D is not running.", parent=self.root); return
        if not self.health_box:
            messagebox.showerror("Error", "Set 'Enemy Name Area'.", parent=self.root); return
        if self.settings_modified:
            if messagebox.askyesno("Unsaved Settings", "Save settings before starting?", parent=self.root):
                self.save_all_settings()
            if self.settings_modified: return
        if not self.bot_running:
            self.bot_running = True; self.log("Bot starting...", "INFO")
            self.start_button.configure(state="disabled"); self.stop_button.configure(state="normal")
            if hasattr(self, 'nav_start_button') and hasattr(self, 'nav_stop_button'):
                self.nav_start_button.configure(state="disabled"); self.nav_stop_button.configure(state="normal")
            self._disable_inputs()
            self.bot_start_time = time.time(); self.last_enemy_detection_time = time.time()
            self.last_afk_time = time.time()
            self._afk_revive_pending = False
            self._in_afk_mode = False
            self.last_skill_use_time = [0] * len(self.skill_names)
            self.bot_thread = threading.Thread(target=self.bot_loop, daemon=True); self.bot_thread.start()
            self.update_timer(); self.log("Bot started.", "SUCCESS")

    def stop_bot(self):
        if self.bot_running:
            self.log("Stop requested.", "INFO"); self.bot_running = False
            if hasattr(self, 'nav_start_button') and hasattr(self, 'nav_stop_button'):
                self.nav_start_button.configure(state="normal"); self.nav_stop_button.configure(state="disabled")
            if self.root and self.root.winfo_exists(): self.root.after(0, self._finalize_stop)

    def _finalize_stop(self):
        if self.start_button.cget('state') == tk.NORMAL: return
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        if hasattr(self, 'nav_start_button') and hasattr(self, 'nav_stop_button'):
            self.nav_start_button.configure(state="normal"); self.nav_stop_button.configure(state="disabled")
        self._enable_inputs(); self.timer_label.configure(text="Runtime: Stopped")

    def update_timer(self):
        if self.bot_running and self.root and self.root.winfo_exists():
            elapsed = int(time.time() - self.bot_start_time)
            hrs, rem = divmod(elapsed, 3600)
            mins, secs = divmod(rem, 60)
            timestr = f"{hrs:02d}:{mins:02d}:{secs:02d}"
            if self.timer_label and self.timer_label.winfo_exists():
                self.root.after(0, lambda: self.timer_label.configure(text=timestr))
            if hasattr(self, 'nav_timer_label') and self.nav_timer_label and self.nav_timer_label.winfo_exists():
                self.root.after(0, lambda: self.nav_timer_label.configure(text=f"Runtime: {timestr}"))
            max_seconds = self.max_runtime_hours * 3600
            if self.max_runtime_hours > 0 and elapsed >= max_seconds:
                self.log(f"Max runtime reached. Stopping.", "INFO")
                self.stop_bot()
                return
            no_enemy_timeout_seconds = self.no_enemy_timeout_minutes * 60
            if self.no_enemy_timeout_minutes > 0 and (time.time() - self.last_enemy_detection_time > no_enemy_timeout_seconds):
                self.log(f"No enemy timeout reached. Stopping.", "WARNING")
                self.stop_bot()
                return
            if self.bot_running:
                self.root.after(1000, self.update_timer)
        else:
            if self.timer_label and self.timer_label.winfo_exists():
                self.root.after(0, lambda: self.timer_label.configure(text="Runtime: Stopped"))
            if hasattr(self, 'nav_timer_label') and self.nav_timer_label and self.nav_timer_label.winfo_exists():
                self.root.after(0, lambda: self.nav_timer_label.configure(text="Runtime: Stopped"))

    def bot_loop(self):
        self.log("Bot thread loop started.", "INFO")
        try:
            while self.bot_running:
                if self.afk_interval_minutes and (time.time() - self.last_afk_time) >= (self.afk_interval_minutes * 60) and not self._in_afk_mode:
                        self._in_afk_mode = True
                        afk_secs = min(self.afk_duration_minutes, 15) * 60
                        self.log(f"Entering AFK for {afk_secs//60} minutes.", "INFO")
                        afk_start = time.time()
                        while self.bot_running and (time.time() - afk_start) < afk_secs:
                            try:
                                if self.check_and_click_revive():
                                    if self.run_back_after_death.get():
                                        self._afk_revive_pending = True
                                        self.log("Revived during AFK. Will run back after AFK.", "INFO")
                                        if self.stop_bot_on_death.get():
                                            self.log("'Stop on Death' is enabled, so stopping bot.", "INFO")
                                            self._schedule_stop()
                                            break
                            except Exception:
                                pass
                            time.sleep(1)
                        self.last_afk_time = time.time()
                        self._in_afk_mode = False
                        self.log("AFK period ended.", "INFO")
                        if self._afk_revive_pending and self.run_back_after_death.get():
                            try:
                                self.log("Performing deferred run-back after AFK.", "INFO")
                                self.run_back_after_death_action()
                            except Exception:
                                pass
                            self._afk_revive_pending = False
                self.check_aq3d_status()
                if not self.aq3d_running: self.log("AQ3D closed. Stopping.", "ERROR"); self._schedule_stop(); break
                if not self.focus_aq3d(): time.sleep(3); continue
                self.check_and_handle_death()
                self.find_and_attack_target()
                time.sleep(random.uniform(0.1, 0.3))
        except Exception as e:
             self.log(f"CRITICAL ERROR in bot loop: {e}", "ERROR")
             self._schedule_stop()
        finally:
            self.log("Bot thread loop finished.", "INFO")
            self._schedule_finalize_stop()

    def _schedule_stop(self):
        if self.root and self.root.winfo_exists(): self.root.after(0, self.stop_bot)

    def _schedule_finalize_stop(self):
        if self.root and self.root.winfo_exists():
             self.root.after(0, self._enable_inputs)
             self.root.after(10, lambda: self.log("Bot has stopped.", "SUCCESS"))

    def focus_aq3d(self):
        """Focus the AQ3D window if enabled in settings."""
        if not self.focus_aq3d_enabled.get():
            self.root.attributes('-topmost', False)
            return True

        try:
            hwnd = win32gui.FindWindow(None, "AQ3D")
            if not hwnd:
                self.log("AQ3D window not found.", "WARNING")
                return False

            if self.root.attributes('-topmost'):
                self.log("Disabling topmost to allow window focus...", "DEBUG")
                self.root.attributes('-topmost', False)
                time.sleep(0.1)

            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.1)

            self.root.attributes('-topmost', True)

            focused = win32gui.GetForegroundWindow() == hwnd
            if focused:
                self.log("Successfully focused AQ3D window.", "SUCCESS")
            else:
                self.log("Failed to bring AQ3D window to foreground.", "WARNING")

            return focused

        except Exception as e:
            self.log(f"Error focusing AQ3D: {e}", "ERROR")
            return False

    def find_and_attack_target(self):
        filters = [f.lower().strip() for f in self.target_enemy_names_list if f.strip()]

        for _ in range(10):
            if not self.bot_running:
                return

            pyautogui.press('tab')
            time.sleep(random.uniform(0.2, 0.4))

            name = self.read_enemy_name()
            if name:
                self.last_enemy_detection_time = time.time()
                lname = name.lower()
                health = self.get_player_health_percentage()
                if health is None:
                    health = 1 #if health cannot be read

                if not filters or any(f in lname for f in filters):
                    self.log(f"Attacking '{name}'.", "INFO")
                    self.attack_current_target(expected_name=name)
                    return

                if health < 50:
                    self.log(f"Low Health, Attacking '{name}'.", "INFO")
                    self.attack_current_target(expected_name=name)
                    return
                
        self.log("No matching enemy found. Moving.", "INFO")
        self.move_randomly()

    def read_enemy_name(self):
        if not self._is_tesseract_ready() or not self.health_box: return None
        try:
            ss = ImageGrab.grab(bbox=self.health_box)
            img = ss.convert('L'); img = ImageEnhance.Contrast(img).enhance(1.8)
            img = img.point(lambda p: 255 if p > 135 else 0); img = ImageOps.invert(img)
            text = pytesseract.image_to_string(img, lang='eng', config=r'--oem 3 --psm 6').strip()
            return ''.join(c for c in text if c.isalnum() or c.isspace()).strip() or None
        except Exception: return None

    def attack_current_target(self, expected_name=None, expected_filters=None):
        start = time.time()
        while self.bot_running and (time.time() - start < 90):
            name = self.read_enemy_name()
            if not name:
                self.log("Target killed or lost.", "INFO")
                break

            self.last_enemy_detection_time = time.time()
            health = self.get_player_health_percentage()
            if health is None:
                health = 1  # safe value if health cant be read

            if expected_name:
                lname = name.lower()
                ename = expected_name.lower()
                filters = expected_filters or []
                names_mismatch = ename not in lname and not any(f in lname for f in filters)

                if names_mismatch:
                    if health >= 50:
                        self.log(f"Target changed from '{expected_name}' to '{name}'. Aborting attack.", "INFO")
                        break
                    else:
                        self.log(f"Target changed from '{expected_name}' to '{name}'. Low Health, attacking anyway.", "INFO")

            self.try_use_available_skill(time.time())
            if self.jump_while_attacking.get() and random.random() < 0.25:
                pyautogui.press('space')
            self.check_and_handle_death()
            time.sleep(random.uniform(0.1, 0.2))

        if self.bot_running and self.collect_loot.get():
            self.loot_enemy()

    def try_use_available_skill(self, current_time):
        ready = [i for i, en in enumerate(self.skill_enabled) if en and (current_time - self.last_skill_use_time[i]) >= self.skill_cooldowns[i]]
        if ready: self.use_skill(max(ready))

    def use_skill(self, idx):
        pyautogui.press(self.skill_keys[idx]); self.last_skill_use_time[idx] = time.time()

    def check_and_handle_death(self):
        if self.check_and_click_revive():
            if self.stop_bot_on_death.get():
                self.log("Died and 'Stop on Death' enabled. Stopping.", "INFO")
                self._schedule_stop()
                return True
            if self._in_afk_mode:
                if self.run_back_after_death.get():
                    self._afk_revive_pending = True
                return True
            else:
                self.run_back_after_death_action()
                return True
        if self.player_health_box:
            health = self.get_player_health_percentage()
            if health is not None and health < self.potion_health_threshold:
                self.log(f"Health low ({health}%). Using potion.", "INFO")
                pyautogui.press(self.potion_hotkey); time.sleep(1.0)
        return False

    def get_player_health_percentage(self):
        if not self._is_tesseract_ready() or not self.player_health_box: return None
        try:
            ss = ImageGrab.grab(bbox=self.player_health_box)
            img = ss.convert('L'); img = ImageEnhance.Contrast(img).enhance(2.8)
            img = img.point(lambda p: 0 if p > 170 else 255)
            text = pytesseract.image_to_string(img, lang='eng', config=r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789/%').strip()
            match = re.search(r'(\d{1,3})\s*%', text)
            return int(match.group(1)) if match else None
        except Exception: return None

    def check_and_click_revive(self):
        if not self._is_tesseract_ready() or not self.detect_revive_box: return False
        try:
            ss = ImageGrab.grab(bbox=self.detect_revive_box)
            img = ss.convert('L'); img = ImageEnhance.Contrast(img).enhance(2.5)
            img = img.point(lambda p: 0 if p > 175 else 255)
            text = pytesseract.image_to_string(img, lang='eng', config=r'--oem 3 --psm 6').strip()
            if "revive" in text.lower():
                self.log("Revive button found. Waiting 5s...", "INFO")
                time.sleep(5)
                if self.bot_running:
                    cx = self.detect_revive_box[0] + (self.detect_revive_box[2] - self.detect_revive_box[0]) / 2
                    cy = self.detect_revive_box[1] + (self.detect_revive_box[3] - self.detect_revive_box[1]) / 2
                    pyautogui.click(cx, cy); time.sleep(3)
                    return True
            return False
        except Exception: return False
        
    def run_back_after_death_action(self):
        if self.run_back_after_death.get():
            seconds = self.run_back_seconds
            self.log(f"Running back after death for {seconds} seconds...", "INFO")
            pyautogui.keyDown('w')
            time.sleep(seconds)
            pyautogui.keyUp('w')

    def loot_enemy(self):
        if self.loot_hotkey:
            pyautogui.press(self.loot_hotkey); time.sleep(0.3) # Once to open loot
            pyautogui.press(self.loot_hotkey); time.sleep(0.3) # Again to collect loot
            pyautogui.press("esc"); time.sleep(0.3) # Close loot window
        if self.menu_close_location:
            pyautogui.click(self.menu_close_location); time.sleep(0.2)

    def move_randomly(self):
        keys = [k for k, v in self.movement_keys.items() if v]
        if not keys: time.sleep(1); return
        for _ in range(random.randint(1, self.movement_loops)):
            if not self.bot_running: break
            key = random.choice(keys); duration = random.uniform(0.15, 0.55)
            pyautogui.keyDown(key)
            if self.jump_while_moving.get():
                start = time.time()
                while time.time() - start < duration:
                    if random.random() < 0.1: pyautogui.press('space')
                    time.sleep(0.05)
            else:
                time.sleep(duration)
            pyautogui.keyUp(key)
            time.sleep(random.uniform(0.05, 0.15))

    def on_closing(self):
        self.unhook_hotkeys()
        if self.bot_running:
            if messagebox.askyesno("Confirm Quit", "Bot is running. Stop and exit?", parent=self.root):
                self.stop_bot(); time.sleep(0.3)
                if self.settings_modified and messagebox.askyesno("Unsaved Settings", "Save changes?", parent=self.root): self.save_all_settings()
                self.root.destroy()
            else: self.setup_hotkeys()
        else:
            if self.settings_modified and messagebox.askyesno("Unsaved Settings", "Save changes?", parent=self.root): self.save_all_settings()
            self.root.destroy()

# --- Main Execution ---
def main():
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        print("Could not set DPI awareness.")

    root = ctk.CTk()
    app = BotApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
