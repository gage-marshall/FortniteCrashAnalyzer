"""Detail tabs widget (right panel)."""
from PyQt6.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QTextEdit, QLabel, QScrollArea, QGroupBox, QFormLayout,
    QPushButton, QHBoxLayout, QApplication
)
from PyQt6.QtCore import Qt
from models.crash_data import CrashData


class DetailTabsWidget(QTabWidget):
    """Widget with tabs showing crash details."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_crash = None

        # Create tabs
        self.summary_tab = SummaryTab()
        self.technical_tab = TechnicalTab()
        self.system_tab = SystemTab()
        self.log_tab = LogTab()
        self.epic_report_tab = EpicReportTab()

        self.addTab(self.summary_tab, "Summary")
        self.addTab(self.technical_tab, "Technical Details")
        self.addTab(self.system_tab, "System Info")
        self.addTab(self.log_tab, "Game Log")
        self.addTab(self.epic_report_tab, "Epic Games Report")

    def load_crash(self, crash: CrashData) -> None:
        """Load crash data into tabs.

        Args:
            crash: CrashData object to display.
        """
        self.current_crash = crash
        self.summary_tab.load_crash(crash)
        self.technical_tab.load_crash(crash)
        self.system_tab.load_crash(crash)
        self.log_tab.load_crash(crash)
        self.epic_report_tab.load_crash(crash)


class SummaryTab(QWidget):
    """Summary tab with plain English explanation."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Title
        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(self.title_label)

        # Explanation
        self.explanation_label = QLabel()
        self.explanation_label.setWordWrap(True)
        self.explanation_label.setStyleSheet("font-size: 11pt; padding: 10px;")
        layout.addWidget(self.explanation_label)

        # Key details
        self.details_group = QGroupBox("Key Details")
        self.details_layout = QFormLayout()
        self.details_group.setLayout(self.details_layout)
        layout.addWidget(self.details_group)

        layout.addStretch()

    def load_crash(self, crash: CrashData) -> None:
        """Load crash data.

        Args:
            crash: CrashData object.
        """
        # Set title
        self.title_label.setText(f"Crash Report - {crash.get_friendly_crash_type()}")

        # Generate explanation
        explanation = self._generate_explanation(crash)
        self.explanation_label.setText(explanation)

        # Clear and populate details
        while self.details_layout.count():
            child = self.details_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        summary = crash.get_summary()
        for key, value in summary.items():
            self.details_layout.addRow(f"{key}:", QLabel(value))

    def _generate_explanation(self, crash: CrashData) -> str:
        """Generate plain English explanation.

        Args:
            crash: CrashData object.

        Returns:
            Explanation string.
        """
        error = crash.get_friendly_error()

        explanation = f"<b>What happened:</b><br>{error}<br><br>"

        # Add context based on crash type
        if "Access Violation" in error:
            # Try to get intelligent diagnosis from memory address
            category, diagnosis, likely_cause = crash.analyze_memory_address()

            if diagnosis:
                explanation += (
                    f"<b>Specific Issue Detected:</b><br>"
                    f"<i>{category}: {diagnosis}</i><br><br>"
                    f"<b>What this means:</b><br>"
                    f"{likely_cause}<br><br>"
                )

                # Add specific recommendations based on category
                if category in ["Null Pointer", "Null Pointer + Offset"]:
                    explanation += (
                        "<b>What you can do:</b><br>"
                        "• This is a game programming bug, report it to Epic Games<br>"
                        "• Try to reproduce the crash and note what you were doing<br>"
                        "• Check if a game update is available that may fix this issue<br>"
                        "• Verify your game files through Epic Games Launcher"
                    )
                elif category in ["Use-After-Free", "Windows Heap Freed Memory"]:
                    explanation += (
                        "<b>What you can do:</b><br>"
                        "• This is a serious game bug, report it to Epic Games with details<br>"
                        "• Note what you were doing when it crashed (helps developers fix it)<br>"
                        "• Try closing other programs to free up memory<br>"
                        "• Verify your game files through Epic Games Launcher"
                    )
                elif category in ["Uninitialized Stack Memory", "Uninitialized Heap Memory", "Uninitialized Pointer"]:
                    explanation += (
                        "<b>What you can do:</b><br>"
                        "• This is a game programming bug, report it to Epic Games<br>"
                        "• Try reproducing the crash to help identify the pattern<br>"
                        "• Check if a game update is available<br>"
                        "• Verify your game files through Epic Games Launcher"
                    )
                elif category == "Buffer Overflow":
                    explanation += (
                        "<b>What you can do:</b><br>"
                        "• This is a memory corruption bug, report it to Epic Games immediately<br>"
                        "• Note exactly what you were doing (loading area, using items, etc.)<br>"
                        "• Check if a game update is available<br>"
                        "• Verify your game files through Epic Games Launcher"
                    )
                else:
                    explanation += (
                        "<b>What you can do:</b><br>"
                        "• Verify your game files through Epic Games Launcher<br>"
                        "• Update your graphics drivers<br>"
                        "• Report this crash to Epic Games Support<br>"
                        "• Check if the issue persists after restarting the game"
                    )
            else:
                # Generic access violation without specific diagnosis
                explanation += (
                    "<b>What this means:</b><br>"
                    "The game tried to use a part of your computer's memory that it wasn't "
                    "allowed to access. This is usually caused by a bug in the game code or "
                    "corrupted game files.<br><br>"
                    "<b>What you can do:</b><br>"
                    "• Verify your game files through Epic Games Launcher<br>"
                    "• Update your graphics drivers<br>"
                    "• Check if the issue persists after restarting the game"
                )
        elif crash.is_oom or "out of memory" in error.lower():
            explanation += (
                "<b>What this means:</b><br>"
                "The game ran out of available memory (RAM) on your system. This can happen "
                "with high graphics settings, many programs running in the background, or "
                "memory leaks.<br><br>"
                "<b>What you can do:</b><br>"
                "• Close unnecessary programs before playing<br>"
                "• Lower graphics settings (especially textures)<br>"
                "• Consider upgrading your RAM if this happens frequently"
            )
        elif "Stack Overflow" in error:
            explanation += (
                "<b>What this means:</b><br>"
                "The game used too much stack memory, often due to infinite recursion or "
                "very deep function calls. This is typically a bug in the game code.<br><br>"
                "<b>What you can do:</b><br>"
                "• Report this crash to Epic Games<br>"
                "• Check if a game update is available<br>"
                "• Try reproducing the crash to help developers fix it"
            )
        else:
            explanation += (
                "<b>What you can do:</b><br>"
                "• Verify your game files through Epic Games Launcher<br>"
                "• Update your graphics drivers<br>"
                "• Report this crash to Epic Games Support<br>"
                "• Check the Technical Details tab for more information"
            )

        # Check for GPU/driver issues
        is_gpu_issue, gpu_vendor, gpu_diagnosis, gpu_recommendations = crash.detect_gpu_driver_issue()

        if is_gpu_issue or gpu_diagnosis:
            explanation += "<br><br>"
            explanation += f"<b>GPU/Driver Issue Detected:</b><br>"
            if gpu_diagnosis:
                explanation += f"<i>{gpu_diagnosis}</i><br><br>"
            if gpu_recommendations:
                explanation += "<b>GPU-Specific Recommendations:</b><br>"
                for rec in gpu_recommendations:
                    explanation += f"• {rec}<br>"
        elif crash.active_rhi or crash.system_info.gpu_brand:
            # Show GPU info even if no issues detected
            explanation += "<br><br>"
            explanation += "<b>GPU Information:</b><br>"
            if crash.system_info.gpu_brand:
                explanation += f"GPU: {crash.system_info.gpu_brand}<br>"
            if crash.active_rhi:
                explanation += f"Graphics API: {crash.active_rhi}<br>"
            if crash.driver_version:
                explanation += f"Driver Version: {crash.driver_version}<br>"

        # Display advanced minidump analysis findings
        if crash.advanced_findings:
            explanation += "<br><br>"
            explanation += "<b>Advanced Crash Analysis:</b><br>"
            explanation += "<i style='color: #888;'>From minidump analysis</i><br>"
            for finding in crash.advanced_findings:
                # Color code findings by severity
                if any(word in finding for word in ['CORRUPTION', 'BAD_RAM', 'KERNEL_SPACE']):
                    explanation += f"<span style='color: #ff6b6b;'>⚠ {finding}</span><br>"
                elif 'GPU_DRIVER' in finding:
                    explanation += f"<span style='color: #ffa500;'>⚠ {finding}</span><br>"
                elif 'CONFIRMED' in finding:
                    explanation += f"<span style='color: #4ecdc4;'>✓ {finding}</span><br>"
                else:
                    explanation += f"• {finding}<br>"

        return explanation


