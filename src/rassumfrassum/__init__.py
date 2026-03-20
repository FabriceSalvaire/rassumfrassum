"""rassumfrassum - A simple LSP multiplexer that forwards JSONRPC messages."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("rassumfrassum")
except PackageNotFoundError:
    __version__ = "unknown"
