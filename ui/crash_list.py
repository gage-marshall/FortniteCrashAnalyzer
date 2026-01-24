"""Crash list widget (left panel)."""
from PyQt6.QtWidgets import QListWidget, QListWidgetItem
from PyQt6.QtCore import pyqtSignal
from typing import List
from models.crash_data import CrashData


class CrashListWidget(QListWidget):
    """Widget displaying list of crashes."""

    crash_selected = pyqtSignal(CrashData)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.crashes = []
        self.itemClicked.connect(self._on_item_clicked)

    def load_crashes(self, crashes: List[CrashData]) -> None:
        """Load crashes into the list.

        Args:
            crashes: List of CrashData objects.
        """
        self.clear()
        self.crashes = crashes

        for crash in crashes:
            item = QListWidgetItem()
            # Format: Time - Error Type
            time_str = crash.crash_time.strftime("%Y-%m-%d %I:%M %p")
            error_type = crash.get_friendly_crash_type()
            item.setText(f"{time_str}\n{error_type}")
            item.setData(1, crash)  # Store crash data with item
            self.addItem(item)

        # Select first item if available
        if self.count() > 0:
            self.setCurrentRow(0)
            self._on_item_clicked(self.item(0))

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Handle item click.

        Args:
            item: Clicked list item.
        """
        crash = item.data(1)
        if crash:
            self.crash_selected.emit(crash)
