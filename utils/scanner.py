"""Scanner for Fortnite crash directories."""
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime


class CrashScanner:
    """Scans for and manages Fortnite crash dump directories."""

    def __init__(self, crash_base_path: Optional[Path] = None):
        """Initialize the scanner.

        Args:
            crash_base_path: Base path to crash directories. If None, uses default.
        """
        if crash_base_path is None:
            # Default: %LOCALAPPDATA%\FortniteGame\Saved\Crashes
            localappdata = os.environ.get('LOCALAPPDATA', '')
            self.crash_base_path = Path(localappdata) / 'FortniteGame' / 'Saved' / 'Crashes'
        else:
            self.crash_base_path = crash_base_path

    def scan_crashes(self) -> List[Path]:
        """Scan for all crash directories.

        Returns:
            List of Path objects for crash directories, sorted by modification time (newest first).
        """
        if not self.crash_base_path.exists():
            return []

        crash_dirs = []
        for item in self.crash_base_path.iterdir():
            if item.is_dir() and item.name.startswith('UECC-Windows-'):
                crash_dirs.append(item)

        # Sort by modification time, newest first
        crash_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return crash_dirs

    def get_crash_time(self, crash_dir: Path) -> datetime:
        """Get the timestamp of a crash directory.

        Args:
            crash_dir: Path to crash directory.

        Returns:
            Datetime object representing the crash time.
        """
        return datetime.fromtimestamp(crash_dir.stat().st_mtime)

    def get_crash_guid(self, crash_dir: Path) -> str:
        """Extract the crash GUID from the directory name.

        Args:
            crash_dir: Path to crash directory.

        Returns:
            The crash GUID string.
        """
        # Format: UECC-Windows-{GUID}_{NUMBER}
        return crash_dir.name

    def validate_crash_directory(self, crash_dir: Path) -> bool:
        """Check if a crash directory contains expected files.

        Args:
            crash_dir: Path to crash directory.

        Returns:
            True if directory contains at least CrashContext.runtime-xml
        """
        if not crash_dir.is_dir():
            return False

        xml_file = crash_dir / 'CrashContext.runtime-xml'
        return xml_file.exists()

    def get_crash_files(self, crash_dir: Path) -> dict:
        """Get paths to all crash-related files in a directory.

        Args:
            crash_dir: Path to crash directory.

        Returns:
            Dictionary with file types as keys and Path objects as values.
        """
        files = {
            'xml': crash_dir / 'CrashContext.runtime-xml',
            'log': crash_dir / 'FortniteGame.log',
            'minidump': crash_dir / 'UEMinidump.dmp',
        }

        # Filter to only existing files
        return {k: v for k, v in files.items() if v.exists()}