class TechnicalTab(QWidget):
    """Technical details tab."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFontFamily("Consolas, Courier New, monospace")
        layout.addWidget(self.text_edit)

    def load_crash(self, crash: CrashData) -> None:
        """Load crash data.

        Args:
            crash: CrashData object.
        """
        html = []
        html.append("<style>")
        html.append(".even { background-color: #1e1e1e; }")
        html.append(".odd { background-color: #2a2a2a; }")
        html.append("body { font-family: 'Consolas', 'Courier New', monospace; }")
        html.append("</style>")

        html.append(f"<div class='odd'><b>Crash GUID:</b> {crash.crash_guid}</div>")
        html.append(f"<div class='even'><b>Crash Type:</b> {crash.crash_type}</div>")
        html.append(f"<div class='odd'><b>Error Message:</b> {crash.error_message}</div>")
        html.append(f"<div class='even'><b>Out of Memory:</b> {'Yes' if crash.is_oom else 'No'}</div>")

        # Show advanced exception info if available
        if crash.exception_code:
            html.append(f"<div class='odd'><b>Exception Code:</b> 0x{crash.exception_code:08X} ({crash.exception_name})</div>")
        html.append("<br>")

        # Show CPU registers if available
        if crash.cpu_registers:
            html.append("<div class='odd'><b>=== CPU Registers (at crash) ===</b></div>")
            reg_count = 0
            for reg_name in ['RIP', 'RSP', 'RBP', 'RAX', 'RBX', 'RCX', 'RDX', 'RSI', 'RDI', 'R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15']:
                if reg_name in crash.cpu_registers:
                    css_class = 'even' if reg_count % 2 == 0 else 'odd'
                    html.append(f"<div class='{css_class}'>{reg_name}: 0x{crash.cpu_registers[reg_name]:016X}</div>")
                    reg_count += 1
            html.append("<br>")

        html.append("<div class='odd'><b>=== Main Thread Call Stack ===</b></div>")
        if crash.main_call_stack:
            for i, frame in enumerate(crash.main_call_stack[:20]):  # Limit to 20 frames
                css_class = 'even' if i % 2 == 0 else 'odd'
                html.append(f"<div class='{css_class}'>{i+1}. {frame.module} {frame.address} + {frame.offset}</div>")
        else:
            html.append("<div class='even'>No call stack available</div>")
        html.append("<br>")

        # Show other threads
        html.append(f"<div class='odd'><b>=== Other Threads ({len(crash.threads)}) ===</b></div>")
        line_count = 0
        for thread in crash.threads[:5]:  # Show first 5 threads
            css_class = 'even' if line_count % 2 == 0 else 'odd'
            html.append(f"<div class='{css_class}'><br><b>Thread:</b> {thread.thread_name} (ID: {thread.thread_id})</div>")
            line_count += 1
            css_class = 'even' if line_count % 2 == 0 else 'odd'
            html.append(f"<div class='{css_class}'><b>Crashed:</b> {thread.is_crashed}</div>")
            line_count += 1
            if thread.call_stack and len(thread.call_stack) > 0:
                css_class = 'even' if line_count % 2 == 0 else 'odd'
                html.append(f"<div class='{css_class}'>Call stack (top 5 frames):</div>")
                line_count += 1
                for frame in thread.call_stack[:5]:
                    css_class = 'even' if line_count % 2 == 0 else 'odd'
                    html.append(f"<div class='{css_class}'>  {frame.module} + {frame.offset}</div>")
                    line_count += 1

        self.text_edit.setHtml("\n".join(html))


class SystemTab(QWidget):
    """System information tab."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

    def load_crash(self, crash: CrashData) -> None:
        """Load crash data.

        Args:
            crash: CrashData object.
        """
        sys_info = crash.system_info

        rows = [
            ("CPU Vendor:", sys_info.cpu_vendor),
            ("CPU:", sys_info.cpu_brand),
            ("CPU Cores:", f"{sys_info.cpu_cores} cores, {sys_info.cpu_threads} threads"),
            ("GPU:", sys_info.gpu_brand),
            ("RAM:", f"{sys_info.total_ram_gb} GB"),
            ("OS:", sys_info.os_version),
            ("", ""),  # Spacer
            ("Engine Version:", crash.engine_version),
            ("Build Version:", crash.build_version),
            ("Game State:", crash.game_state or "Unknown"),
            ("Session Duration:", crash.get_session_duration_friendly()),
        ]

        html = []
        html.append("<style>")
        html.append(".even { background-color: #1e1e1e; padding: 8px; }")
        html.append(".odd { background-color: #2a2a2a; padding: 8px; }")
        html.append(".label { font-weight: bold; display: inline-block; width: 180px; }")
        html.append("</style>")

        for i, (label, value) in enumerate(rows):
            if label:  # Skip spacer rows
                css_class = 'even' if i % 2 == 0 else 'odd'
                html.append(f"<div class='{css_class}'><span class='label'>{label}</span> {value}</div>")
            else:
                html.append("<br>")

        self.text_edit.setHtml("\n".join(html))


