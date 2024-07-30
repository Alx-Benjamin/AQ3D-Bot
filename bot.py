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

        self.aq3d_running = False
        self.health_box = None
        self.loot_button_location = None
        self.attack_keys = ['q', 'e', 'r']
        self.movement_keys = ['w', 'a', 's', 'd']
        self.movement_loops = 5
        self.player_health_box = None
        self.potion_hotkey = 'p'
        self.detect_revive_box = None
        self.revive_button_location = None
        self.collect_loot = tk.BooleanVar(value=True)  # Add Collect Loot variable  d   dd  a
        self.jump_while_moving = tk.BooleanVar()  # Initialize jump_while_moving
        self.jump_while_attacking = tk.BooleanVar()  # Initialize jump_while_attacking

        status_frame = ctk.CTkFrame(root)
        status_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        location_frame = ctk.CTkFrame(root)
        location_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        settings_frame = ctk.CTkFrame(root)
        settings_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        action_frame = ctk.CTkFrame(root)
        action_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

        log_frame = ctk.CTkFrame(root)
        log_frame.grid(row=0, column=1, rowspan=4, padx=10, pady=10, sticky="nsew")

        # --- Status Frame ---
        self.aq3d_status_label = ctk.CTkLabel(status_frame, text="Not Running")
        self.aq3d_status_label.grid(row=0, column=1, padx=5)
        ctk.CTkLabel(status_frame, text="AQ3D Status:").grid(row=0, column=0, padx=5)
        ctk.CTkButton(status_frame, text="Check AQ3D Status",
                     command=self.check_aq3d_status).grid(row=1, column=0, columnspan=2, pady=5)

        # --- Location Frame ---
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

        # --- Settings Frame ---
        ctk.CTkLabel(settings_frame, text="Attack Buttons:").grid(row=0, column=0)
        self.attack_buttons_entry = ctk.CTkEntry(settings_frame)
        self.attack_buttons_entry.grid(row=0, column=1)
        self.attack_buttons_entry.insert(0, ', '.join(self.attack_keys))
        ctk.CTkButton(settings_frame, text="Save Attack Buttons",
                     command=self.save_attack_buttons).grid(row=0, column=2, padx=5)

        ctk.CTkLabel(settings_frame, text="Movement Buttons:").grid(row=1, column=0)
        self.movement_buttons_entry = ctk.CTkEntry(settings_frame)
        self.movement_buttons_entry.grid(row=1, column=1)
        self.movement_buttons_entry.insert(0, ', '.join(self.movement_keys))
        ctk.CTkButton(settings_frame, text="Save Movement Buttons",
                     command=self.save_movement_buttons).grid(row=1, column=2, padx=5)

        ctk.CTkLabel(settings_frame, text="Movement Loops:").grid(row=2, column=0)
        self.movement_loops_entry = ctk.CTkEntry(settings_frame)
        self.movement_loops_entry.grid(row=2, column=1)
        self.movement_loops_entry.insert(0, str(self.movement_loops))
        ctk.CTkButton(settings_frame, text="Save Movement Loops",
                     command=self.save_movement_loops).grid(row=2, column=2, padx=5)

        ctk.CTkLabel(settings_frame, text="Potion Hotkey:").grid(row=3, column=0)
        self.potion_hotkey_entry = ctk.CTkEntry(settings_frame)
        self.potion_hotkey_entry.grid(row=3, column=1)
        self.potion_hotkey_entry.insert(0, self.potion_hotkey)
        ctk.CTkButton(settings_frame, text="Save Potion Hotkey",
                     command=self.save_potion_hotkey).grid(row=3, column=2, padx=5)

        # --- Action Frame ---
        ctk.CTkCheckBox(action_frame, text="Jump While Moving",
                       variable=self.jump_while_moving).grid(row=0, column=0, columnspan=2)
        ctk.CTkCheckBox(action_frame, text="Jump While Attacking",
                       variable=self.jump_while_attacking).grid(row=1, column=0, columnspan=2)
        ctk.CTkCheckBox(action_frame, text="Collect Loot",  # Add Collect Loot checkbox
                       variable=self.collect_loot).grid(row=2, column=0, columnspan=2)
        ctk.CTkButton(action_frame, text="Start Bot", command=self.start_bot).grid(row=3, column=0, pady=5)
        self.stop_button = ctk.CTkButton(action_frame, text="Stop Bot", command=self.stop_bot)  
        self.stop_button.grid(row=3, column=1, pady=5)

        # --- Log Frame --- (Make log text box scalable)
        self.log_text = ctk.CTkTextbox(log_frame, width=300, height=200, wrap="word")  
        self.log_text.pack(expand=True, fill="both")  # Expand to fill frame

        self.load_settings()
        self.check_aq3d_status()

    def log(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.yview(tk.END)

    def check_aq3d_status(self):
        self.aq3d_running = any(proc.name() == "AQ3D.exe" for proc in psutil.process_iter())
        self.aq3d_status_label.configure(text="Running" if self.aq3d_running else "Not Running")
        self.log("Checked AQ3D status")

    def set_health_location(self):
        self.log("Click on the top-left and bottom-right corners of the enemy health bar")
        overlay = Overlay(self.root)
        self.log("Setting top-left corner")
        top_left = overlay.get_coords()
        if top_left:
            self.log("Setting bottom-right corner")
            overlay = Overlay(self.root)
            bottom_right = overlay.get_coords()
            if bottom_right:
                self.health_box = (*top_left, *bottom_right)
                self.health_location_label.configure(text=f"Enemy Health Location: {self.health_box}")
                self.log(f"Enemy health area set: {self.health_box}")
                self.save_settings()
            else:
                self.log("Operation cancelled")
        else:
            self.log("Operation cancelled")

    def set_player_health_location(self):
        self.log("Click on the top-left and bottom-right corners of the player health bar")
        overlay = Overlay(self.root)
        self.log("Setting top-left corner")
        top_left = overlay.get_coords()
        if top_left:
            self.log("Setting bottom-right corner")
            overlay = Overlay(self.root)
            bottom_right = overlay.get_coords()
            if bottom_right:
                self.player_health_box = (*top_left, *bottom_right)
                self.player_health_location_label.configure(text=f"Player Health Location: {self.player_health_box}")
                self.log(f"Player health area set: {self.player_health_box}")
                self.save_settings()
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
            self.save_settings()
        else:
            self.log("Operation cancelled")

    def set_detect_revive_location(self):
        self.log("Click on the top-left and bottom-right corners of the area to detect revive button")
        overlay = Overlay(self.root)
        self.log("Setting top-left corner")
        top_left = overlay.get_coords()
        if top_left:
            self.log("Setting bottom-right corner")
            overlay = Overlay(self.root)
            bottom_right = overlay.get_coords()
            if bottom_right:
                self.detect_revive_box = (*top_left, *bottom_right)
                self.detect_revive_location_label.configure(text=f"Detect Revive Location: {self.detect_revive_box}")
                self.log(f"Detect revive area set: {self.detect_revive_box}")
                self.save_settings()
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
            self.save_settings()
        else:
            self.log("Operation cancelled")

    def save_attack_buttons(self):
        self.attack_keys = [key.strip() for key in self.attack_buttons_entry.get().split(',')]
        self.log(f"Attack buttons saved: {self.attack_keys}")
        self.save_settings()

    def save_movement_buttons(self):
        self.movement_keys = [key.strip() for key in self.movement_buttons_entry.get().split(',')]
        self.log(f"Movement buttons saved: {self.movement_keys}")
        self.save_settings()

    def save_movement_loops(self):
        try:
            self.movement_loops = int(self.movement_loops_entry.get())
            self.log(f"Movement loops saved: {self.movement_loops}")
            self.save_settings()
        except ValueError:
            self.log("Invalid input for movement loops")

    def save_potion_hotkey(self):
        self.potion_hotkey = self.potion_hotkey_entry.get().strip()
        self.log(f"Potion hotkey saved: {self.potion_hotkey}")
        self.save_settings()

    def save_settings(self):
        settings = {
            'health_box': self.health_box,
            'player_health_box': self.player_health_box,
            'loot_button_location': self.loot_button_location,
            'attack_keys': self.attack_keys,
            'movement_keys': self.movement_keys,
            'movement_loops': self.movement_loops,
            'potion_hotkey': self.potion_hotkey,
            'detect_revive_box': self.detect_revive_box,
            'revive_button_location': self.revive_button_location,
            'collect_loot': self.collect_loot.get()  # Save Collect Loot status
        }
        with open('settings.json', 'w') as f:
            json.dump(settings, f)
        self.log("Settings saved")

    def load_settings(self):
        if os.path.exists('settings.json'):
            with open('settings.json', 'r') as f:
                settings = json.load(f)
            self.health_box = settings.get('health_box')
            self.player_health_box = settings.get('player_health_box')
            self.loot_button_location = settings.get('loot_button_location')
            self.attack_keys = settings.get('attack_keys', ['q', 'e', 'r'])
            self.movement_keys = settings.get('movement_keys', ['w', 'a', 's', 'd'])
            self.movement_loops = settings.get('movement_loops', 5)
            self.potion_hotkey = settings.get('potion_hotkey', 'p')
            self.detect_revive_box = settings.get('detect_revive_box')
            self.revive_button_location = settings.get('revive_button_location')

            self.health_location_label.configure(text=f"Enemy Health Location: {self.health_box if self.health_box else 'Not Set'}")
            self.player_health_location_label.configure(text=f"Player Health Location: {self.player_health_box if self.player_health_box else 'Not Set'}")
            self.loot_location_label.configure(text=f"Loot Button Location: {self.loot_button_location if self.loot_button_location else 'Not Set'}")
            self.detect_revive_location_label.configure(text=f"Detect Revive Location: {self.detect_revive_box if self.detect_revive_box else 'Not Set'}")
            self.revive_button_location_label.configure(text=f"Revive Button Location: {self.revive_button_location if self.revive_button_location else 'Not Set'}")
            self.attack_buttons_entry.delete(0, tk.END)
            self.attack_buttons_entry.insert(0, ', '.join(self.attack_keys))
            self.movement_buttons_entry.delete(0, tk.END)
            self.movement_buttons_entry.insert(0, ', '.join(self.movement_keys))
            self.movement_loops_entry.delete(0, tk.END)
            self.movement_loops_entry.insert(0, str(self.movement_loops))
            self.potion_hotkey_entry.delete(0, tk.END)
            self.potion_hotkey_entry.insert(0, self.potion_hotkey)
            self.collect_loot.set(settings.get('collect_loot', True))  # Load Collect Loot status
            self.log("Settings loaded")
        else:
            self.log("No settings file found, using defaults")

    def start_bot(self):
        if not self.aq3d_running:
            self.log("AQ3D is not running. Start the game before starting the bot.")
            return
        if not self.health_box or not self.loot_button_location or not self.detect_revive_box or not self.revive_button_location:
            self.log("Please set all required locations before starting the bot.")
            return

        self.bot_running = True
        self.log("Bot started")
        self.stop_button.configure(state="normal")  # Enable Stop button
        self.bot_thread = threading.Thread(target=self.bot_loop)
        self.bot_thread.daemon = True # Make thread a daemon so it exits when the main program exits
        self.bot_thread.start()

    def stop_bot(self):
        self.bot_running = False
        self.stop_button.configure(state="disabled")  # Disable Stop button
        self.log("Bot will stop after current rotation..")

    def bot_loop(self):
        while self.bot_running:
            self.focus_aq3d() # Ensure AQ3D is the active window
            self.select_enemy()
            time.sleep(1)

    def focus_aq3d(self):
        try:
            # Find the AQ3D window handle
            hwnd = win32gui.FindWindow(None, "AQ3D")
            if not hwnd:
                raise Exception("AQ3D window not found")

            # Get the handle of the currently active window
            active_hwnd = win32gui.GetForegroundWindow()

            # Only focus if not already active
            if hwnd != active_hwnd:
                # Minimize and then maximize to bring to front reliably
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                time.sleep(0.2)  # Brief delay (adjust if needed)
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

                # Set as foreground and active
                win32gui.SetForegroundWindow(hwnd)
                win32gui.SetActiveWindow(hwnd)

                self.log("Focused AQ3D window.")
            else:
                #self.log("AQ3D already focused.")  # (Optional log)
                pass

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
            #self.log(f"Average color detected while checking if enemy is detected: {average_color}")
            target_color = (166, 4, 4) 
            tolerance = 30 

            if self.is_color_within_tolerance(average_color, target_color, tolerance):
                self.log("Enemy detected")
                return True
            else:
                return False
        else:
            return False

    def attack_enemy(self):
        self.log("Starting attack")
        while self.is_enemy_detected(): 
            button = random.choice(self.attack_keys)
            self.log(f"Pressing button: {button}")
            pyautogui.press(button)
            time.sleep(random.randint(2, 5))
            if self.jump_while_attacking.get() and random.random() < 0.2:
                pyautogui.press('space')
            self.check_and_handle_death()
        
        # Check for enemies again before looting
        if not self.is_enemy_detected() and self.collect_loot.get():
            self.loot_enemy() 

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
        time.sleep(3)
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
            #self.log(f"Average player health color: {average_color}")

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
            #self.log(f"Average color in revive area: {average_color}")
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
            if self.jump_while_moving.get() and random.random() < 0.1:
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