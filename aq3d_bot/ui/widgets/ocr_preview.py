from __future__ import annotations

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame
from PIL import Image


def pil_to_qpixmap(pil_img: Image.Image, max_width: int = 200) -> QPixmap:
    """Convert a PIL Image to a QPixmap, scaling if needed."""
    if pil_img.mode == "L":
        pil_img = pil_img.convert("RGB")
    elif pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")

    data = pil_img.tobytes("raw", "RGB")
    qimg = QImage(data, pil_img.width, pil_img.height, pil_img.width * 3, QImage.Format.Format_RGB888)
    pixmap = QPixmap.fromImage(qimg)

    if pixmap.width() > max_width:
        pixmap = pixmap.scaledToWidth(max_width, Qt.TransformationMode.SmoothTransformation)

    return pixmap


class OCRPreviewBox(QFrame):
    """Single OCR region preview — shows the captured image and recognized text."""

    def __init__(self, title: str = "Region", parent=None):
        super().__init__(parent)
        self.setObjectName("card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("subheading")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title_label)

        self._image_label = QLabel()
        self._image_label.setMinimumHeight(36)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet(
            "background-color: #11111b; border: 1px solid #313244; border-radius: 4px; padding: 4px;"
        )
        self._image_label.setText("No data")
        layout.addWidget(self._image_label)

        self._text_label = QLabel("—")
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_label.setWordWrap(True)
        layout.addWidget(self._text_label)

    def update_preview(self, image: Image.Image | None, text: str = "") -> None:
        """Update the preview with a new image and OCR text."""
        if image is not None:
            max_w = max(self._image_label.width() - 8, 100)
            pixmap = pil_to_qpixmap(image, max_width=max_w)
            self._image_label.setPixmap(pixmap)
        else:
            self._image_label.setText("No data")

        display_text = text.strip() if text.strip() else "—"
        if len(display_text) > 40:
            display_text = display_text[:37] + "..."
        self._text_label.setText(display_text)


class OCRPreviewPanel(QWidget):
    """Panel showing OCR previews for all configured regions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.enemy_preview = OCRPreviewBox("Enemy Name")
        self.health_preview = OCRPreviewBox("Player Health")
        self.revive_preview = OCRPreviewBox("Revive Button")

        layout.addWidget(self.enemy_preview, stretch=1)
        layout.addWidget(self.health_preview, stretch=1)
        layout.addWidget(self.revive_preview, stretch=1)

    @Slot(str, object, str)
    def on_ocr_snapshot(self, region_name: str, image, text: str) -> None:
        """Handle OCR snapshot signals from the engine."""
        preview_map = {
            "enemy_name": self.enemy_preview,
            "health": self.health_preview,
            "revive": self.revive_preview,
        }
        preview = preview_map.get(region_name)
        if preview:
            preview.update_preview(image, text)
