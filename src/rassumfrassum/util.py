import sys
from datetime import datetime
from enum import IntEnum, StrEnum

import orjson as json

from .json import JSON

# Type aliases for presets
ServerCommand = list[str]
ServerCommands = list[ServerCommand]
PresetResult = tuple[ServerCommands, type | None]

class LogLevel(IntEnum):
    # lower number = higher priority
    SILENT = 0
    WARN = 1
    INFO = 2
    EVENT = 3  # DEFAULT  rassum
    DEBUG = 4  # rassum (aggregator) / frassum (LSP)
    TRACE = 5  # unused

class Ansi(StrEnum):
    # Basic set of ANSI Sequence
    RESET = '\x1b[0m'
    RED = '\x1b[1;31m'
    GREEN = '\x1b[1;32m'
    YELLOW = '\x1b[1;33m'
    BLUE = '\x1b[1;34m'
    MAGENTA = '\x1b[1;35m'
    CYAN = '\x1b[1;36m'

# Global settings
_current_log_level = LogLevel.EVENT
_max_log_length = 4000
_pretty_event: str | None = None

def set_log_level(level: int) -> None:
    """Set the global log level."""
    global _current_log_level
    _current_log_level = level

def get_log_level() -> int:
    """Get the current log level."""
    return _current_log_level

def set_max_log_length(max_len: int) -> None:
    """Set the maximum log message length (0 = unlimited)."""
    global _max_log_length
    _max_log_length = max_len

def set_pretty_event(value: str) -> None:
    """Set pretty event."""
    global _pretty_event
    _pretty_event = value if value != 'none' else None

def _truncate(s: bytes) -> bytes:
    """Internal: truncate string if needed."""
    if _max_log_length <= 0 or len(s) <= _max_log_length:
        return s
    return s[:_max_log_length] + f'... (truncated, {len(s)} bytes total)\n'.encode()

def _log(prefix: str, message: str, level: LogLevel, bmessage: bytes = b'') -> None:
    """Internal: common logging implementation."""
    if _current_log_level < level:
        return
    now = datetime.now()
    timestamp = now.strftime("%H:%M:%S.%f")[:-3]
    if _pretty_event == 'ansi':
        # WARNING: actually Emacs Eglot stderr buffer don't support ANSI sequence
        umessage = f"{Ansi.RED}{prefix}{Ansi.RESET}[{Ansi.BLUE}{timestamp}{Ansi.RESET}] {message}"
    else:
        umessage = f"{prefix}[{timestamp}] {message}"
    # NOTE: we use the bmessage trick because orjson dumps to bytes
    _ = _truncate(
        umessage.encode('utf8')
        + bmessage
        + b'\n'  # os.linesep
    )
    sys.stderr.buffer.write(_)


def info(s: str):
    """Log info-level message (high-level events, lifecycle)."""
    _log("i", s, LogLevel.INFO)

def debug(s: str):
    """Log debug-level message (method names, routing decisions)."""
    _log("d", s, LogLevel.DEBUG)

def trace(s: str):
    """Log trace-level message (full protocol details)."""
    _log("t", s, LogLevel.TRACE)

def warn(s: str):
    """Log warning message."""
    _log("W", "WARN: " + s, LogLevel.WARN)

def event(direction: str, prefix: str, data: JSON):
    """Log JSONRPC protocol event."""
    if _pretty_event == 'ansi':
        umessage = f"{Ansi.GREEN}{direction} {Ansi.YELLOW}{prefix} {Ansi.RESET}"
    else:
        umessage = f"{direction} {prefix} "
    # JSONRPC 'textDocument/semanticTokens/full' message is mainly a long list of integers
    indent = 'semanticTokens' not in prefix and _pretty_event is not None
    bmessage = json.dumps(
        data,
        option=json.OPT_INDENT_2 if indent else None,
    )
    # Format: [timestamp] --> method_name {...json...}
    _log("e", umessage, LogLevel.EVENT, bmessage)

# Alias for backward compatibility
log = info

def is_scalar(v):
    return not isinstance(v, (dict, list, set, tuple))

def dmerge(d1: dict, d2: dict):
    """Merge d2 into d1 destructively.
    Non-scalars win over scalars; d1 wins on scalar conflicts."""

    result = d1.copy()
    for key, value in d2.items():
        if key in result:
            v1, v2 = result[key], value
            # Both dicts: recursive merge
            if isinstance(v1, dict) and isinstance(v2, dict):
                result[key] = dmerge(v1, v2)
            # Both lists: concatenate
            elif isinstance(v1, list) and isinstance(v2, list):
                result[key] = v1 + v2
            # One scalar, one non-scalar: non-scalar wins
            elif is_scalar(v1) and not is_scalar(v2):
                result[key] = v2  # d2's non-scalar wins
            elif not is_scalar(v1) and is_scalar(v2):
                result[key] = v1  # d1's non-scalar wins
            # Both scalars: d1 wins (keep result[key])
        else:
            result[key] = value
    return result


def expand_braces(pattern: str) -> list[str]:
    """Expand {a,b,c} brace groups in glob pattern.

    Examples:
        "**/*.{ts,js}" -> ["**/*.ts", "**/*.js"]
        "*.{a,b}.{x,y}" -> ["*.a.x", "*.a.y", "*.b.x", "*.b.y"]
        "no-braces" -> ["no-braces"]
    """
    import re

    # Find first brace group
    match = re.search(r'\{([^}]+)\}', pattern)
    if not match:
        return [pattern]

    # Split alternatives by comma
    alternatives = match.group(1).split(',')
    prefix = pattern[: match.start()]
    suffix = pattern[match.end() :]

    # Recursively expand remaining braces
    results = []
    for alt in alternatives:
        for expanded in expand_braces(prefix + alt + suffix):
            results.append(expanded)
    return results
