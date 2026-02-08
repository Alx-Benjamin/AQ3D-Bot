"""cx_Freeze setup script — builds a frozen exe and MSI installer."""

import os
import site
import sys
from cx_Freeze import setup, Executable

# Locate pywin32 DLLs (pywintypes312.dll, pythoncom312.dll)
# These live in pywin32_system32/ and cx_Freeze doesn't find them automatically.
_pywin32_dlls = []
for sp in site.getsitepackages():
    pw32_dir = os.path.join(sp, "pywin32_system32")
    if os.path.isdir(pw32_dir):
        for dll in os.listdir(pw32_dir):
            if dll.endswith(".dll"):
                _pywin32_dlls.append((os.path.join(pw32_dir, dll), dll))
        break

build_exe_options = {
    "include_files": [
        # Entire Tesseract bundle (exe + 56 DLLs + tessdata/)
        ("aq3d_bot/resources/tesseract/", "resources/tesseract/"),
        ("aq3d_bot/resources/icons/logo.ico", "resources/icons/logo.ico"),
        ("aq3d_bot/ui/styles/theme.qss", "ui/styles/theme.qss"),
    ] + _pywin32_dlls,
    "packages": [
        "aq3d_bot",
        "aq3d_bot.core",
        "aq3d_bot.models",
        "aq3d_bot.ui",
        "aq3d_bot.ui.pages",
        "aq3d_bot.ui.widgets",
        "win32api",
        "win32gui",
        "win32con",
        "win32process",
    ],
    "excludes": ["tkinter", "unittest", "test"],
    "include_msvcr": True,
}

bdist_msi_options = {
    "initial_target_dir": r"[LocalAppDataFolder]\DeadLinks AQ3D Bot",
    "all_users": False,
    "install_icon": "aq3d_bot/resources/icons/logo.ico",
    "summary_data": {
        "author": "DeadLink",
        "comments": "AQ3D automation bot",
    },
    "upgrade_code": "{0C407F12-C99F-4389-A656-EB3AFE8BA236}",
}

exe = Executable(
    script="aq3d_bot/main.py",
    base="gui",
    target_name="AQ3D Bot.exe",
    icon="aq3d_bot/resources/icons/logo.ico",
    shortcut_name="DeadLink's AQ3D Bot",
    shortcut_dir="StartMenuFolder",
)

setup(
    name="DeadLinks AQ3D Bot",
    version="4.0.0",
    description="AQ3D automation bot",
    options={
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options,
    },
    executables=[exe],
)
