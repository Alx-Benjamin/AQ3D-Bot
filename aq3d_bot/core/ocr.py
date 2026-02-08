from __future__ import annotations

import os
import sys
import re

import pytesseract
from PIL import Image, ImageEnhance, ImageGrab, ImageOps


# Preprocessing presets: each maps to (contrast, threshold, invert)
_PRESETS: dict[str, dict] = {
    "enemy_name": {"contrast": 1.8, "threshold": 135, "invert": True},
    "health": {"contrast": 2.8, "threshold": 170, "invert": False},
    "revive": {"contrast": 2.5, "threshold": 175, "invert": False},
}


class OCREngine:
    """Unified OCR engine with bundled Tesseract path resolution.

    Searches for Tesseract in this order:
      1. Bundled: resources/tesseract/tesseract.exe (or PyInstaller _MEIPASS)
      2. Common install paths on Windows
      3. System PATH
    """

    def __init__(self):
        self._tesseract_path: str | None = None
        self._configured = False
        self._resolve_tesseract_path()

    @property
    def is_ready(self) -> bool:
        return self._configured

    @property
    def tesseract_path(self) -> str | None:
        return self._tesseract_path

    def _resolve_tesseract_path(self) -> None:
        """Find and validate the Tesseract executable."""
        candidates: list[str] = []

        # 1. Bundled path (PyInstaller or dev)
        if getattr(sys, "frozen", False):
            base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bundled = os.path.join(base, "resources", "tesseract", "tesseract.exe")
        candidates.append(bundled)

        # 2. Common Windows install paths
        candidates.extend([
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ])

        for path in candidates:
            if os.path.isfile(path):
                try:
                    pytesseract.pytesseract.tesseract_cmd = path
                    # Set TESSDATA_PREFIX to the tessdata directory itself
                    tess_dir = os.path.dirname(path)
                    tessdata_dir = os.path.join(tess_dir, "tessdata")
                    if os.path.isdir(tessdata_dir):
                        os.environ["TESSDATA_PREFIX"] = tessdata_dir
                    pytesseract.get_tesseract_version()
                    self._tesseract_path = path
                    self._configured = True
                    return
                except Exception:
                    continue

        # 3. System PATH fallback
        try:
            pytesseract.get_tesseract_version()
            self._configured = True
        except Exception:
            self._configured = False

    def read_region(
        self,
        bbox: tuple[int, int, int, int],
        preset: str = "enemy_name",
        psm: int = 6,
        whitelist: str | None = None,
    ) -> tuple[str, Image.Image]:
        """Grab a screen region, preprocess, and OCR it.

        Returns:
            (recognized_text, processed_image) — the processed image is useful
            for the OCR debug preview widget.
        """
        if not self._configured:
            return ("", Image.new("RGB", (1, 1)))

        img = ImageGrab.grab(bbox=bbox)
        processed = self._preprocess(img, preset)

        config = f"--oem 3 --psm {psm}"
        if whitelist:
            config += f" -c tessedit_char_whitelist={whitelist}"

        text = pytesseract.image_to_string(processed, lang="eng", config=config).strip()
        return (text, processed)

    def read_enemy_name(self, bbox: tuple[int, int, int, int]) -> str | None:
        """Read the enemy name from the configured region.

        Uses the same preprocessing as the original bot: grayscale, contrast 1.8,
        threshold 135, invert, PSM 6.

        Returns cleaned name or None if nothing detected.
        """
        text, _ = self.read_region(bbox, preset="enemy_name", psm=6)
        cleaned = "".join(c for c in text if c.isalnum() or c.isspace()).strip()
        return cleaned or None

    def read_health_percentage(self, bbox: tuple[int, int, int, int]) -> int | None:
        """Read the player health percentage from the configured region.

        Looks for a pattern like '78%' or '78 %'.
        """
        text, _ = self.read_region(
            bbox, preset="health", psm=7, whitelist="0123456789/%"
        )
        match = re.search(r"(\d{1,3})\s*%", text)
        return int(match.group(1)) if match else None

    def read_revive_text(self, bbox: tuple[int, int, int, int]) -> bool:
        """Check if the revive button text is visible in the configured region."""
        text, _ = self.read_region(bbox, preset="revive", psm=6)
        return "revive" in text.lower()

    def snapshot_region(
        self, bbox: tuple[int, int, int, int], preset: str = "enemy_name"
    ) -> tuple[str, Image.Image, Image.Image]:
        """Capture a region for OCR preview display.

        Returns:
            (recognized_text, raw_screenshot, processed_image)
        """
        if not self._configured:
            blank = Image.new("RGB", (1, 1))
            return ("", blank, blank)

        raw = ImageGrab.grab(bbox=bbox)
        processed = self._preprocess(raw, preset)
        config = "--oem 3 --psm 6"
        text = pytesseract.image_to_string(processed, lang="eng", config=config).strip()
        return (text, raw, processed)

    @staticmethod
    def _preprocess(img: Image.Image, preset: str) -> Image.Image:
        """Apply preset-specific image preprocessing for OCR."""
        params = _PRESETS.get(preset, _PRESETS["enemy_name"])

        img = img.convert("L")
        img = ImageEnhance.Contrast(img).enhance(params["contrast"])

        threshold = params["threshold"]
        if params.get("invert"):
            img = img.point(lambda p: 255 if p > threshold else 0)
            img = ImageOps.invert(img)
        else:
            img = img.point(lambda p: 0 if p > threshold else 255)

        return img
