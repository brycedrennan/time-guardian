"""Time Guardian - AI-powered time travel for your screen."""

try:
    from ._version import version as __version__  # type: ignore
except ImportError:
    __version__ = "0.0.0.dev0"

from . import analyze, capture, report

__all__ = ["__version__", "analyze", "capture", "report"]
