from __future__ import annotations

import time

import psutil
import win32con
import win32gui


PROCESS_NAME = "AQ3D.exe"
WINDOW_TITLE = "AQ3D"


class AQ3DWindow:
    """Manages detection and focusing of the AQ3D game window."""

    def __init__(self):
        self._hwnd: int = 0

    def is_game_running(self) -> bool:
        """Check if the AQ3D process is currently running."""
        try:
            return any(
                p.name() == PROCESS_NAME for p in psutil.process_iter(["name"])
            )
        except Exception:
            return False

    def find_window(self) -> int:
        """Find the AQ3D window handle. Returns 0 if not found."""
        self._hwnd = win32gui.FindWindow(None, WINDOW_TITLE)
        return self._hwnd

    def focus(self) -> bool:
        """Bring the AQ3D window to the foreground.

        Returns True if the window was successfully focused.
        """
        hwnd = self.find_window()
        if not hwnd:
            return False

        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.1)
            return win32gui.GetForegroundWindow() == hwnd
        except Exception:
            return False

    def is_focused(self) -> bool:
        """Check if the AQ3D window currently has focus."""
        if not self._hwnd:
            self.find_window()
        try:
            return win32gui.GetForegroundWindow() == self._hwnd
        except Exception:
            return False
