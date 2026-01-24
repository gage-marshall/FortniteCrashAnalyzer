"""Main application window."""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QSplitter,
    QLabel, QMessageBox, QProgressDialog
)
from PyQt6.QtCore import Qt
from pathlib import Path
from typing import List

from models.crash_data import CrashData
from utils.scanner import CrashScanner
from parsers.crash_context import CrashContextParser
from parsers.game_log import GameLogParser
from ui.crash_list import CrashListWidget
from ui.detail_tabs import DetailTabsWidget


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fortnite Crash Analyzer")
        self.setGeometry(100, 100, 1200, 800)

        self.crashes: List[CrashData] = []
        self.scanner = CrashScanner()

        self._setup_ui()
        self._load_crashes()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top bar with buttons
        top_bar = QWidget()
        top_bar.setMaximumHeight(35)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(5, 2, 5, 2)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._load_crashes)
        top_layout.addWidget(self.refresh_button)

        self.crash_count_label = QLabel("No crashes found")
        top_layout.addWidget(self.crash_count_label)
        top_layout.addStretch()

        main_layout.addWidget(top_bar)

        # Splitter with crash list and details
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Crash list
        self.crash_list = CrashListWidget()
        self.crash_list.crash_selected.connect(self._on_crash_selected)
        splitter.addWidget(self.crash_list)

        # Right panel: Details
        self.detail_tabs = DetailTabsWidget()
        splitter.addWidget(self.detail_tabs)

        # Set initial splitter sizes (30% list, 70% details)
        splitter.setSizes([300, 700])

        main_layout.addWidget(splitter)

    def _load_crashes(self) -> None:
        """Load all crashes from the crash directory."""
        try:
            # Show progress dialog
            progress = QProgressDialog("Scanning for crashes...", "Cancel", 0, 0, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()

            # Scan for crash directories
            crash_dirs = self.scanner.scan_crashes()

            if not crash_dirs:
                self.crash_count_label.setText("No crashes found")
                progress.close()
                QMessageBox.information(
                    self,
                    "No Crashes Found",
                    f"No crash dumps found in:\n{self.scanner.crash_base_path}\n\n"
                    "Crash dumps are typically stored after Fortnite crashes."
                )
                return

            progress.setMaximum(len(crash_dirs))
            progress.setLabelText(f"Loading {len(crash_dirs)} crashes...")

            # Parse each crash
            self.crashes = []
            for i, crash_dir in enumerate(crash_dirs):
                if progress.wasCanceled():
                    break

                progress.setValue(i)
                progress.setLabelText(f"Loading crash {i+1} of {len(crash_dirs)}...")

                crash_data = self._parse_crash(crash_dir)
                if crash_data:
                    self.crashes.append(crash_data)

            progress.close()

            # Update UI
            self.crash_count_label.setText(f"Found {len(self.crashes)} crashes")
            self.crash_list.load_crashes(self.crashes)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load crashes:\n{str(e)}")

    def _parse_crash(self, crash_dir: Path) -> CrashData | None:
        """Parse a single crash directory.

        Args:
            crash_dir: Path to crash directory.

        Returns:
            CrashData object or None if parsing failed.
        """
        try:
            # Create CrashData object
            crash_data = CrashData(
                crash_guid=self.scanner.get_crash_guid(crash_dir),
                crash_directory=crash_dir,
                crash_time=self.scanner.get_crash_time(crash_dir)
            )

            # Get crash files
            files = self.scanner.get_crash_files(crash_dir)

            # Parse XML if available
            if 'xml' in files:
                CrashContextParser.parse(files['xml'], crash_data)

            # Parse log if available
            if 'log' in files:
                GameLogParser.parse(files['log'], crash_data)

            return crash_data

        except Exception as e:
            print(f"Error parsing crash {crash_dir.name}: {e}")
            return None

    def _on_crash_selected(self, crash: CrashData) -> None:
        """Handle crash selection.

        Args:
            crash: Selected CrashData object.
        """
        self.detail_tabs.load_crash(crash)
