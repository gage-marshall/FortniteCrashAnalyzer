"""Parser for CrashContext.runtime-xml files."""
import xml.etree.ElementTree as ET
import re
from pathlib import Path
from typing import Optional
from models.crash_data import CrashData, SystemInfo, ThreadInfo, CallStackFrame


class CrashContextParser:
    """Parses CrashContext.runtime-xml files."""

    @staticmethod
    def parse_call_stack(call_stack_text: str) -> list[CallStackFrame]:
        """Parse call stack text into CallStackFrame objects.

        Args:
            call_stack_text: Raw call stack text from XML.

        Returns:
            List of CallStackFrame objects.
        """
        frames = []
        lines = call_stack_text.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Format: "Module 0xBASE + OFFSET"
            parts = line.split()
            if len(parts) >= 4:
                module = parts[0]
                address = parts[1] if len(parts) > 1 else ""
                offset = parts[3] if len(parts) > 3 else ""
                frames.append(CallStackFrame(module=module, address=address, offset=offset))

        return frames

    @staticmethod
    def parse(xml_path: Path, crash_data: CrashData) -> None:
        """Parse a CrashContext.runtime-xml file and populate CrashData.

        Args:
            xml_path: Path to the XML file.
            crash_data: CrashData object to populate.
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Store raw XML
            crash_data.raw_xml = ET.tostring(root, encoding='unicode')

            # Parse RuntimeProperties
            runtime_props = root.find('RuntimeProperties')
            if runtime_props is not None:
                # Basic crash info
                crash_data.crash_type = CrashContextParser._get_text(runtime_props, 'CrashType')
                crash_data.error_message = CrashContextParser._get_text(runtime_props, 'ErrorMessage')

                # Extract memory address from error message
                if crash_data.error_message:
                    address_match = re.search(r'(?:address |at )(0x[0-9a-fA-F]+)', crash_data.error_message)
                    if address_match:
                        crash_data.memory_address = address_match.group(1)

                # Game info
                crash_data.engine_version = CrashContextParser._get_text(runtime_props, 'EngineVersion')
                crash_data.build_version = CrashContextParser._get_text(runtime_props, 'BuildVersion')
                crash_data.game_state = CrashContextParser._get_text(runtime_props, 'GameStateName')

                # Session duration
                duration_str = CrashContextParser._get_text(runtime_props, 'SecondsSinceStart')
                crash_data.session_duration_seconds = int(duration_str) if duration_str else 0

                # System info
                sys_info = SystemInfo()
                sys_info.cpu_vendor = CrashContextParser._get_text(runtime_props, 'Misc.CPUVendor')
                sys_info.cpu_brand = CrashContextParser._get_text(runtime_props, 'Misc.CPUBrand')

                cores_str = CrashContextParser._get_text(runtime_props, 'Misc.NumberOfCores')
                sys_info.cpu_cores = int(cores_str) if cores_str else 0

                threads_str = CrashContextParser._get_text(runtime_props, 'Misc.NumberOfCoresIncludingHyperthreads')
                sys_info.cpu_threads = int(threads_str) if threads_str else 0

                sys_info.gpu_brand = CrashContextParser._get_text(runtime_props, 'Misc.PrimaryGPUBrand')

                ram_str = CrashContextParser._get_text(runtime_props, 'MemoryStats.TotalPhysicalGB')
                sys_info.total_ram_gb = int(ram_str) if ram_str else 0

                sys_info.os_version = CrashContextParser._get_text(runtime_props, 'Misc.OSVersionMajor')

                crash_data.system_info = sys_info

                # OOM detection
                oom_str = CrashContextParser._get_text(runtime_props, 'MemoryStats.bIsOOM')
                crash_data.is_oom = oom_str == '1'

                # Main call stack
                pcall_stack = CrashContextParser._get_text(runtime_props, 'PCallStack')
                if pcall_stack:
                    crash_data.main_call_stack = CrashContextParser.parse_call_stack(pcall_stack)

                # Threads
                threads_elem = runtime_props.find('Threads')
                if threads_elem is not None:
                    for thread_elem in threads_elem.findall('Thread'):
                        thread_info = ThreadInfo(
                            thread_id=CrashContextParser._get_text(thread_elem, 'ThreadID'),
                            thread_name=CrashContextParser._get_text(thread_elem, 'ThreadName'),
                            is_crashed=CrashContextParser._get_text(thread_elem, 'IsCrashed') == 'true'
                        )

                        call_stack_text = CrashContextParser._get_text(thread_elem, 'CallStack')
                        if call_stack_text:
                            thread_info.call_stack = CrashContextParser.parse_call_stack(call_stack_text)

                        crash_data.threads.append(thread_info)

        except Exception as e:
            print(f"Error parsing CrashContext.runtime-xml: {e}")

    @staticmethod
    def _get_text(element: ET.Element, tag: str) -> str:
        """Get text content of a child element.

        Args:
            element: Parent element.
            tag: Tag name of child element.

        Returns:
            Text content or empty string if not found.
        """
        child = element.find(tag)
        return child.text if child is not None and child.text else ""
