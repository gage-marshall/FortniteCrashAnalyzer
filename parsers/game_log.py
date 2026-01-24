"""Parser for FortniteGame.log files."""
import re
from pathlib import Path
from typing import List
from models.crash_data import CrashData


class GameLogParser:
    """Parses FortniteGame.log files."""

    @staticmethod
    def parse(log_path: Path, crash_data: CrashData, num_recent_lines: int = 500) -> None:
        """Parse a FortniteGame.log file and populate CrashData.

        Args:
            log_path: Path to the log file.
            crash_data: CrashData object to populate.
            num_recent_lines: Number of recent lines to store.
        """
        try:
            # Read the log file
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # Get last N lines
            recent_lines = lines[-num_recent_lines:] if len(lines) > num_recent_lines else lines
            crash_data.recent_log_lines = [line.strip() for line in recent_lines]

            # Extract errors and warnings from entire log
            errors = []
            warnings = []

            for line in lines:
                line_lower = line.lower()

                # Check for errors
                if any(keyword in line_lower for keyword in ['logerror:', 'error:', ' fatal ']):
                    errors.append(line.strip())

                # Check for warnings
                elif any(keyword in line_lower for keyword in ['logwarning:', 'warning:']):
                    warnings.append(line.strip())

            # Store unique errors and warnings (limit to avoid excessive data)
            crash_data.log_errors = GameLogParser._deduplicate(errors, max_entries=100)
            crash_data.log_warnings = GameLogParser._deduplicate(warnings, max_entries=100)

            # Extract RHI information
            GameLogParser._extract_rhi_info(lines, crash_data)

        except Exception as e:
            print(f"Error parsing FortniteGame.log: {e}")

    @staticmethod
    def _deduplicate(entries: List[str], max_entries: int = 100) -> List[str]:
        """Remove duplicate entries while preserving order.

        Args:
            entries: List of log entries.
            max_entries: Maximum number of entries to keep.

        Returns:
            Deduplicated list limited to max_entries.
        """
        seen = set()
        unique = []

        for entry in entries:
            if entry not in seen:
                seen.add(entry)
                unique.append(entry)
                if len(unique) >= max_entries:
                    break

        return unique

    @staticmethod
    def _extract_rhi_info(lines: List[str], crash_data: CrashData) -> None:
        """Extract RHI (graphics API) and driver information from log.

        Args:
            lines: All log lines.
            crash_data: CrashData object to populate.
        """
        for line in lines:
            # Extract active RHI (D3D11, D3D12, Vulkan)
            if "Using Preferred RHI:" in line or "GetSelectedDynamicRHIModuleName =" in line:
                match = re.search(r'(?:Using Preferred RHI:|GetSelectedDynamicRHIModuleName =)\s*(\w+)', line)
                if match:
                    rhi = match.group(1)
                    # Normalize RHI names
                    if rhi in ["D3D11", "D3D11RHI"]:
                        crash_data.active_rhi = "DirectX 11"
                    elif rhi in ["D3D12", "D3D12RHI"]:
                        crash_data.active_rhi = "DirectX 12"
                    elif rhi in ["Vulkan", "VulkanRHI"]:
                        crash_data.active_rhi = "Vulkan"
                    elif rhi in ["OpenGL", "OpenGLRHI"]:
                        crash_data.active_rhi = "OpenGL"

            # Extract driver version
            # Pattern: "Driver Version: 580.88" or "D3D10Warp Version:"
            if "Driver Version:" in line and not crash_data.driver_version:
                match = re.search(r'Driver Version:\s*([\d.]+)', line)
                if match:
                    crash_data.driver_version = match.group(1)

    @staticmethod
    def search_log(crash_data: CrashData, search_term: str, case_sensitive: bool = False) -> List[str]:
        """Search for a term in the crash log.

        Args:
            crash_data: CrashData object containing log lines.
            search_term: Term to search for.
            case_sensitive: Whether to perform case-sensitive search.

        Returns:
            List of matching log lines.
        """
        results = []
        search_term_comp = search_term if case_sensitive else search_term.lower()

        for line in crash_data.recent_log_lines:
            line_comp = line if case_sensitive else line.lower()
            if search_term_comp in line_comp:
                results.append(line)

        return results
