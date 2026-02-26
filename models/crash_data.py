"""Data models for Fortnite crash information."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path


@dataclass
class SystemInfo:
    """System hardware and software information."""
    cpu_vendor: str = ""
    cpu_brand: str = ""
    cpu_cores: int = 0
    cpu_threads: int = 0
    gpu_brand: str = ""
    total_ram_gb: int = 0
    os_version: str = ""


@dataclass
class CallStackFrame:
    """Single frame in a call stack."""
    module: str
    address: str
    offset: str


@dataclass
class ThreadInfo:
    """Information about a thread."""
    thread_id: str
    thread_name: str
    is_crashed: bool
    call_stack: List[CallStackFrame] = field(default_factory=list)


@dataclass
class CrashData:
    """Complete crash information."""
    # Metadata
    crash_guid: str
    crash_directory: Path
    crash_time: datetime

    # Crash details
    crash_type: str = ""  # Crash, Assert, Ensure, Stall
    error_message: str = ""
    is_oom: bool = False  # Out of memory
    memory_address: str = ""  # Memory address from crash
    active_rhi: str = ""  # Active RHI (D3D11, D3D12, Vulkan, etc.)
    driver_version: str = ""  # GPU driver version

    # Game info
    engine_version: str = ""
    build_version: str = ""
    game_state: str = ""
    session_duration_seconds: int = 0

    # System info
    system_info: SystemInfo = field(default_factory=SystemInfo)

    # Call stacks
    main_call_stack: List[CallStackFrame] = field(default_factory=list)
    threads: List[ThreadInfo] = field(default_factory=list)

    # Log entries
    log_errors: List[str] = field(default_factory=list)
    log_warnings: List[str] = field(default_factory=list)
    recent_log_lines: List[str] = field(default_factory=list)

    # Raw data
    raw_xml: str = ""

    # Advanced minidump analysis
    exception_code: int = 0  # NTSTATUS code
    exception_name: str = ""  # Friendly exception name
    exception_params: List[int] = field(default_factory=list)  # Exception parameters
    cpu_registers: Dict[str, int] = field(default_factory=dict)  # RIP, RSP, RBP, RAX, etc.
    loaded_modules: List[Dict[str, Any]] = field(default_factory=list)  # Loaded DLLs
    crash_in_gpu_driver: bool = False  # Crash occurred in GPU driver
    stack_corruption_detected: bool = False  # Stack corruption detected
    bad_ram_suspected: bool = False  # Bad RAM patterns detected
    address_space_type: str = ""  # USER_SPACE, KERNEL_SPACE, NON_CANONICAL
    advanced_findings: List[str] = field(default_factory=list)  # All advanced heuristic findings

    def get_friendly_crash_type(self) -> str:
        """Get a user-friendly description of the crash type."""
        crash_types = {
            "Crash": "Game Crash",
            "Assert": "Internal Error (Assert)",
            "Ensure": "Recoverable Error (Ensure)",
            "Stall": "Game Froze/Stalled"
        }
        return crash_types.get(self.crash_type, self.crash_type)

    def get_friendly_error(self) -> str:
        """Get a simplified, user-friendly error description."""
        error = self.error_message.lower()

        if "access_violation" in error or "access violation" in error:
            if "reading address" in error:
                return "The game tried to read from an invalid memory location (Access Violation)"
            elif "writing address" in error:
                return "The game tried to write to an invalid memory location (Access Violation)"
            else:
                return "The game accessed invalid memory (Access Violation)"

        elif "stack overflow" in error:
            return "The game ran out of stack memory (Stack Overflow)"

        elif self.is_oom or "out of memory" in error:
            return "The game ran out of memory (OOM)"

        elif "divide by zero" in error or "division by zero" in error:
            return "The game attempted a division by zero"

        elif "pure virtual" in error:
            return "The game called an unimplemented function (Pure Virtual Function Call)"

        else:
            return self.error_message if self.error_message else "Unknown error"

    def get_session_duration_friendly(self) -> str:
        """Get human-readable session duration."""
        seconds = self.session_duration_seconds

        if seconds < 60:
            return f"{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def analyze_memory_address(self) -> tuple[str, str, str]:
        """Analyze memory address to determine likely crash cause.

        Returns:
            Tuple of (category, diagnosis, likely_cause)
        """
        if not self.memory_address:
            return ("Unknown", "", "")

        try:
            # Parse hex address
            addr_str = self.memory_address.replace("0x", "").replace("0X", "")
            addr = int(addr_str, 16)

            # Null pointer issues (0x00000000 - 0x0000FFFF / 64KB)
            if addr == 0:
                return (
                    "Null Pointer",
                    "Direct null pointer dereference",
                    "The game tried to access a null pointer directly. This is a common programming bug where a pointer was never initialized or was set to null."
                )
            elif 0 < addr < 0x10000:
                return (
                    "Null Pointer + Offset",
                    f"Accessing structure member at offset {hex(addr)} from null pointer",
                    "The game tried to access a member of an object or structure, but the base pointer was null. This typically happens when trying to use an object that was never created or has already been deleted."
                )

            # Debug heap patterns (check all bytes match pattern)
            if addr & 0xFFFFFFFF == 0xCCCCCCCC:
                return (
                    "Uninitialized Stack Memory",
                    "Accessing uninitialized stack variable",
                    "The game tried to use a local variable that was never given a value. This is a programming bug where the developer forgot to initialize a variable before using it."
                )
            elif addr & 0xFFFFFFFF == 0xCDCDCDCD:
                return (
                    "Uninitialized Heap Memory",
                    "Accessing uninitialized heap memory (malloc/new without initialization)",
                    "The game allocated memory but tried to use it before setting any values. This is a programming bug where memory was allocated but not properly initialized."
                )
            elif addr & 0xFFFFFFFF == 0xDDDDDDDD:
                return (
                    "Use-After-Free",
                    "Accessing memory that has already been freed",
                    "The game tried to use memory that was already deleted. This is a serious bug where the program still has a pointer to memory it no longer owns, often causing unpredictable crashes."
                )
            elif addr & 0xFFFFFFFF == 0xFEEEFEEE:
                return (
                    "Windows Heap Freed Memory",
                    "Accessing memory freed by Windows heap manager",
                    "The game tried to use memory that was returned to the operating system. This is similar to use-after-free and indicates the program is accessing memory it no longer owns."
                )
            elif addr & 0xFFFFFFFF == 0xFDFDFDFD:
                return (
                    "Buffer Overflow",
                    "Accessing heap guard bytes (buffer overflow detection)",
                    "The game wrote beyond the end of an allocated memory block. This is a buffer overflow bug where too much data was written to a fixed-size memory area."
                )

            # Wild pointer patterns (all F's or very high addresses)
            if addr == 0xFFFFFFFF or addr == 0xFFFFFFFFFFFFFFFF:
                return (
                    "Uninitialized Pointer",
                    "Wild pointer with uninitialized value",
                    "The game tried to use a pointer that was never set to a valid address. This is a bug where a pointer variable was used before being assigned a proper value."
                )

            # Very high addresses (likely corrupted or uninitialized)
            if addr > 0x7FFFFFFFFFFF:  # Beyond typical user-space on 64-bit
                return (
                    "Invalid Address",
                    "Address in invalid memory range",
                    "The memory address is outside the normal range for application memory. This could indicate memory corruption, an uninitialized pointer, or pointer arithmetic that went wrong."
                )

            # If we get here, it's a generic access violation
            return (
                "Generic Access Violation",
                "Access to invalid memory address",
                "The game tried to access memory at an address it doesn't have permission to use. This could be due to memory corruption, incorrect pointer arithmetic, or other memory management bugs."
            )

        except (ValueError, AttributeError):
            return ("Unknown", "", "")

    def detect_gpu_driver_issue(self) -> tuple[bool, str, str, List[str]]:
        """Detect potential GPU driver issues from logs and crash data.

        Returns:
            Tuple of (is_gpu_issue, gpu_vendor, diagnosis, recommendations)
        """
        is_gpu_issue = False
        diagnosis_parts = []
        recommendations = []

        # Determine GPU vendor from system info
        gpu_brand = self.system_info.gpu_brand.lower()
        if "nvidia" in gpu_brand or "geforce" in gpu_brand or "rtx" in gpu_brand or "gtx" in gpu_brand:
            gpu_vendor = "NVIDIA"
        elif "amd" in gpu_brand or "radeon" in gpu_brand or "rx " in gpu_brand:
            gpu_vendor = "AMD"
        elif "intel" in gpu_brand or "arc" in gpu_brand or "uhd" in gpu_brand or "iris" in gpu_brand:
            gpu_vendor = "Intel"
        else:
            gpu_vendor = "Unknown"

        # Check for GPU-related errors in logs
        gpu_error_patterns = [
            "gpu crashed",
            "d3d device removed",
            "dxgi_error_device_removed",
            "dxgi_error_device_hung",
            "device lost",
            "tdr",
            "timeout detection",
        ]

        rhi_error_patterns = [
            "logd3d11rhi.*error",
            "logd3d12rhi.*error",
            "logrhi.*error",
            "logvulkanrhi.*error",
        ]

        # Search through error logs
        for error_line in self.log_errors:
            error_lower = error_line.lower()

            # Check for GPU crash patterns
            for pattern in gpu_error_patterns:
                if pattern in error_lower:
                    is_gpu_issue = True
                    diagnosis_parts.append(f"GPU error detected in log: {pattern}")
                    break

            # Check for RHI errors
            for pattern in rhi_error_patterns:
                if pattern.replace(".*", "") in error_lower:
                    is_gpu_issue = True
                    diagnosis_parts.append(f"Graphics API (RHI) error detected")
                    break

        # Build diagnosis string
        diagnosis = "; ".join(diagnosis_parts) if diagnosis_parts else ""

        # Add RHI and driver information to diagnosis if available
        if self.active_rhi:
            diagnosis = f"Using {self.active_rhi}. " + diagnosis
        if self.driver_version and gpu_vendor != "Unknown":
            diagnosis = f"{gpu_vendor} Driver {self.driver_version}. " + diagnosis

        # Generate recommendations based on findings
        if is_gpu_issue or self.active_rhi or diagnosis:
            # Vendor-specific recommendations
            if gpu_vendor == "NVIDIA":
                recommendations.append("Update NVIDIA drivers to the latest Game Ready Driver from nvidia.com/drivers")
                if self.active_rhi == "D3D12":
                    recommendations.append("Try switching to DirectX 11 in Fortnite settings (may reduce crashes)")
                    recommendations.append("Check NVIDIA Control Panel for any forced graphics settings")
                if "device removed" in diagnosis.lower() or "tdr" in diagnosis.lower():
                    recommendations.append("Increase TDR timeout in Windows Registry (search: 'TDR Timeout Fix')")
                recommendations.append("Use DDU (Display Driver Uninstaller) for clean driver reinstall")
                recommendations.append("Disable any GPU overclocking")

            elif gpu_vendor == "AMD":
                recommendations.append("Update AMD drivers to latest Adrenalin Edition from amd.com/support")
                if self.active_rhi == "D3D12":
                    recommendations.append("Try switching to DirectX 11 in Fortnite settings")
                recommendations.append("Disable Radeon Anti-Lag and Image Sharpening for Fortnite")
                recommendations.append("Use DDU (Display Driver Uninstaller) for clean driver reinstall")
                recommendations.append("Check for GPU overheating")

            elif gpu_vendor == "Intel":
                recommendations.append("Update Intel graphics drivers from intel.com/content/www/us/en/download-center")
                recommendations.append("Intel integrated graphics may struggle with Fortnite, consider dedicated GPU")
                if self.active_rhi == "D3D12":
                    recommendations.append("Switch to DirectX 11 for better stability on Intel graphics")

            # General recommendations if GPU issue detected
            if is_gpu_issue:
                recommendations.append("Clear shader cache: Delete FortniteGame\\Saved\\ShaderCache folder")
                recommendations.append("Verify game files through Epic Games Launcher")
                recommendations.append("Check GPU temperature and ensure adequate cooling")
                recommendations.append("Close GPU-intensive background applications (overlays, recording software)")

        return (is_gpu_issue, gpu_vendor, diagnosis, recommendations)

    def get_summary(self) -> Dict[str, str]:
        """Get a summary of the crash suitable for display."""
        summary = {
            "Crash Type": self.get_friendly_crash_type(),
            "Error": self.get_friendly_error(),
            "Time": self.crash_time.strftime("%Y-%m-%d %I:%M:%S %p"),
            "Session Duration": self.get_session_duration_friendly(),
            "Game Version": self.build_version,
            "Engine Version": self.engine_version,
            "Game State": self.game_state or "Unknown",
        }
        if self.memory_address:
            summary["Memory Address"] = self.memory_address
        return summary
