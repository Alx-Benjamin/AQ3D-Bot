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
import io
import webbrowser
import keyboard

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
            except pytesseract.TesseractNotFoundError:
                 print(f"Path exists ({path}) but TesseractNotFoundError.")
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
    error_message = f"Tesseract configuration failed.\nError: {e}\nPlease ensure Tesseract-OCR is installed correctly (including language data 'eng') and added to your system's PATH, or update the path check in the script.\n\nOCR features will be disabled."
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


# --- CollapsibleFrame Class ---
class CollapsibleFrame(ctk.CTkFrame):
    def __init__(self, master, title="", **kwargs):
        super().__init__(master, **kwargs); self.show = tk.BooleanVar(value=True)

        self.title_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.title_frame.pack(fill="x", expand=False, pady=(0, 5), padx=0)
        self.title_frame.grid_columnconfigure(1, weight=1)


        self.toggle_button = ctk.CTkButton(self.title_frame, text="-", width=25, height=25, command=self.toggle)
        self.toggle_button.grid(row=0, column=0, padx=(5, 2), pady=0)


        self.title_label = ctk.CTkLabel(self.title_frame, text=title, font=ctk.CTkFont(weight="bold"), anchor="w")
        self.title_label.grid(row=0, column=1, padx=(2, 5), pady=0, sticky="ew")


        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")

        self.content_frame.pack(fill="both", expand=True, padx=5, pady=(0,5))

    def toggle(self):
        if self.show.get():
            self.content_frame.pack_forget()
            self.toggle_button.configure(text="+")
        else:

            self.content_frame.pack(fill="both", expand=True, padx=5, pady=(0,5))
            self.toggle_button.configure(text="-")
        self.show.set(not self.show.get())
# --- End CollapsibleFrame Class ---


