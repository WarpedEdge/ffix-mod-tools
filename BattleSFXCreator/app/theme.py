"""Application theming helpers."""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def apply_default_theme(app: QApplication) -> None:
    """Apply a dark Fusion theme while keeping contrast legible."""

    app.setStyle("Fusion")
    palette = app.palette()

    def color(r: int, g: int, b: int) -> QColor:
        return QColor(r, g, b)

    palette.setColor(QPalette.Window, color(37, 37, 42))
    palette.setColor(QPalette.WindowText, color(235, 235, 240))
    palette.setColor(QPalette.Base, color(26, 26, 30))
    palette.setColor(QPalette.AlternateBase, color(45, 45, 50))
    palette.setColor(QPalette.Text, color(235, 235, 240))
    palette.setColor(QPalette.Button, color(45, 45, 50))
    palette.setColor(QPalette.ButtonText, color(235, 235, 240))
    palette.setColor(QPalette.Highlight, color(76, 110, 219))
    palette.setColor(QPalette.HighlightedText, color(255, 255, 255))
    palette.setColor(QPalette.ToolTipBase, color(250, 250, 255))
    palette.setColor(QPalette.ToolTipText, color(32, 32, 32))
    palette.setColor(QPalette.BrightText, color(255, 96, 96))

    app.setPalette(palette)
