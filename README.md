# DeadLink's AQ3D Bot

A customizable automation bot for **AdventureQuest 3D** built with Python and PySide6. Features human-like play patterns, a visual rotation builder for per-class combat optimization, shareable profiles, and a screen-reading-only approach for safer botting.

**Version 4.0.0** — Full rewrite with modular architecture and a modern dark-themed UI.

[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white)](https://discord.gg/MfW5Mt7KUe)
[![Donate](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Support-FFDD00?logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/deadlink)

---

## Features

### Human-Like Play
The bot simulates natural gameplay rather than robotic precision. Movement uses random WASD key presses with varying durations, combat includes configurable random delays between skills, and optional random jumps during attacking and moving add a layer of organic behavior. There is no frame-perfect timing or pixel-perfect clicking — inputs are staggered and varied to mimic a real player.

### Custom Class Rotations
Build per-class skill rotations with a visual drag-and-drop rotation builder. Define the exact sequence of 9 skill slots (1 Auto Attack + 5 Class Skills + 3 Cross Skills), insert wait/pause steps between abilities, and fine-tune random delay ranges. The bot executes your rotation in strict order, automatically tracking cooldowns and waiting for skills to come off cooldown before pressing them. This lets you maximize class performance the same way a skilled player would.

### Shareable Bot Profiles
Each class setup is saved as its own profile — skills, rotation, potion settings, loot preferences, death handling, and target filters all in one portable JSON file. Export a profile and share it with others, or import profiles from the community. Duplicate, rename, and hot-swap profiles on the fly without restarting the bot. The sidebar dropdown lets you switch classes in seconds.

### Screen-Reading Only (No Memory Injection)
The bot reads the game screen using OCR (Tesseract) and sends standard keyboard/mouse inputs — it never touches game memory, injects DLLs, or sends custom network packets. This approach is inherently safer because it interacts with the game the same way a human does: by looking at the screen and pressing keys.

### Smart Combat System
- **Tab-target searching** — presses Tab to cycle through nearby enemies
- **OCR name detection** — reads the enemy nameplate to confirm a target is selected
- **Target filtering** — only fight specific enemies by name (partial match, case-insensitive)
- **90-second attack timeout** — prevents getting stuck on unkillable targets
- **Auto-looting** — collects loot after kills with configurable hotkeys

### Health Monitoring & Auto-Potions
Reads your health bar via OCR and automatically uses a potion when HP drops below a configurable threshold (default 50%). Potion hotkey, threshold percentage, and cooldown are all customizable per profile.

### Death Handling & Recovery
Detects player death through OCR, automatically clicks the revive button after a short delay, and optionally holds W to run back to the combat area. You can also configure the bot to stop entirely on death if you prefer manual recovery.

### AFK System
Go AFK on a schedule — the bot idles for a set duration at configurable intervals. If an enemy attacks during AFK, the bot fights back using your full rotation, auto-revives if killed, and returns to AFK once the threat is handled. AFK duration is capped at 15 minutes for safety.

### Timeout & Safety Limits
- **No enemy timeout** — stops the bot if no enemy is found for X minutes
- **Max runtime** — automatically stops after X hours
- **Attack timeout** — abandons a target after 90 seconds
- **AQ3D process monitor** — stops if the game closes
- **Clean stop** — all blocking operations check a stop flag every 0.1 seconds

### Live Dashboard
A real-time dashboard shows bot state (with color coding), current target name, player HP as a progress bar, kill count, and a runtime timer. Nine cooldown bars display each skill's status. Three OCR preview panels show raw screenshots alongside preprocessed images and recognized text. A scrolling log viewer with color-coded entries (DEBUG/INFO/SUCCESS/WARNING/ERROR) shows exactly what the bot is doing.

### Configurable Screen Regions
An interactive fullscreen overlay lets you drag-select the screen regions the bot should read: enemy nameplate, player health bar, menu close point, and revive button area. Multi-monitor and DPI scaling are handled automatically.

### Modern UI
Dark theme using the Catppuccin Mocha color palette with color-coded skill types (yellow for Auto Attack, blue for Class, purple for Cross Skills). Card-based layouts, hover effects, custom scrollbars, and a system tray with minimize-on-close support.

### Global Hotkeys
**F5** to start, **F6** to stop — works even when the bot window is not focused.

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| UI Framework | PySide6 (Qt6) |
| OCR Engine | Tesseract (bundled — no install required) |
| OCR Wrapper | pytesseract |
| Image Processing | Pillow (PIL) |
| Input Simulation | pyautogui |
| Global Hotkeys | keyboard |
| Window Management | pywin32 |
| Process Detection | psutil |
| Build / Distribution | cx_Freeze (MSI installer), PyInstaller |

---

## How It Works

### Architecture

```
aq3d_bot/
├── core/           # Bot engine and subsystems
│   ├── engine.py   # QThread state machine (main loop)
│   ├── ocr.py      # Tesseract OCR preprocessing & recognition
│   ├── combat.py   # Target finding, skill rotation execution
│   ├── movement.py # Random WASD movement
│   ├── health.py   # HP monitoring, auto-potions
│   ├── death.py    # Revive detection, run-back
│   └── afk.py      # AFK scheduling, fight-back logic
├── models/         # Data layer
│   ├── settings.py # Global settings dataclass
│   ├── profile.py  # Profile + rotation step dataclasses
│   ├── skill.py    # Skill dataclass (9 slots)
│   └── migration.py# Legacy format conversion (v0/v1 → v2)
├── ui/             # Presentation layer
│   ├── app.py      # MainWindow, system tray, lifecycle
│   ├── pages/      # Dashboard, Combat, Settings, Profiles, About
│   ├── widgets/    # Cooldown bars, log viewer, OCR preview, overlay, rotation builder
│   └── styles/     # Catppuccin Mocha QSS theme
└── resources/
    └── tesseract/  # Bundled Tesseract OCR (exe + DLLs + traineddata)
```

### State Machine

The bot engine runs as a QThread with the following states:

```
START → SEARCHING ⇄ MOVING (random WASD when no enemies found)
            ↓
       ATTACKING → LOOTING → SEARCHING
            ↓
       (player dies)
            ↓
         DEAD → REVIVING → RUNNING_BACK → SEARCHING

SEARCHING → (AFK timer) → AFK → (attacked) → ATTACKING → AFK
```

Every state transition is logged. All blocking waits (cooldowns, sleep, run-back) are broken into 0.1-second intervals that check a stop flag, so the bot responds to F6 within 100ms regardless of what it's doing.

### OCR Pipeline

1. Capture a screen region with `PIL.ImageGrab.grab(bbox)`
2. Convert to grayscale
3. Enhance contrast (1.8x–2.8x depending on region)
4. Apply binary threshold (135–175)
5. Optionally invert for dark-on-light text
6. Run Tesseract with tuned PSM mode and character whitelists
7. Clean and pattern-match the result (regex for HP%, substring for "Revive", alphanumeric filter for enemy names)

Three presets are used for different regions, each with optimized contrast, threshold, and inversion settings.

### Threading Model

| Thread | Purpose |
|---|---|
| Main thread | PySide6 UI event loop |
| Engine thread | QThread running the state machine |
| Hotkey thread | `keyboard` module callbacks, bridged to Qt via signals |

All engine-to-UI communication uses Qt signals for thread safety. The stop flag is protected by a QMutex.

### Settings Split

Configuration is split into two file types:
- **`settings.json`** — global settings (screen regions, movement, timers, window preferences)
- **`profiles/<name>.json`** — per-class settings (skills, rotation, potions, loot, death, targeting)

This lets you swap combat profiles without losing your screen region calibration.

---

## Getting Started

### Requirements
- Windows 10/11
- Python 3.10+
- AdventureQuest 3D (Steam or standalone)

### Installation

```bash
git clone https://github.com/Alx-Benjamin/AQ3D-Bot.git
cd AQ3D-Bot
pip install -r requirements.txt
```

### Running

```bash
python -m aq3d_bot.main
```

Or use the pre-built MSI installer from the [Releases](https://github.com/Alx-Benjamin/AQ3D-Bot/releases) page.

### Quick Start

1. Launch AQ3D and log into your character
2. Launch the bot
3. Go to **Settings > Screen Regions** and select your enemy nameplate area
4. Go to **Combat** and configure your skills and rotation
5. Press **F5** to start

---

## Disclaimer

**Botting in AdventureQuest 3D is against the game's Terms of Service.** Use of this software may result in account suspension or permanent ban.

This project is provided for **educational and personal use only**. The developers do not condone, encourage, or endorse the use of automation tools to gain an unfair advantage in online games. By using this software, you acknowledge that:

- You are solely responsible for any consequences to your game account
- You use this software entirely at your own risk
- The developers are not liable for any bans, suspensions, or other actions taken against your account
- This project is an exercise in automation, OCR, and UI development — not an invitation to cheat

**Play fair. You have been warned.**

---

## Links

- [Discord](https://discord.gg/MfW5Mt7KUe)
- [Donate](https://buymeacoffee.com/deadlink)
- [Source Code](https://github.com/Alx-Benjamin/AQ3D-Bot)
