"""Parser for Windows Minidump (.dmp) files."""
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
from models.crash_data import CrashData

# Suppress PEB parsing errors from minidump library (expected for minimal dumps)
logging.getLogger('root').setLevel(logging.CRITICAL)

try:
    from minidump.minidumpfile import MinidumpFile
    MINIDUMP_AVAILABLE = True
except ImportError:
    MINIDUMP_AVAILABLE = False
    print("Warning: minidump library not installed. Advanced crash analysis disabled.")
    print("Install with: pip install minidump")


# NTSTATUS Exception Codes
NTSTATUS_CODES = {
    0xC0000005: "STATUS_ACCESS_VIOLATION",
    0xC0000409: "STATUS_STACK_BUFFER_OVERRUN",
    0xC000001D: "STATUS_ILLEGAL_INSTRUCTION",
    0xC0000094: "STATUS_INTEGER_DIVIDE_BY_ZERO",
    0xC000008C: "STATUS_ARRAY_BOUNDS_EXCEEDED",
    0xC000008D: "STATUS_FLOAT_DENORMAL_OPERAND",
    0xC000008E: "STATUS_FLOAT_DIVIDE_BY_ZERO",
    0xC0000090: "STATUS_FLOAT_INVALID_OPERATION",
    0xC0000091: "STATUS_FLOAT_OVERFLOW",
    0xC0000092: "STATUS_FLOAT_STACK_CHECK",
    0xC0000093: "STATUS_FLOAT_UNDERFLOW",
    0xC0000095: "STATUS_INTEGER_OVERFLOW",
    0xC0000096: "STATUS_PRIVILEGED_INSTRUCTION",
    0xC00000FD: "STATUS_STACK_OVERFLOW",
    0xC0000017: "STATUS_NO_MEMORY",
}


