"""DataViewer 실행 진입점."""
import sys

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.theme import STYLESHEET


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
