"""Fortnite Crash Analyzer - Main Entry Point

A PyQt6 application for analyzing Fortnite crash dumps in a user-friendly way.
"""
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Fortnite Crash Analyzer")
    app.setOrganizationName("FortniteCrashAnalyzer")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
