from __future__ import annotations
import logging
import sys
from PySide6.QtWidgets import QApplication
from app.main_window import MainWindow

def main() -> int:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    app = QApplication(sys.argv)
    app.setApplicationName('MediaSelector')
    w = MainWindow(); w.show()
    return app.exec()

if __name__ == '__main__':
    raise SystemExit(main())
