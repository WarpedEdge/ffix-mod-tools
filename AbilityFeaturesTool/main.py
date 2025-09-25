from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

try:
    from AbilityFeaturesTool.app.main_window import MainWindow  # type: ignore
except ImportError:
    if __package__ in (None, ""):
        current_dir = Path(__file__).resolve().parent
        if str(current_dir) not in sys.path:
            sys.path.insert(0, str(current_dir))
        try:
            from app.main_window import MainWindow  # type: ignore
        except ImportError:
            raise
    else:
        from .app.main_window import MainWindow


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)

    qt_app = QApplication(argv)
    window = MainWindow()
    window.show()
    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
