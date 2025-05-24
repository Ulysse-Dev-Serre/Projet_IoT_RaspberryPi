# main.py
import sys
from PyQt6.QtWidgets import QApplication
from base_window import BaseWindow # Importe la BaseWindow modifiée

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_application_window = BaseWindow() # Crée la fenêtre principale
    main_application_window.show()
    sys.exit(app.exec())