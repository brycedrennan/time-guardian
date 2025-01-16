"""Main entry point for the Time Guardian application."""

import logging
import sys

from time_guardian.cli import app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the application."""
    try:
        app()
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
