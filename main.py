"""
Spektro-Control — Software kontrol UVmini-1240 via RS-232C.
Entry point aplikasi.
"""

import sys
import logging
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow


import os
from datetime import datetime

def setup_logging():
    """Setup logging ke console dan file untuk debugging."""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Generate log filename with current date
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = f"logs/spektro-control_{today}.log"
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info("==================================================")
    logging.info("Aplikasi Spektro-Control dijalankan")


def main():
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("Spektro-Control")
    app.setOrganizationName("Lab Kimia")

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
