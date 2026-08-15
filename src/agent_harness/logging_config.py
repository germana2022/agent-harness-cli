"""Standard-library logging configuration.

Logs go to stderr only. There is no log file, telemetry, or network transport.
"""

from __future__ import annotations

import logging
import sys


def setup_logging(log_level: str, verbose: bool = False) -> None:
    """Configure root logging to stderr.

    ``verbose`` forces DEBUG level for extra diagnostics.
    """
    level = logging.DEBUG if verbose else logging.getLevelName(log_level.upper())
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format="%(levelname)s: %(message)s",
    )