class LogTab(QWidget):
    """Game log tab."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Errors section
        errors_label = QLabel("Errors Found:")
        errors_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(errors_label)

        self.errors_text = QTextEdit()
        self.errors_text.setReadOnly(True)
        self.errors_text.setFixedHeight(150)
        self.errors_text.setFontFamily("Consolas, Courier New, monospace")
        layout.addWidget(self.errors_text)

        # Recent log section
        log_label = QLabel("Recent Log Entries (last 500 lines):")
        log_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFontFamily("Consolas, Courier New, monospace")
        layout.addWidget(self.log_text)

    def load_crash(self, crash: CrashData) -> None:
        """Load crash data.

        Args:
            crash: CrashData object.
        """
        # Load errors with alternating backgrounds
        if crash.log_errors:
            html = []
            html.append("<style>")
            html.append(".even { background-color: #1e1e1e; font-family: 'Consolas', 'Courier New', monospace; }")
            html.append(".odd { background-color: #2a2a2a; font-family: 'Consolas', 'Courier New', monospace; }")
            html.append("</style>")
            for i, error in enumerate(crash.log_errors):
                css_class = 'even' if i % 2 == 0 else 'odd'
                html.append(f"<div class='{css_class}'>{error}</div>")
            self.errors_text.setHtml("\n".join(html))
        else:
            self.errors_text.setPlainText("No errors found in log")

        # Load recent log entries with alternating backgrounds
        if crash.recent_log_lines:
            html = []
            html.append("<style>")
            html.append(".even { background-color: #1e1e1e; font-family: 'Consolas', 'Courier New', monospace; }")
            html.append(".odd { background-color: #2a2a2a; font-family: 'Consolas', 'Courier New', monospace; }")
            html.append("</style>")
            for i, line in enumerate(crash.recent_log_lines):
                css_class = 'even' if i % 2 == 0 else 'odd'
                html.append(f"<div class='{css_class}'>{line}</div>")
            self.log_text.setHtml("\n".join(html))
        else:
            self.log_text.setPlainText("No log entries available")


class EpicReportTab(QWidget):
    """Epic Games crash report tab."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Copy button and link at top
        button_layout = QHBoxLayout()
        self.copy_button = QPushButton("Copy Report to Clipboard")
        self.copy_button.clicked.connect(self._copy_to_clipboard)
        button_layout.addWidget(self.copy_button)

        # Add clickable link to Epic Games support
        link_label = QLabel('<a href="https://www.epicgames.com/help/en-US/fortnite-battle-royale-c-202300000001636">Contact Epic Games</a>')
        link_label.setOpenExternalLinks(True)
        link_label.setStyleSheet("padding-left: 10px;")
        button_layout.addWidget(link_label)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Report text area
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setFontFamily("Consolas, Courier New, monospace")
        self.report_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.report_text)

        self.current_crash = None

    def load_crash(self, crash: CrashData) -> None:
        """Load crash data and generate report.

        Args:
            crash: CrashData object.
        """
        self.current_crash = crash
        report = self._generate_report(crash)
        self.report_text.setPlainText(report)

    def _generate_report(self, crash: CrashData) -> str:
        """Generate formatted report for Epic Games.

        Args:
            crash: CrashData object.

        Returns:
            Formatted report string.
        """
        lines = []

        # Header
        lines.append("=" * 60)
        lines.append("FORTNITE CRASH REPORT")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Crash GUID: {crash.crash_guid}")
        lines.append(f"Date/Time: {crash.crash_time.strftime('%Y-%m-%d %I:%M:%S %p')}")
        lines.append(f"Session Duration: {crash.get_session_duration_friendly()}")
        lines.append("")

        # Crash Summary
        lines.append("=" * 60)
        lines.append("CRASH SUMMARY")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Type: {crash.get_friendly_crash_type()}")
        lines.append(f"Error: {crash.error_message}")

        if crash.memory_address:
            lines.append(f"Memory Address: {crash.memory_address}")
            category, diagnosis, likely_cause = crash.analyze_memory_address()
            if diagnosis:
                lines.append(f"Likely Cause: {category} - {diagnosis}")

        if crash.is_oom:
            lines.append("Out of Memory: YES")
        lines.append("")

        # System Information
        lines.append("=" * 60)
        lines.append("SYSTEM INFORMATION")
        lines.append("=" * 60)
        lines.append("")
        sys_info = crash.system_info
        lines.append(f"CPU: {sys_info.cpu_brand} ({sys_info.cpu_cores} cores, {sys_info.cpu_threads} threads)")
        lines.append(f"GPU: {sys_info.gpu_brand}")
        if crash.driver_version:
            lines.append(f"GPU Driver: {crash.driver_version}")
        lines.append(f"RAM: {sys_info.total_ram_gb} GB")
        lines.append(f"OS: {sys_info.os_version}")
        if crash.active_rhi:
            lines.append(f"Graphics API: {crash.active_rhi}")
        lines.append("")

        # Game Information
        lines.append("=" * 60)
        lines.append("GAME INFORMATION")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Engine Version: {crash.engine_version}")
        lines.append(f"Build Version: {crash.build_version}")
        if crash.game_state:
            lines.append(f"Game State: {crash.game_state}")
        lines.append("")

        # Advanced Crash Analysis (if available)
        if crash.advanced_findings or crash.cpu_registers or crash.exception_code:
            lines.append("=" * 60)
            lines.append("ADVANCED CRASH ANALYSIS")
            lines.append("=" * 60)
            lines.append("")

            if crash.exception_code:
                lines.append(f"Exception Code: 0x{crash.exception_code:08X} ({crash.exception_name})")
                if crash.exception_params:
                    lines.append(f"Exception Parameters: {[hex(p) for p in crash.exception_params]}")
                lines.append("")

            if crash.cpu_registers:
                lines.append("CPU Registers (at time of crash):")
                for reg_name in ['RIP', 'RSP', 'RBP', 'RAX', 'RBX', 'RCX', 'RDX', 'RSI', 'RDI']:
                    if reg_name in crash.cpu_registers:
                        lines.append(f"  {reg_name}: 0x{crash.cpu_registers[reg_name]:016X}")
                lines.append("")

            if crash.advanced_findings:
                lines.append("Automated Diagnosis:")
                for finding in crash.advanced_findings:
                    lines.append(f"  - {finding}")
                lines.append("")

            if crash.address_space_type:
                lines.append(f"Address Space: {crash.address_space_type}")
            if crash.crash_in_gpu_driver:
                lines.append("GPU Driver Involvement: YES")
            if crash.stack_corruption_detected:
                lines.append("Stack Corruption: DETECTED")
            if crash.bad_ram_suspected:
                lines.append("Bad RAM: SUSPECTED")
            lines.append("")

        # Main Thread Call Stack
        lines.append("=" * 60)
        lines.append("MAIN THREAD CALL STACK")
        lines.append("=" * 60)
        lines.append("")
        if crash.main_call_stack:
            for i, frame in enumerate(crash.main_call_stack, 1):
                lines.append(f"{i}. {frame.module} {frame.address} + {frame.offset}")
        else:
            # Try to find GameThread from threads
            game_thread = None
            for thread in crash.threads:
                if thread.thread_name == "GameThread" and thread.is_crashed:
                    game_thread = thread
                    break

            if game_thread and game_thread.call_stack:
                for i, frame in enumerate(game_thread.call_stack, 1):
                    lines.append(f"{i}. {frame.module} {frame.address} + {frame.offset}")
            else:
                lines.append("No call stack available")
        lines.append("")

        # Other Crashed Threads
        other_crashed = [t for t in crash.threads if t.is_crashed and t.thread_name != "GameThread"]
        if other_crashed:
            lines.append("=" * 60)
            lines.append("OTHER CRASHED THREADS")
            lines.append("=" * 60)
            lines.append("")
            for thread in other_crashed:
                lines.append(f"Thread: {thread.thread_name} (ID: {thread.thread_id})")
                lines.append("-" * 40)
                if thread.call_stack:
                    for i, frame in enumerate(thread.call_stack[:20], 1):  # Limit to 20 frames
                        lines.append(f"{i}. {frame.module} {frame.address} + {frame.offset}")
                else:
                    lines.append("No call stack available")
                lines.append("")

        # Log Errors
        lines.append("=" * 60)
        lines.append("LOG ERRORS")
        lines.append("=" * 60)
        lines.append("")
        if crash.log_errors:
            for error in crash.log_errors[:50]:  # Limit to 50 errors
                lines.append(error)
        else:
            lines.append("No errors found in log")
        lines.append("")

        # Log Tail
        lines.append("=" * 60)
        lines.append("LOG TAIL (Last 20 lines)")
        lines.append("=" * 60)
        lines.append("")
        if crash.recent_log_lines:
            tail_lines = crash.recent_log_lines[-20:]
            for line in tail_lines:
                lines.append(line)
        else:
            lines.append("No log entries available")
        lines.append("")

        lines.append("=" * 60)
        lines.append("END OF REPORT")
        lines.append("=" * 60)

        return "\n".join(lines)

    def _copy_to_clipboard(self) -> None:
        """Copy report to clipboard."""
        if self.current_crash:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.report_text.toPlainText())
            self.copy_button.setText("✓ Copied to Clipboard!")
            # Reset button text after 2 seconds
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self.copy_button.setText("Copy Report to Clipboard"))