class BotApp:
    LOG_LEVELS = ["DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR"]
    LOG_COLORS = { "TIME": "#AAAAAA", "DEBUG": "#BEBEBE", "INFO": "#E0E0E0", "SUCCESS": "#00E676", "WARNING": "#FFAB00", "ERROR": "#FF5252" }
    MAX_LOG_LINES = 500

    def __init__(self, root):
        self.root = root
        self.root.title("DeadLink's AQ3D Bot [v2.0.0]")
        icon_path = 'logo.ico';
        if os.path.exists(icon_path): self.root.iconbitmap(icon_path)
        else: print(f"Warning: Icon '{icon_path}' not found.")
        self.root.attributes('-topmost', True)
        ctk.set_appearance_mode("dark"); ctk.set_default_color_theme("blue")

        self._default_button_text_color = ctk.ThemeManager.theme["CTkButton"]["text_color"]

        # --- Bot Settings & State ---
        self.aq3d_running = False; self.health_box = None; self.loot_button_location = None
        self.movement_keys = {'w': True, 'a': True, 's': True, 'd': True}; self.movement_loops = 5
        self.player_health_box = None; self.potion_hotkey = 'p'; self.potion_health_threshold = 50
        self.detect_revive_box = None; self.collect_loot = tk.BooleanVar(value=True)
        self.jump_while_moving = tk.BooleanVar(); self.jump_while_attacking = tk.BooleanVar()
        self.stop_bot_on_death = tk.BooleanVar(); self.target_enemy_names_list = []
        self.skill_names = ["Basic Attack", "Skill 1", "Skill 2", "Skill 3", "Skill 4", "Cross Skill"]
        self.skill_keys = ['1','2','3','4','5','6']; self.skill_cooldowns = [0,5,10,15,20,25]
        self.skill_enabled = [True]*len(self.skill_names); self.last_skill_use_time = [0]*len(self.skill_names)
        self.no_enemy_timeout_minutes = 5; self.max_runtime_hours = 0; self.bot_start_time = 0
        self.bot_running = False; self.last_enemy_detection_time = time.time(); self.settings_modified = False
        self.log_line_count = 0
        # --- End Settings & State ---

        # --- GUI Setup ---
        self.root.grid_columnconfigure(0, weight=0, minsize=300)
        self.root.grid_columnconfigure(1, weight=0, minsize=300)
        self.root.grid_columnconfigure(2, weight=1)
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=0)
        self.root.grid_rowconfigure(2, weight=1)

        frame_width = 300

        # --- Column 0 Frames ---
        self.status_frame=CollapsibleFrame(root, title="Status", width=frame_width);
        self.status_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
        self.skill_settings_frame=CollapsibleFrame(root, title="Skill Settings", width=frame_width);
        self.skill_settings_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.action_frame=CollapsibleFrame(root, title="Bot Actions", width=frame_width);
        self.action_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

        # --- Column 1 Frames ---
        self.location_frame=CollapsibleFrame(root, title="Location Settings", width=frame_width);
        self.location_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        self.settings_frame=CollapsibleFrame(root, title="General Settings", width=frame_width);
        self.settings_frame.grid(row=1, column=1, padx=10, pady=5, sticky="nsew")
        self.link_frame = ctk.CTkFrame(root)
        self.link_frame.grid(row=2, column=1, padx=10, pady=5, sticky="nsew")
        self.link_frame.grid_columnconfigure(0, weight=1)
        self.link_frame.grid_columnconfigure(1, weight=1)
        self.link_frame.grid_columnconfigure(2, weight=1)

        # --- Column 2 Frame (Logs) ---
        self.log_outer_frame = ctk.CTkFrame(root)
        self.log_outer_frame.grid(row=0, column=2, rowspan=3, padx=(5,10), pady=(10, 10), sticky="nsew")
        self.log_outer_frame.grid_rowconfigure(0, weight=1)
        self.log_outer_frame.grid_columnconfigure(0, weight=1)
        self.log_frame = CollapsibleFrame(self.log_outer_frame, title="Log")
        self.log_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        # --- End GUI Layout ---


        # --- Populate Frames ---
        self.input_widgets_to_disable = []


        self.status_frame.content_frame.grid_columnconfigure(0, weight=1); self.status_frame.content_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.status_frame.content_frame, text="AQ3D Status:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.aq3d_status_label = ctk.CTkLabel(self.status_frame.content_frame, text="Not Running"); self.aq3d_status_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.save_button = ctk.CTkButton(self.status_frame.content_frame, text="Save All Settings", command=self.save_all_settings); self.save_button.grid(row=1, column=0, columnspan=2, pady=5, padx=5, sticky="ew")
        self.start_button = ctk.CTkButton(self.status_frame.content_frame, text="Start Bot (F5)", command=self.start_bot); self.start_button.grid(row=2, column=0, columnspan=2, pady=5, padx=5, sticky="ew")
        self.stop_button = ctk.CTkButton(self.status_frame.content_frame, text="Stop Bot (F6)", command=self.stop_bot, state="disabled"); self.stop_button.grid(row=3, column=0, columnspan=2, pady=5, padx=5, sticky="ew")
        self.input_widgets_to_disable.append(self.save_button)


        self.location_frame.content_frame.grid_columnconfigure(1, weight=1)
        loc_btn1 = ctk.CTkButton(self.location_frame.content_frame, text="Enemy Name Area", command=self.set_health_location); loc_btn1.grid(row=0, column=0, padx=5, pady=3, sticky="ew")
        self.health_location_label = ctk.CTkLabel(self.location_frame.content_frame, text="Not Set", anchor="w"); self.health_location_label.grid(row=0, column=1, padx=5, pady=3, sticky="ew")
        loc_btn2 = ctk.CTkButton(self.location_frame.content_frame, text="Player Health Text Area", command=self.set_player_health_location); loc_btn2.grid(row=1, column=0, padx=5, pady=3, sticky="ew")
        self.player_health_location_label = ctk.CTkLabel(self.location_frame.content_frame, text="Not Set", anchor="w"); self.player_health_location_label.grid(row=1, column=1, padx=5, pady=3, sticky="ew")
        loc_btn3 = ctk.CTkButton(self.location_frame.content_frame, text="Loot Button Pos", command=self.set_loot_button_location); loc_btn3.grid(row=2, column=0, padx=5, pady=3, sticky="ew")
        self.loot_location_label = ctk.CTkLabel(self.location_frame.content_frame, text="Not Set", anchor="w"); self.loot_location_label.grid(row=2, column=1, padx=5, pady=3, sticky="ew")
        loc_btn4 = ctk.CTkButton(self.location_frame.content_frame, text="Revive Button Area", command=self.set_detect_revive_location); loc_btn4.grid(row=3, column=0, padx=5, pady=3, sticky="ew")
        self.detect_revive_location_label = ctk.CTkLabel(self.location_frame.content_frame, text="Not Set", anchor="w"); self.detect_revive_location_label.grid(row=3, column=1, padx=5, pady=3, sticky="ew")
        self.input_widgets_to_disable.extend([loc_btn1, loc_btn2, loc_btn3, loc_btn4])


        self.skill_settings_frame.content_frame.grid_columnconfigure(0, weight=0); self.skill_settings_frame.content_frame.grid_columnconfigure(1, weight=0)
        self.skill_settings_frame.content_frame.grid_columnconfigure(2, weight=0); self.skill_settings_frame.content_frame.grid_columnconfigure(3, weight=0)
        self.skill_entries = []; self.skill_cooldown_entries = []; self.skill_enabled_vars = []
        ctk.CTkLabel(self.skill_settings_frame.content_frame, text="Skill", anchor="w").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ctk.CTkLabel(self.skill_settings_frame.content_frame, text="Hotkey").grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        ctk.CTkLabel(self.skill_settings_frame.content_frame, text="Cooldown(s)").grid(row=0, column=2, padx=5, pady=2, sticky="ew")
        ctk.CTkLabel(self.skill_settings_frame.content_frame, text="Enabled").grid(row=0, column=3, padx=(15,5), pady=2)
        for i, name in enumerate(self.skill_names):
            ctk.CTkLabel(self.skill_settings_frame.content_frame, text=f"{name}:").grid(row=i + 1, column=0, padx=5, pady=2, sticky="w")
            se = ctk.CTkEntry(self.skill_settings_frame.content_frame, width=50);
            se.grid(row=i + 1, column=1, padx=5, pady=2, sticky="ew"); se.insert(0, self.skill_keys[i]); se.bind("<KeyRelease>", self.mark_settings_modified); self.skill_entries.append(se)
            ce = ctk.CTkEntry(self.skill_settings_frame.content_frame, width=50);
            ce.grid(row=i + 1, column=2, padx=5, pady=2, sticky="ew"); ce.insert(0, str(self.skill_cooldowns[i])); ce.bind("<KeyRelease>", self.mark_settings_modified); self.skill_cooldown_entries.append(ce)
            sv = tk.BooleanVar(value=self.skill_enabled[i])
            sc_frame = ctk.CTkFrame(self.skill_settings_frame.content_frame, fg_color="transparent")
            sc_frame.grid(row=i + 1, column=3, padx=(15,5), pady=0, sticky="ew")
            sc = ctk.CTkCheckBox(sc_frame, text="", variable=sv, command=self.mark_settings_modified, width=10)
            sc.pack(anchor="center", pady=2)
            self.skill_enabled_vars.append(sv)
            self.input_widgets_to_disable.extend([se, ce, sc])


        self.settings_frame.content_frame.grid_columnconfigure(1, weight=1); self.settings_frame.content_frame.grid_rowconfigure(5, weight=1)
        ctk.CTkLabel(self.settings_frame.content_frame, text="Movement Loops:").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self.movement_loops_entry = ctk.CTkEntry(self.settings_frame.content_frame, width=70); self.movement_loops_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=3); self.movement_loops_entry.insert(0, str(self.movement_loops)); self.movement_loops_entry.bind("<KeyRelease>", self.mark_settings_modified)
        ctk.CTkLabel(self.settings_frame.content_frame, text="Potion Hotkey:").grid(row=1, column=0, sticky="w", padx=5, pady=3)
        self.potion_hotkey_entry = ctk.CTkEntry(self.settings_frame.content_frame, width=70); self.potion_hotkey_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=3); self.potion_hotkey_entry.insert(0, self.potion_hotkey); self.potion_hotkey_entry.bind("<KeyRelease>", self.mark_settings_modified)
        ctk.CTkLabel(self.settings_frame.content_frame, text="Use Potion Below (%):").grid(row=2, column=0, sticky="w", padx=5, pady=3)
        self.potion_threshold_entry = ctk.CTkEntry(self.settings_frame.content_frame, width=70); self.potion_threshold_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=3); self.potion_threshold_entry.insert(0, str(self.potion_health_threshold)); self.potion_threshold_entry.bind("<KeyRelease>", self.mark_settings_modified)
        ctk.CTkLabel(self.settings_frame.content_frame, text="No Enemy Timeout (min):").grid(row=3, column=0, sticky="w", padx=5, pady=3)
        self.no_enemy_timeout_entry = ctk.CTkEntry(self.settings_frame.content_frame, width=70); self.no_enemy_timeout_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=3); self.no_enemy_timeout_entry.insert(0, str(self.no_enemy_timeout_minutes)); self.no_enemy_timeout_entry.bind("<KeyRelease>", self.mark_settings_modified)
        ctk.CTkLabel(self.settings_frame.content_frame, text="Max Runtime (hrs, 0=inf):").grid(row=4, column=0, sticky="w", padx=5, pady=3)
        self.max_runtime_entry = ctk.CTkEntry(self.settings_frame.content_frame, width=70); self.max_runtime_entry.grid(row=4, column=1, sticky="ew", padx=5, pady=3); self.max_runtime_entry.insert(0, str(self.max_runtime_hours)); self.max_runtime_entry.bind("<KeyRelease>", self.mark_settings_modified)
        ctk.CTkLabel(self.settings_frame.content_frame, text="Target Enemies (partial match):").grid(row=5, column=0, sticky="nw", padx=5, pady=3)
        self.target_enemy_names_textbox = ctk.CTkTextbox(self.settings_frame.content_frame, height=80); self.target_enemy_names_textbox.grid(row=5, column=1, columnspan=2, sticky="nsew", padx=5, pady=3); self.target_enemy_names_textbox.bind("<KeyRelease>", self.mark_settings_modified)
        self.input_widgets_to_disable.extend([self.movement_loops_entry, self.potion_hotkey_entry, self.potion_threshold_entry, self.no_enemy_timeout_entry, self.max_runtime_entry, self.target_enemy_names_textbox])


        self.action_frame.content_frame.grid_columnconfigure(0, weight=1); self.action_frame.content_frame.grid_columnconfigure(1, weight=1)
        cb1 = ctk.CTkCheckBox(self.action_frame.content_frame, text="Jump While Moving", variable=self.jump_while_moving, command=self.mark_settings_modified); cb1.grid(row=0, column=0, padx=5, pady=3, sticky="w")
        cb2 = ctk.CTkCheckBox(self.action_frame.content_frame, text="Collect Loot (F)", variable=self.collect_loot, command=self.mark_settings_modified); cb2.grid(row=0, column=1, padx=5, pady=3, sticky="w")
        cb3 = ctk.CTkCheckBox(self.action_frame.content_frame, text="Jump While Attacking", variable=self.jump_while_attacking, command=self.mark_settings_modified); cb3.grid(row=1, column=0, padx=5, pady=3, sticky="w")
        cb4 = ctk.CTkCheckBox(self.action_frame.content_frame, text="Stop Bot on Death", variable=self.stop_bot_on_death, command=self.mark_settings_modified); cb4.grid(row=1, column=1, padx=5, pady=3, sticky="w")
        ctk.CTkLabel(self.action_frame.content_frame, text="Movement Keys:").grid(row=2, column=0, columnspan=2, padx=5, pady=3, sticky="w")
        self.movement_key_vars = {}; keys = ['w', 'a', 's', 'd'];
        action_checkboxes = [cb1, cb2, cb3, cb4]
        for i, key in enumerate(keys):
            self.movement_key_vars[key] = tk.BooleanVar(value=self.movement_keys.get(key, True))
            cb_move = ctk.CTkCheckBox(self.action_frame.content_frame, text=f"{key.upper()}", variable=self.movement_key_vars[key], command=self.mark_settings_modified); cb_move.grid(row=3 + i // 2, column=i % 2, padx=5, pady=3, sticky="w")
            action_checkboxes.append(cb_move)
        self.input_widgets_to_disable.extend(action_checkboxes)


        self.log_text = ctk.CTkTextbox(self.log_frame.content_frame, width=350, height=400, wrap="word", state="disabled", text_color="#E0E0E0"); self.log_text.pack(expand=True, fill="both", padx=5, pady=5)
        for level, color in self.LOG_COLORS.items(): self.log_text.tag_config(level, foreground=color)
        self.timer_label = ctk.CTkLabel(self.log_frame.content_frame, text="Runtime: 00:00:00"); self.timer_label.pack(pady=(5,0))


        self.source_button = ctk.CTkButton(self.link_frame, text="Source Code", command=lambda: self._open_link("https://github.com/Alx-Benjamin/AQ3D-Bot"));
        self.source_button.grid(row=0, column=0, padx=5, pady=10, sticky="ew")
        self.discord_button = ctk.CTkButton(self.link_frame, text="Discord", command=lambda: self._open_link("https://discord.gg/MfW5Mt7KUe"));
        self.discord_button.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.donate_button = ctk.CTkButton(self.link_frame, text="Donate", command=lambda: self._open_link("https://buymeacoffee.com/deadlink"));
        self.donate_button.grid(row=0, column=2, padx=5, pady=10, sticky="ew")
        # --- End Populate Frames ---

        # --- Initial Setup ---
        self.load_settings(); self.check_aq3d_status()
        self.setup_hotkeys()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        # --- End Init ---


    # --- Hotkey Methods ---
    def setup_hotkeys(self):
        """Sets up global hotkeys."""
        try:
            keyboard.unhook_all()
            keyboard.add_hotkey('f5', lambda: self.root.after(0, self._try_start_bot))
            keyboard.add_hotkey('f6', lambda: self.root.after(0, self._try_stop_bot))
            self.log("Hotkeys F5 (Start) / F6 (Stop) registered.", "INFO")
        except ImportError:
             self.log("Could not import 'keyboard' library. Hotkeys disabled.", "WARNING")
             self.log("Install using: pip install keyboard", "WARNING")
        except Exception as e:
             perm_error = False
             if os.name == 'nt':
                 try:
                     import ctypes; perm_error = not ctypes.windll.shell32.IsUserAnAdmin()
                 except Exception: pass
             if perm_error: self.log(f"Failed to set up hotkeys: {e}. Try running as administrator.", "ERROR")
             else: self.log(f"Failed to set up hotkeys: {e}", "ERROR")

    def _try_start_bot(self):
        """Safely attempts to start the bot (called by hotkey via root.after)."""
        if not self.bot_running: self.log("F5 pressed - Starting bot...", "INFO"); self.start_bot()
        else: self.log("F5 pressed - Bot already running.", "DEBUG")

    def _try_stop_bot(self):
        """Safely attempts to stop the bot (called by hotkey via root.after)."""
        if self.bot_running: self.log("F6 pressed - Stopping bot...", "INFO"); self.stop_bot()
        else: self.log("F6 pressed - Bot not running.", "DEBUG")

    def unhook_hotkeys(self):
        """Removes all registered hotkeys."""
        try: keyboard.unhook_all(); self.log("Hotkeys unhooked.", "INFO")
        except ImportError: pass
        except Exception as e: self.log(f"Error unhooking hotkeys: {e}", "WARNING")

    # --- Input Control Methods ---
    def _set_input_widgets_state(self, state):
        """Sets the state of all collected input widgets."""
        for widget in self.input_widgets_to_disable:
             if widget and widget.winfo_exists():
                 try:
                     if isinstance(widget, ctk.CTkTextbox): widget.configure(state=state)
                     elif hasattr(widget, 'configure'): widget.configure(state=state)
                 except Exception as e: self.log(f"Error changing state for widget {widget}: {e}", "WARNING")

    def _disable_inputs(self):
        self.log("Disabling settings inputs.", "DEBUG"); self._set_input_widgets_state(tk.DISABLED)

    def _enable_inputs(self):
        self.log("Enabling settings inputs.", "DEBUG"); self._set_input_widgets_state(tk.NORMAL)

    # --- Tesseract Check ---
    def _is_tesseract_ready(self):
        """Checks if Tesseract is configured AND functional."""
        global TESSERACT_CONFIGURED
        if not TESSERACT_CONFIGURED:
             try:
                 pytesseract.get_tesseract_version(); TESSERACT_CONFIGURED = True
                 print("Tesseract found in system PATH during check.")
             except pytesseract.TesseractNotFoundError: self.log("Tesseract path not set and not found in PATH.", "ERROR"); return False
             except Exception as e: self.log(f"Tesseract in PATH failed verification during check: {e}", "ERROR"); return False
        try:
            pytesseract.get_tesseract_version(); return True
        except pytesseract.TesseractNotFoundError:
            self.log(f"Tesseract configured but not found at runtime (Path: {TESSERACT_PATH or 'PATH'}).", "ERROR"); return False
        except Exception as e: self.log(f"Tesseract execution failed: {e}", "ERROR"); return False

    # --- Other Methods ---
    def _open_link(self, url):
        try: webbrowser.open_new_tab(url); self.log(f"Opened link: {url}", "INFO")
        except Exception as e: self.log(f"Failed to open link {url}: {e}", "ERROR"); messagebox.showerror("Link Error", f"Could not open link:\n{url}\n\nError: {e}")

    def mark_settings_modified(self, event=None):
        if not self.settings_modified: self.settings_modified=True; self.save_button.configure(text="Save All Settings *", text_color="orange")

    # --- LOG FUNCTION ---
    def log(self, message, level="INFO"):
        """ Thread-safe logging to the GUI textbox and console. """
        if level not in self.LOG_LEVELS: level = "INFO"
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"


        print(log_entry.strip())

        # --- Schedule GUI Update ---
        try:

            if self.root and self.root.winfo_exists():

                self.root.after(0, self._update_log_textbox, log_entry, level)

        except Exception as e:

            print(f"[Log Error] Failed to schedule GUI log update: {e}")

    def _update_log_textbox(self, log_entry, level):
        """ **INTERNAL:** Updates the log textbox (must run on main thread). """
        try:
            # --- Check if log widget is valid ---

            log_widget = getattr(self, 'log_text', None)
            if not log_widget or not log_widget.winfo_exists():

                return

            # --- Insert Text ---
            log_widget.configure(state="normal")


            try:

                 message_start_index = log_widget.index(tk.END + "-1c linestart") + f" +{len(f'[{time.strftime('%H:%M:%S')}] [{level}] ')}c"
                 tag_start_index = log_widget.index(tk.END + "-1c linestart")
                 log_widget.insert(tk.END, log_entry)

                 log_widget.tag_add(level, tag_start_index, tk.END + "-1c")
            except tk.TclError as tcl_error:

                 print(f"[Log Error] TclError applying tags: {tcl_error}. Inserting without tags.")
                 log_widget.insert(tk.END, log_entry)

            self.log_line_count += 1

            # --- Prune Old Lines ---
            if self.log_line_count > self.MAX_LOG_LINES:
                 lines_to_delete = self.log_line_count - self.MAX_LOG_LINES
                 end_delete_index = f"{lines_to_delete + 1}.0"
                 log_widget.delete("1.0", end_delete_index)
                 self.log_line_count = self.MAX_LOG_LINES

            log_widget.configure(state="disabled")

            # --- Auto-scroll ---

            if log_widget.yview()[1] > 0.95:
                 log_widget.yview(tk.END)

        except Exception as e:
            print(f"[Log Error] Unhandled exception in _update_log_textbox: {e}")
            import traceback
            print(traceback.format_exc())
    # --- END LOG FUNCTION ---


    def check_aq3d_status(self):
        try: self.aq3d_running = any(p.name()=="AQ3D.exe" for p in psutil.process_iter(['name']))
        except (psutil.NoSuchProcess, psutil.AccessDenied): self.aq3d_running = False
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

    # --- Location Setting Methods ---
    def set_health_location(self):
        coords = self._get_overlay_coords("Define ENEMY NAME Area (Drag Box)", 'area')
        if coords and len(coords)==4: self.health_box=coords; self.health_location_label.configure(text=f"Set: {coords[0]},{coords[1]}->{coords[2]},{coords[3]}"); self.log(f"Enemy name area set: {self.health_box}", "SUCCESS"); self.mark_settings_modified()
        else: self.log("Enemy name area selection cancelled or failed.", "WARNING")
    def set_player_health_location(self):
        coords = self._get_overlay_coords("Define PLAYER HEALTH TEXT Area (Drag Box)", 'area')
        if coords and len(coords)==4: self.player_health_box=coords; self.player_health_location_label.configure(text=f"Set: {coords[0]},{coords[1]}->{coords[2]},{coords[3]}"); self.log(f"Player health text area set: {self.player_health_box}", "SUCCESS"); self.mark_settings_modified()
        else: self.log("Player health text area selection cancelled or failed.", "WARNING")
    def set_loot_button_location(self):
        coords = self._get_overlay_coords("Define 'Loot All' Button Position (Click Point)", 'point')
        if coords and len(coords)==2: self.loot_button_location=coords; self.loot_location_label.configure(text=f"Set: ({coords[0]},{coords[1]})"); self.log(f"Loot button position set: {self.loot_button_location}", "SUCCESS"); self.mark_settings_modified()
        else: self.log("Loot button position selection cancelled or failed.", "WARNING")
    def set_detect_revive_location(self):
        coords = self._get_overlay_coords("Define REVIVE Button Area (Drag Box)", 'area')
        if coords and len(coords)==4: self.detect_revive_box=coords; self.detect_revive_location_label.configure(text=f"Set: {coords[0]},{coords[1]}->{coords[2]},{coords[3]}"); self.log(f"Revive button area set: {self.detect_revive_box}", "SUCCESS"); self.mark_settings_modified()
        else: self.log("Revive button area selection cancelled or failed.", "WARNING")
    # --- End Location Setting ---

    def save_all_settings(self):
        """Reads all settings from GUI, validates, and saves to file."""
        try:

            self.movement_loops = int(self.movement_loops_entry.get()); assert self.movement_loops >= 0
            thresh = int(self.potion_threshold_entry.get()); self.potion_health_threshold = max(0, min(100, thresh))
            self.potion_threshold_entry.delete(0, tk.END); self.potion_threshold_entry.insert(0, str(self.potion_health_threshold))
            self.no_enemy_timeout_minutes = int(self.no_enemy_timeout_entry.get()); assert self.no_enemy_timeout_minutes >= 0
            self.max_runtime_hours = int(self.max_runtime_entry.get()); assert self.max_runtime_hours >= 0

            temp_cds = []
            for i, e in enumerate(self.skill_cooldown_entries):
                 cd_val = int(e.get())
                 if cd_val < 0: self.log(f"Corrected negative CD {i+1} to 0.", "WARNING"); cd_val = 0
                 temp_cds.append(cd_val)
                 e.delete(0, tk.END); e.insert(0, str(cd_val))
            self.skill_cooldowns = temp_cds

            self.potion_hotkey = self.potion_hotkey_entry.get().strip().lower()
            names=self.target_enemy_names_textbox.get("1.0", tk.END).strip(); self.target_enemy_names_list = [n.strip() for n in names.splitlines() if n.strip()]
            self.skill_keys = [e.get().strip().lower() for e in self.skill_entries]
            self.skill_enabled = [v.get() for v in self.skill_enabled_vars]
            for k, v in self.movement_key_vars.items(): self.movement_keys[k] = v.get()

        except (ValueError, AssertionError):
             messagebox.showerror("Settings Error", "Invalid numeric value entered.\nPlease check numbers (must be non-negative).", parent=self.root)
             return
        except Exception as e:
             messagebox.showerror("Settings Error", f"Error reading settings: {e}", parent=self.root)
             return

        settings = {
            'health_box': getattr(self, 'health_box', None), 'player_health_box': getattr(self, 'player_health_box', None),
            'loot_button_location': getattr(self, 'loot_button_location', None), 'detect_revive_box': getattr(self, 'detect_revive_box', None),
            'movement_keys': getattr(self, 'movement_keys', {'w':True,'a':True,'s':True,'d':True}), 'movement_loops': getattr(self, 'movement_loops', 5),
            'potion_hotkey': getattr(self, 'potion_hotkey', 'p'), 'potion_health_threshold': getattr(self, 'potion_health_threshold', 50),
            'no_enemy_timeout_minutes': getattr(self, 'no_enemy_timeout_minutes', 5), 'max_runtime_hours': getattr(self, 'max_runtime_hours', 0),
            'target_enemy_names_list': getattr(self, 'target_enemy_names_list', []), 'skill_keys': getattr(self, 'skill_keys', ['1','2','3','4','5','6']),
            'skill_cooldowns': getattr(self, 'skill_cooldowns', [0,5,10,15,20,25]), 'skill_enabled': getattr(self, 'skill_enabled', [True]*len(self.skill_names)),
            'collect_loot': self.collect_loot.get(), 'jump_while_moving': self.jump_while_moving.get(),
            'jump_while_attacking': self.jump_while_attacking.get(), 'stop_bot_on_death': self.stop_bot_on_death.get()
        }
        try:
            with open('settings.json', 'w') as f: json.dump(settings, f, indent=4)
            self.settings_modified = False
            self.save_button.configure(text="Save All Settings", text_color=self._default_button_text_color)
            self.log("Settings saved successfully.", "SUCCESS")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save settings.\n\n{e}", parent=self.root)
            self.log(f"Error saving settings: {e}", "ERROR")


    def load_settings(self):
        """Loads settings from file and updates the GUI."""
        self.log("Loading settings...", "INFO")
        defaults = {
            'health_box': None, 'player_health_box': None, 'loot_button_location': None, 'detect_revive_box': None,
            'movement_keys': {'w':True,'a':True,'s':True,'d':True}, 'movement_loops': 5,
            'potion_hotkey': 'p', 'potion_health_threshold': 50,
            'no_enemy_timeout_minutes': 5, 'max_runtime_hours': 0,
            'target_enemy_names_list': [], 'skill_keys': ['1','2','3','4','5','6'],
            'skill_cooldowns': [0,5,10,15,20,25], 'skill_enabled': [True]*len(self.skill_names),
            'collect_loot': True, 'jump_while_moving': False,
            'jump_while_attacking': False, 'stop_bot_on_death': False
        }
        loaded_settings = defaults.copy()

        if os.path.exists('settings.json'):
            try:
                with open('settings.json', 'r') as f:
                    loaded_settings.update(json.load(f))
                self.log("Settings file found and loaded.", "INFO")
            except json.JSONDecodeError as e:
                self.log(f"Error decoding settings.json: {e}. Using defaults.", "ERROR")
                messagebox.showwarning("Load Error", f"Error reading settings file (invalid JSON).\nUsing defaults.\n\n{e}", parent=self.root)
            except Exception as e:
                self.log(f"Error loading settings.json: {e}. Using defaults.", "ERROR")
                messagebox.showwarning("Load Error", f"Error loading settings file.\nUsing defaults.\n\n{e}", parent=self.root)
        else:
            self.log("No settings file found. Using default settings.", "WARNING")


        self.health_box = loaded_settings['health_box']
        self.player_health_box = loaded_settings['player_health_box']
        self.loot_button_location = loaded_settings['loot_button_location']
        self.detect_revive_box = loaded_settings['detect_revive_box']
        self.movement_keys = loaded_settings['movement_keys']
        self.movement_loops = loaded_settings['movement_loops']
        self.potion_hotkey = loaded_settings['potion_hotkey']
        self.potion_health_threshold = loaded_settings['potion_health_threshold']
        self.no_enemy_timeout_minutes = loaded_settings['no_enemy_timeout_minutes']
        self.max_runtime_hours = loaded_settings['max_runtime_hours']
        self.target_enemy_names_list = loaded_settings['target_enemy_names_list']

        num_skills = len(self.skill_names)
        self.skill_keys = loaded_settings['skill_keys'][:num_skills] + [''] * (num_skills - len(loaded_settings['skill_keys']))

        valid_cds = []
        for cd in loaded_settings['skill_cooldowns'][:num_skills]:
             try: valid_cds.append(max(0, int(cd)))
             except (ValueError, TypeError): valid_cds.append(0)
        self.skill_cooldowns = valid_cds + [0] * (num_skills - len(valid_cds))
        self.skill_enabled = loaded_settings['skill_enabled'][:num_skills] + [True] * (num_skills - len(loaded_settings['skill_enabled']))

        self.collect_loot.set(loaded_settings['collect_loot'])
        self.jump_while_moving.set(loaded_settings['jump_while_moving'])
        self.jump_while_attacking.set(loaded_settings['jump_while_attacking'])
        self.stop_bot_on_death.set(loaded_settings['stop_bot_on_death'])

        self.settings_modified = False
        self.save_button.configure(text="Save All Settings", text_color=self._default_button_text_color)
        self.update_gui_elements_from_settings()


    def update_gui_elements_from_settings(self):
        """Updates GUI elements to reflect the currently loaded settings."""
        try:

            self.health_location_label.configure(text=f"{self.health_box}" if self.health_box else "Not Set")
            self.player_health_location_label.configure(text=f"{self.player_health_box}" if self.player_health_box else "Not Set")
            self.loot_location_label.configure(text=f"{self.loot_button_location}" if self.loot_button_location else "Not Set")
            self.detect_revive_location_label.configure(text=f"{self.detect_revive_box}" if self.detect_revive_box else "Not Set")

            self.movement_loops_entry.delete(0, tk.END); self.movement_loops_entry.insert(0, str(self.movement_loops))
            self.potion_hotkey_entry.delete(0, tk.END); self.potion_hotkey_entry.insert(0, self.potion_hotkey)
            self.potion_threshold_entry.delete(0, tk.END); self.potion_threshold_entry.insert(0, str(self.potion_health_threshold))
            self.no_enemy_timeout_entry.delete(0, tk.END); self.no_enemy_timeout_entry.insert(0, str(self.no_enemy_timeout_minutes))
            self.max_runtime_entry.delete(0, tk.END); self.max_runtime_entry.insert(0, str(self.max_runtime_hours))
            self.target_enemy_names_textbox.delete("1.0", tk.END); self.target_enemy_names_textbox.insert("1.0", "\n".join(self.target_enemy_names_list))

            for i in range(len(self.skill_names)):
                if i < len(self.skill_entries): self.skill_entries[i].delete(0, tk.END); self.skill_entries[i].insert(0, self.skill_keys[i])
                if i < len(self.skill_cooldown_entries): self.skill_cooldown_entries[i].delete(0, tk.END); self.skill_cooldown_entries[i].insert(0, str(self.skill_cooldowns[i]))
                if i < len(self.skill_enabled_vars): self.skill_enabled_vars[i].set(self.skill_enabled[i])

            for key, var in self.movement_key_vars.items(): var.set(self.movement_keys.get(key, True))

        except Exception as e:
            self.log(f"Error updating GUI elements from settings: {e}", "ERROR")


    def start_bot(self):
        """Validates settings and starts the bot thread."""
        if not self._is_tesseract_ready():
             messagebox.showerror("OCR Error", "Tesseract OCR not ready.\nPlease install/configure Tesseract.\nSee console/log.", parent=self.root)
             return
        self.check_aq3d_status()
        if not self.aq3d_running:
            messagebox.showerror("Error", "AQ3D is not running.", parent=self.root); return
        if not self.health_box:
            messagebox.showerror("Error", "Set 'Enemy Name Area'.", parent=self.root); return

        if not self.player_health_box: self.log("Warning: Player Health Area not set. Potions disabled.", "WARNING")
        if not self.detect_revive_box: self.log("Warning: Revive Button Area not set. Revive disabled.", "WARNING")
        if not self.loot_button_location and self.collect_loot.get(): self.log("Warning: Loot Pos not set (using 'F' only).", "WARNING")

        if self.settings_modified:
            save_choice = messagebox.askyesnocancel("Unsaved Settings", "Save settings before starting?", parent=self.root)
            if save_choice is None: return
            elif save_choice is True: self.save_all_settings();
            if self.settings_modified: return

        if not self.bot_running:
            self.bot_running = True; self.log("Bot starting...", "INFO")
            self.start_button.configure(state="disabled"); self.stop_button.configure(state="normal")
            self._disable_inputs()
            self.bot_start_time = time.time(); self.last_enemy_detection_time = time.time()
            self.last_skill_use_time = [0] * len(self.skill_names)
            self.bot_thread = threading.Thread(target=self.bot_loop, daemon=True); self.bot_thread.start()
            self.update_timer(); self.log("Bot started.", "SUCCESS")
        else: self.log("Bot already running.", "WARNING")


    def stop_bot(self):
        """Signals the bot loop to stop and updates the GUI via _finalize_stop."""
        if self.bot_running:
            self.log("Stop requested.", "INFO"); self.bot_running = False
            if self.root and self.root.winfo_exists(): self.root.after(0, self._finalize_stop)
        else:
            self.log("Stop requested, but bot not running.", "INFO")
            if self.root and self.root.winfo_exists(): self.root.after(0, self._enable_inputs)


    def _finalize_stop(self):
        """Helper function called by stop_bot via root.after to update GUI state."""
        if self.start_button.cget('state') == tk.NORMAL: return
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self._enable_inputs(); self.timer_label.configure(text="Runtime: Stopped")


    def update_timer(self):
        """Updates the runtime timer label and checks for time limits."""
        if self.bot_running and self.root and self.root.winfo_exists():
            elapsed = int(time.time() - self.bot_start_time)
            hrs, rem = divmod(elapsed, 3600); mins, secs = divmod(rem, 60)
            if self.timer_label and self.timer_label.winfo_exists():
                 self.root.after(0, lambda: self.timer_label.configure(text=f"Runtime: {hrs:02d}:{mins:02d}:{secs:02d}"))

            max_seconds = self.max_runtime_hours * 3600
            if self.max_runtime_hours > 0 and elapsed >= max_seconds: self.log(f"Max runtime ({self.max_runtime_hours}h) reached. Stopping.", "INFO"); self.stop_bot(); return
            no_enemy_timeout_seconds = self.no_enemy_timeout_minutes * 60
            if self.no_enemy_timeout_minutes > 0 and elapsed > 60 and (time.time() - self.last_enemy_detection_time > no_enemy_timeout_seconds): self.log(f"No enemy timeout ({self.no_enemy_timeout_minutes}m) reached. Stopping.", "WARNING"); self.stop_bot(); return

            if self.bot_running: self.root.after(1000, self.update_timer)


    # --- Main Bot Loop & Actions ---
    def bot_loop(self):
        """The main loop executed by the bot thread."""
        self.log("Bot thread loop started.", "INFO")
        self.last_health_check_time = 0; self.last_revive_check_time = 0; self.last_attack_health_check = 0
        try:
            while self.bot_running:
                start_time = time.time()
                self.check_aq3d_status()
                if not self.aq3d_running: self.log("AQ3D closed. Stopping.", "ERROR"); self._schedule_stop(); break
                if not self.focus_aq3d(): self.log("Focus failed. Retrying...", "WARNING"); time.sleep(3); continue
                time.sleep(0.05)
                died = self.check_and_handle_death()
                if not self.bot_running: break
                if died and self.stop_bot_on_death.get(): self.log("Died & stop on death enabled. Stopping.", "INFO"); self._schedule_stop(); break
                if not self.bot_running: break
                self.find_and_attack_target()
                if not self.bot_running: break
                loop_duration = time.time() - start_time
                sleep_time = max(0.05, random.uniform(0.1, 0.3) - loop_duration); time.sleep(sleep_time)
        except Exception as e:
             self.log(f"CRITICAL ERROR in bot loop: {e}", "ERROR")
             import traceback; self.log(traceback.format_exc(), "DEBUG")
             self._schedule_stop()
        finally:
            self.log("Bot thread loop finished.", "INFO")
            self._schedule_finalize_stop()

    def _schedule_stop(self):
        """Helper to schedule stop_bot from background thread."""
        if self.root and self.root.winfo_exists(): self.root.after(0, self.stop_bot)

    def _schedule_finalize_stop(self):
        """Helper to schedule final GUI updates after loop ends."""
        if self.root and self.root.winfo_exists():
             self.root.after(0, self._enable_inputs)
             self.root.after(10, lambda: self.log("Bot has stopped.", "SUCCESS"))


    def focus_aq3d(self):
        """Attempts to find and set focus to the AQ3D window."""
        try:
            hwnd = win32gui.FindWindow(None, "AQ3D");
            if not hwnd:
                if time.time() - getattr(self, '_last_focus_fail_log', 0) > 15: self.log("AQ3D window not found.", "WARNING"); setattr(self, '_last_focus_fail_log', time.time())
                return False
            if hwnd == win32gui.GetForegroundWindow(): return True
            try: win32gui.SetForegroundWindow(hwnd); time.sleep(0.05); return win32gui.GetForegroundWindow() == hwnd
            except Exception: pass
            try:
                placement = win32gui.GetWindowPlacement(hwnd); state = placement[1] if placement else win32con.SW_SHOWNORMAL
                if state == win32con.SW_SHOWMINIMIZED: win32gui.ShowWindow(hwnd, win32con.SW_RESTORE); time.sleep(0.1)
                win32gui.BringWindowToTop(hwnd); time.sleep(0.05); win32gui.SetForegroundWindow(hwnd); time.sleep(0.05)
                return win32gui.GetForegroundWindow() == hwnd
            except Exception as e: self.log(f"Focus restore error: {e}", "DEBUG"); return False
        except Exception as e: self.log(f"Focus error: {e}", "ERROR"); return False


    def find_and_attack_target(self):
        """Finds matching enemy via tabbing or moves randomly."""
        filters = [f.lower().strip() for f in self.target_enemy_names_list if f.strip()]
        found = False
        for _ in range(10):
            if not self.bot_running: return
            pyautogui.press('tab'); time.sleep(random.uniform(0.2, 0.4))
            name = self.read_enemy_name()
            if name:
                self.last_enemy_detection_time = time.time(); name_lower = name.lower()
                if not filters or any(f in name_lower for f in filters):
                    self.log(f"Target '{name}' found. Attacking.", "INFO"); self.attack_current_target(); found = True; return
        if not found: self.log("No matching enemy found. Moving.", "INFO"); self.move_randomly()


    def read_enemy_name(self):
        """Reads text from the enemy name area using OCR."""
        if not self._is_tesseract_ready() or not self.health_box: return None
        try:
            if not isinstance(self.health_box, (tuple, list)) or len(self.health_box) != 4: return None
            x1, y1, x2, y2 = map(int, self.health_box); assert x1 < x2 and y1 < y2
            ss = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            if not ss or not ss.getbbox(): return None
            img = ss.convert('L'); img = ImageEnhance.Contrast(img).enhance(1.8)
            thresh = 135; img = img.point(lambda p: 255 if p > thresh else 0); img = ImageOps.invert(img)
            cfg = r'--oem 3 --psm 6'; text = pytesseract.image_to_string(img, lang='eng', config=cfg, timeout=1.5).strip()
            filtered = ''.join(c for c in text if c.isalnum() or c.isspace() or c in ["'", "-"]).strip()
            return filtered if len(filtered) >= 2 else None
        except Exception as e: self.log(f"OCR Error (Enemy Name): {e}", "ERROR"); return None


    def attack_current_target(self):
        """Attacks the current target until lost or timeout."""
        start = time.time(); timeout = 90; check_interval = 1.0; last_check = 0
        name = self.read_enemy_name() or "Unknown"
        while self.bot_running:
            now = time.time()
            if now - last_check > check_interval:
                current = self.read_enemy_name(); last_check = now
                if not current: self.log(f"Target '{name}' lost.", "INFO"); break
            if now - start > timeout: self.log(f"Attack timeout for '{name}'.", "WARNING"); break
            self.last_enemy_detection_time = now
            used_skill = self.try_use_available_skill(now)
            if used_skill and self.jump_while_attacking.get() and random.random() < 0.25: pyautogui.press('space'); time.sleep(0.05)
            if now - getattr(self, 'last_attack_health_check', 0) > 2.5: self.check_and_handle_death(); setattr(self, 'last_attack_health_check', now)
            if not self.bot_running: return
            time.sleep(random.uniform(0.08, 0.20))

        if self.bot_running and self.collect_loot.get() and time.time() - start < timeout: self.loot_enemy()


    def try_use_available_skill(self, current_time):
        """Finds and uses the highest priority available skill."""
        ready = [i for i, en in enumerate(self.skill_enabled) if en and (current_time - self.last_skill_use_time[i]) >= self.skill_cooldowns[i]]
        if not ready: return False
        self.use_skill(max(ready)); return True


    def use_skill(self, idx):
        """Presses the key for the given skill index."""
        if 0 <= idx < len(self.skill_keys) and self.skill_keys[idx]:
             pyautogui.press(self.skill_keys[idx]); self.last_skill_use_time[idx] = time.time(); time.sleep(random.uniform(0.04, 0.08))


    def check_and_handle_death(self):
        """Checks for revive button or low health. Returns True if revive clicked."""
        now = time.time(); revived = False
        if now - getattr(self, 'last_revive_check_time', 0) > 2.0:
            self.last_revive_check_time = now
            if self.check_and_click_revive(): revived = True; return True
        if not revived and now - getattr(self, 'last_health_check_time', 0) > 1.5:
            self.last_health_check_time = now
            if self.player_health_box:
                health = self.get_player_health_percentage()
                if health is not None and health < self.potion_health_threshold:
                    self.log(f"Health {health}% < {self.potion_health_threshold}%. Potion.", "INFO")
                    if self.potion_hotkey: pyautogui.press(self.potion_hotkey); time.sleep(1.0); self.focus_aq3d()
                    else:
                        if now - getattr(self, '_lpkw', 0) > 30: self.log("Potion hotkey not set!", "WARNING"); setattr(self, '_lpkw', now)
        return revived


    def get_player_health_percentage(self):
        """Reads health via OCR. Returns % or None."""
        if not self._is_tesseract_ready() or not self.player_health_box: return None
        try:
            if not isinstance(self.player_health_box, (tuple, list)) or len(self.player_health_box) != 4: return None
            x1, y1, x2, y2 = map(int, self.player_health_box); assert x1 < x2 and y1 < y2
            ss = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            if not ss or not ss.getbbox(): return None
            img = ss.convert('L'); img = ImageEnhance.Contrast(img).enhance(2.8)
            thresh = 170; img = img.point(lambda p: 0 if p > thresh else 255)
            cfg = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789/%()'; text = pytesseract.image_to_string(img, lang='eng', config=cfg, timeout=1.5).strip()
            match = re.search(r'\((\d{1,3})\s*%\)', text) or re.search(r'(\d{1,3})\s*%', text)
            return max(0, min(100, int(match.group(1)))) if match else None
        except Exception as e: self.log(f"OCR Error (Player Health): {e}", "ERROR"); return None


    def check_and_click_revive(self):
        """Checks revive OCR, waits 5s, clicks if found. Returns True if clicked."""
        if not self._is_tesseract_ready() or not self.detect_revive_box: return False
        try:
            if not isinstance(self.detect_revive_box, (tuple, list)) or len(self.detect_revive_box) != 4: return False
            x1, y1, x2, y2 = map(int, self.detect_revive_box); assert x1 < x2 and y1 < y2
            ss = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            if not ss or not ss.getbbox(): return False
            img = ss.convert('L'); img = ImageEnhance.Contrast(img).enhance(2.5)
            thresh = 175; img = img.point(lambda p: 0 if p > thresh else 255)
            cfg=r'--oem 3 --psm 6'; text = pytesseract.image_to_string(img, lang='eng', config=cfg, timeout=1.0).strip()
            if "revive" in text.lower():
                self.log("Revive found. Waiting 5s...", "INFO"); wait_start = time.time()
                while time.time() - wait_start < 5.0:
                    if not self.bot_running: self.log("Stop during revive wait.", "INFO"); return False
                    time.sleep(0.1)
                if self.bot_running:
                    cx = x1 + (x2 - x1) / 2; cy = y1 + (y2 - y1) / 2
                    self.log(f"Clicking Revive ({int(cx)}, {int(cy)})", "INFO"); pyautogui.click(cx, cy); time.sleep(2.3)
                    pyautogui.press('esc'); time.sleep(0.6); self.focus_aq3d(); return True
                else: self.log("Stop before revive click.", "INFO"); return False
            return False
        except Exception as e: self.log(f"OCR Error (Revive): {e}", "ERROR"); return False


    def loot_enemy(self):
        """Attempts to loot via 'F' and clicking."""
        if not self.focus_aq3d(): self.log("Loot failed - focus lost.", "WARNING"); return

        time.sleep(0.15); pyautogui.press('f'); time.sleep(0.3)
        if self.loot_button_location:
            try:
                if isinstance(self.loot_button_location, (tuple, list)) and len(self.loot_button_location) == 2:
                    pyautogui.click(self.loot_button_location); time.sleep(0.2)
            except Exception as e: self.log(f"Loot click error: {e}", "ERROR")
        pyautogui.press('esc'); time.sleep(0.15); self.focus_aq3d()


    def move_randomly(self):
        """Performs random movements."""
        if not self.bot_running: return
        keys = [k for k, v in self.movement_keys.items() if v]
        if not keys:
            if time.time() - getattr(self, '_lmw', 0) > 60: self.log("No movement keys.", "WARNING"); setattr(self, '_lmw', time.time())
            time.sleep(1); return
        for _ in range(random.randint(1, max(1, self.movement_loops))):
            if not self.bot_running: break
            key = random.choice(keys); duration = random.uniform(0.15, 0.55)
            pyautogui.keyDown(key); start = time.time()
            while time.time() - start < duration:
                if not self.bot_running: break
                if self.jump_while_moving.get() and random.random() < 0.07: pyautogui.press('space'); time.sleep(0.05)
                time.sleep(0.02)
            pyautogui.keyUp(key); time.sleep(random.uniform(0.05, 0.15))
            if not self.bot_running: break


    def on_closing(self):
        """Handles the window close (X button) event."""
        self.unhook_hotkeys()
        if self.bot_running:
            if messagebox.askyesno("Confirm Quit", "Bot is running.\nStop bot and exit?", parent=self.root):
                self.stop_bot(); time.sleep(0.3)
                if self.settings_modified and messagebox.askyesno("Unsaved Settings", "Save changes before quitting?", parent=self.root): self.save_all_settings()
                self.root.destroy()
            else: self.setup_hotkeys(); return
        else:
            if self.settings_modified and messagebox.askyesno("Unsaved Settings", "Save changes before quitting?", parent=self.root): self.save_all_settings()
            self.root.destroy()

# --- Main Execution ---
def main():
    try: from ctypes import windll; windll.shcore.SetProcessDpiAwareness(1); print("DPI awareness set.")
    except Exception: print("Could not set DPI awareness.")

    root = ctk.CTk()
    app = BotApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()