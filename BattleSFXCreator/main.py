from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

try:
    from BattleSFXCreator.app.main_window import MainWindow  # type: ignore
    from BattleSFXCreator.app.theme import apply_default_theme  # type: ignore
except ImportError:
    if __package__ in (None, ""):
        current_dir = Path(__file__).resolve().parent
        if str(current_dir) not in sys.path:
            sys.path.insert(0, str(current_dir))
        from app.main_window import MainWindow  # type: ignore
        from app.theme import apply_default_theme  # type: ignore
    else:
        from .app.main_window import MainWindow
        from .app.theme import apply_default_theme


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)

    qt_app = QApplication(argv)
    apply_default_theme(qt_app)
    window = MainWindow()
    window.show()
    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