class MinidumpParser:
    """Parses Windows Minidump files for advanced crash analysis."""

    @staticmethod
    def parse(minidump_path: Path, crash_data: CrashData) -> None:
        """Parse minidump file and populate CrashData with advanced information.

        Args:
            minidump_path: Path to the .dmp file.
            crash_data: CrashData object to populate.
        """
        if not MINIDUMP_AVAILABLE:
            return

        if not minidump_path.exists():
            return

        try:
            # Parse minidump file (PEB parsing errors are expected for minimal dumps)
            mf = MinidumpFile.parse(str(minidump_path))

            # DEBUG: Inspect structure (remove after debugging)
            # print(f"\n=== Minidump Structure for {minidump_path.name} ===")
            # print(f"Exception type: {type(mf.exception)}")
            # print(f"Exception attributes: {dir(mf.exception) if mf.exception else 'None'}")
            # print(f"Threads type: {type(mf.threads)}")
            # print(f"Threads_ex type: {type(mf.threads_ex)}")
            # print(f"Modules type: {type(mf.modules)}")

            # Extract exception information
            if mf.exception:
                MinidumpParser._parse_exception(mf.exception, crash_data)

            # Extract CPU registers from crashed thread
            # Try threads_ex first, fall back to threads
            if mf.threads_ex:
                MinidumpParser._parse_registers_ex(mf.threads_ex, mf.exception, crash_data)
            elif mf.threads:
                MinidumpParser._parse_registers(mf.threads, mf.exception, crash_data)

            # Extract loaded modules
            if mf.modules:
                MinidumpParser._parse_modules(mf.modules, crash_data)

            # Run advanced heuristics
            MinidumpParser._run_advanced_heuristics(crash_data)

        except Exception as e:
            # Ignore PEB parsing errors, expected for minimal dumps
            error_str = str(e)
            if "PEB parsing error" not in error_str and "not in process memory space" not in error_str:
                print(f"Error parsing minidump {minidump_path.name}: {e}")

    @staticmethod
    def _parse_exception(exception_stream, crash_data: CrashData) -> None:
        """Parse exception information from minidump.

        Args:
            exception_stream: Exception stream from minidump.
            crash_data: CrashData object to populate.
        """
        try:
            # ExceptionList object, need to access the actual exception
            exc_record = None

            # Try different attribute names
            if hasattr(exception_stream, 'ExceptionRecord'):
                exc_record = exception_stream.ExceptionRecord
            elif hasattr(exception_stream, 'exception_record'):
                exc_record = exception_stream.exception_record
            elif hasattr(exception_stream, 'ExceptionStream'):
                exc_record = exception_stream.ExceptionStream.ExceptionRecord

            if exc_record:
                crash_data.exception_code = exc_record.ExceptionCode

                # Extract exception parameters
                if hasattr(exc_record, 'ExceptionInformation'):
                    crash_data.exception_params = list(exc_record.ExceptionInformation)
                elif hasattr(exc_record, 'exception_information'):
                    crash_data.exception_params = list(exc_record.exception_information)

                # Get friendly exception name
                crash_data.exception_name = NTSTATUS_CODES.get(
                    crash_data.exception_code,
                    f"UNKNOWN_0x{crash_data.exception_code:08X}"
                )

        except AttributeError as e:
            # Silent, ExceptionList might not have ExceptionRecord for some dumps
            pass
        except Exception as e:
            print(f"Error parsing exception: {e}")

    @staticmethod
    def _parse_registers(threads_stream, exception_stream, crash_data: CrashData) -> None:
        """Parse CPU registers from crashed thread (MinidumpThreadList).

        Args:
            threads_stream: MinidumpThreadList from minidump.
            exception_stream: Exception stream to find crashed thread ID.
            crash_data: CrashData object to populate.
        """
        try:
            # Get crashed thread ID from exception if available
            crashed_thread_id = None
            if exception_stream and hasattr(exception_stream, 'ThreadId'):
                crashed_thread_id = exception_stream.ThreadId

            # Find the crashed thread
            crashed_thread = None
            if hasattr(threads_stream, 'threads'):
                for thread in threads_stream.threads:
                    if crashed_thread_id and hasattr(thread, 'ThreadId'):
                        if thread.ThreadId == crashed_thread_id:
                            crashed_thread = thread
                            break
                    elif crashed_thread is None:
                        # Default to first thread if no ID match
                        crashed_thread = thread

            if crashed_thread:
                MinidumpParser._extract_registers_from_thread(crashed_thread, crash_data)

        except Exception as e:
            print(f"Error parsing registers from threads: {e}")

    @staticmethod
    def _parse_registers_ex(threads_ex_stream, exception_stream, crash_data: CrashData) -> None:
        """Parse CPU registers from crashed thread (MinidumpThreadExList).

        Args:
            threads_ex_stream: MinidumpThreadExList from minidump.
            exception_stream: Exception stream to find crashed thread ID.
            crash_data: CrashData object to populate.
        """
        try:
            # Get crashed thread ID from exception if available
            crashed_thread_id = None
            if exception_stream and hasattr(exception_stream, 'ThreadId'):
                crashed_thread_id = exception_stream.ThreadId

            # Find the crashed thread
            crashed_thread = None
            if hasattr(threads_ex_stream, 'Threads'):
                for thread in threads_ex_stream.Threads:
                    if crashed_thread_id and hasattr(thread, 'ThreadId'):
                        if thread.ThreadId == crashed_thread_id:
                            crashed_thread = thread
                            break
                    elif crashed_thread is None:
                        # Default to first thread if no ID match
                        crashed_thread = thread

            if crashed_thread:
                MinidumpParser._extract_registers_from_thread(crashed_thread, crash_data)

        except Exception as e:
            print(f"Error parsing registers from threads_ex: {e}")

    @staticmethod
    def _extract_registers_from_thread(thread, crash_data: CrashData) -> None:
        """Extract CPU registers from a thread object.

        Args:
            thread: Thread object from minidump.
            crash_data: CrashData object to populate.
        """
        try:
            ctx = None
            if hasattr(thread, 'ContextObject') and thread.ContextObject is not None:
                ctx = thread.ContextObject

            if ctx:
                # Extract x64 registers - direct attribute access
                # CONTEXT structure has these attributes from Windows API
                crash_data.cpu_registers = {
                    'RIP': ctx.Rip,  # Instruction Pointer
                    'RSP': ctx.Rsp,  # Stack Pointer
                    'RBP': ctx.Rbp,  # Base Pointer
                    'RAX': ctx.Rax,  # Accumulator
                    'RBX': ctx.Rbx,  # Base
                    'RCX': ctx.Rcx,  # Counter
                    'RDX': ctx.Rdx,  # Data
                    'RSI': ctx.Rsi,  # Source Index
                    'RDI': ctx.Rdi,  # Destination Index
                    'R8':  ctx.R8,   # Extended registers
                    'R9':  ctx.R9,
                    'R10': ctx.R10,
                    'R11': ctx.R11,
                    'R12': ctx.R12,
                    'R13': ctx.R13,
                    'R14': ctx.R14,
                    'R15': ctx.R15,
                }

        except AttributeError:
            # ContextObject might not exist for some threads or minimal dumps
            pass
        except Exception as e:
            print(f"Error extracting registers from thread: {e}")

    @staticmethod
    def _parse_modules(modules_stream, crash_data: CrashData) -> None:
        """Parse loaded modules from minidump.

        Args:
            modules_stream: Modules stream from minidump.
            crash_data: CrashData object to populate.
        """
        try:
            crash_data.loaded_modules = []

            # Get module list
            module_list = None
            if hasattr(modules_stream, 'modules'):
                module_list = modules_stream.modules
            elif hasattr(modules_stream, 'Modules'):
                module_list = modules_stream.Modules

            if module_list:
                for module in module_list:
                    # Try different attribute names
                    name = getattr(module, 'name', getattr(module, 'Name', getattr(module, 'module_name', '')))
                    base_addr = getattr(module, 'baseaddress', getattr(module, 'BaseAddress', getattr(module, 'base_address', 0)))
                    size = getattr(module, 'size', getattr(module, 'Size', getattr(module, 'module_size', 0)))

                    if name:  # Only add if we got a name
                        mod_info = {
                            'name': name,
                            'base_address': base_addr,
                            'size': size,
                        }
                        crash_data.loaded_modules.append(mod_info)

        except Exception as e:
            print(f"Error parsing modules: {e}")

    @staticmethod
    def _run_advanced_heuristics(crash_data: CrashData) -> None:
        """Run all advanced heuristics on crash data.

        Args:
            crash_data: CrashData object to analyze.
        """
        findings = []

        # Null pointer + offset verification
        result = MinidumpParser._verify_null_pointer_offset(crash_data)
        if result:
            findings.append(result)

        # Exception analysis
        result = MinidumpParser._analyze_exception(crash_data)
        if result:
            findings.append(result)

        # GPU driver detection
        result = MinidumpParser._detect_gpu_driver_crash(crash_data)
        if result:
            findings.append(result)
            crash_data.crash_in_gpu_driver = True

        # Address space detection
        result = MinidumpParser._detect_address_space(crash_data)
        if result:
            findings.append(result)
            crash_data.address_space_type = result.split(':')[0]

        # Stack corruption detection
        result = MinidumpParser._detect_stack_corruption(crash_data)
        if result:
            findings.append(result)
            crash_data.stack_corruption_detected = True

        # Bad RAM detection
        result = MinidumpParser._detect_bad_ram(crash_data)
        if result:
            findings.append(result)
            crash_data.bad_ram_suspected = True

        # Store all findings
        crash_data.advanced_findings = findings

    @staticmethod
    def _verify_null_pointer_offset(crash_data: CrashData) -> Optional[str]:
        """Verify null pointer + offset theory using registers.

        Args:
            crash_data: CrashData object.

        Returns:
            Finding string or None.
        """
        if not crash_data.memory_address or not crash_data.cpu_registers:
            return None

        try:
            # Parse crash address
            addr_str = crash_data.memory_address.replace("0x", "").replace("0X", "")
            crash_addr = int(addr_str, 16)

            # Check if in near-null range
            if 0 < crash_addr < 0x10000:
                # Check all general-purpose registers for NULL
                null_regs = []
                for reg_name in ['RAX', 'RBX', 'RCX', 'RDX', 'RSI', 'RDI', 'R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15']:
                    if reg_name in crash_data.cpu_registers and crash_data.cpu_registers[reg_name] == 0:
                        null_regs.append(reg_name)

                if null_regs:
                    return f"NULL_POINTER_CONFIRMED: Register(s) {', '.join(null_regs)} contain NULL (0x0), crash at offset {crash_data.memory_address} confirms struct member access"

        except Exception:
            pass

        return None

    @staticmethod
    def _analyze_exception(crash_data: CrashData) -> Optional[str]:
        """Analyze exception code and parameters.

        Args:
            crash_data: CrashData object.

        Returns:
            Finding string or None.
        """
        if not crash_data.exception_code:
            return None

        analysis = f"EXCEPTION: {crash_data.exception_name} (0x{crash_data.exception_code:08X})"

        if crash_data.exception_code == 0xC0000005:  # ACCESS_VIOLATION
            if len(crash_data.exception_params) >= 2:
                access_type = crash_data.exception_params[0]
                access_addr = crash_data.exception_params[1]

                type_str = {0: "READ", 1: "WRITE", 8: "EXECUTE"}.get(access_type, "UNKNOWN")
                analysis += f" - {type_str} at 0x{access_addr:016X}"

        elif crash_data.exception_code == 0xC0000409:  # STACK_BUFFER_OVERRUN
            analysis += " - Security check failure (buffer overrun detected)"

        elif crash_data.exception_code == 0xC00000FD:  # STACK_OVERFLOW
            analysis += " - Stack overflow (infinite recursion or excessive stack usage)"

        return analysis

    @staticmethod
    def _detect_gpu_driver_crash(crash_data: CrashData) -> Optional[str]:
        """Detect if crash occurred inside GPU driver module.

        Args:
            crash_data: CrashData object.

        Returns:
            Finding string or None.
        """
        if not crash_data.cpu_registers or not crash_data.loaded_modules:
            return None

        rip = crash_data.cpu_registers.get('RIP', 0)
        if rip == 0:
            return None

        # GPU driver module names
        gpu_modules = ['nvwgf2umx.dll', 'nvwgf2um.dll', 'nvd3dumx.dll', 'nvcuda.dll',
                      'aticfx64.dll', 'atioglxx.dll', 'atidxx64.dll', 'amdihk64.dll',
                      'ig9icd64.dll', 'igdumdim64.dll', 'igd10iumd64.dll']

        for module in crash_data.loaded_modules:
            if module['name'].lower() in gpu_modules:
                base = module['base_address']
                size = module['size']

                if base <= rip < base + size:
                    offset = rip - base
                    return f"GPU_DRIVER_CRASH: Crash inside {module['name']} at offset +0x{offset:X}"

        return None

    @staticmethod
    def _detect_address_space(crash_data: CrashData) -> Optional[str]:
        """Detect if crash is in kernel or user space.

        Args:
            crash_data: CrashData object.

        Returns:
            Finding string or None.
        """
        if not crash_data.cpu_registers:
            return None

        rip = crash_data.cpu_registers.get('RIP', 0)
        if rip == 0:
            return None

        if rip >= 0xFFFF800000000000:
            return "KERNEL_SPACE: Crash in kernel mode, driver issue"
        elif rip <= 0x00007FFFFFFFFFFF:
            return "USER_SPACE: Crash in user mode, application issue"
        else:
            return "NON_CANONICAL: Invalid address (non-canonical form)"

    @staticmethod
    def _detect_stack_corruption(crash_data: CrashData) -> Optional[str]:
        """Detect stack corruption.

        Args:
            crash_data: CrashData object.

        Returns:
            Finding string or None.
        """
        if not crash_data.cpu_registers:
            return None

        rsp = crash_data.cpu_registers.get('RSP', 0)
        rbp = crash_data.cpu_registers.get('RBP', 0)
        rip = crash_data.cpu_registers.get('RIP', 0)

        if rsp == 0:
            return None

        # Check RSP is in valid user space
        if not (0x000000000000 < rsp < 0x00007FFFFFFFFFFF):
            return "STACK_CORRUPTION: Stack pointer (RSP) in invalid memory range"

        # Check RBP >= RSP relationship
        if rbp != 0 and rbp < rsp:
            return "STACK_CORRUPTION: Base pointer (RBP) < Stack pointer (RSP)"

        # Check if RIP is on stack (possible stack smashing)
        if rsp <= rip <= rsp + 0x100000:  # Within ~1MB stack
            return "STACK_CORRUPTION: Instruction pointer on stack, possible buffer overflow"

        return None

    @staticmethod
    def _detect_bad_ram(crash_data: CrashData) -> Optional[str]:
        """Detect potential bad RAM or off-by-one errors.

        Args:
            crash_data: CrashData object.

        Returns:
            Finding string or None.
        """
        if not crash_data.cpu_registers:
            return None

        # Debug fill patterns that indicate uninitialized memory
        bad_patterns = {
            0xCDCDCDCDCDCDCDCD: "Uninitialized heap (malloc/new)",
            0xDDDDDDDDDDDDDDDD: "Freed memory (use-after-free)",
            0xFEEEFEEEFEEEFEEE: "Windows heap freed",
            0xCCCCCCCCCCCCCCCC: "Uninitialized stack",
        }

        # Check all registers for bad patterns
        for reg_name, reg_value in crash_data.cpu_registers.items():
            if reg_value in bad_patterns:
                return f"BAD_RAM_SUSPECTED: {bad_patterns[reg_value]} pattern in {reg_name} (0x{reg_value:016X})"

        # Check crash address for off-by-one from page boundaries
        if crash_data.memory_address:
            try:
                addr_str = crash_data.memory_address.replace("0x", "").replace("0X", "")
                crash_addr = int(addr_str, 16)

                # Skip off-by-one check for wild pointers and invalid addresses
                # Only check legitimate user-space addresses
                if 0x10000 <= crash_addr <= 0x00007FFFFFFFFFFF:
                    # Check if one byte off from page boundary (0x1000 alignment)
                    if (crash_addr & 0xFFF) == 0xFFF or (crash_addr & 0xFFF) == 0x1001:
                        return f"OFF_BY_ONE: Address {crash_data.memory_address} is off-by-one from page boundary"

            except Exception:
                pass

        return None
