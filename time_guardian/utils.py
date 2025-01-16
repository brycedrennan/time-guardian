import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


def get_timestamp() -> int:
    """Get current UTC timestamp in seconds."""
    return int(time.time())


def format_timestamp(timestamp: int) -> str:
    """Format timestamp in YYYYMMDD_HHMMSS format using UTC timezone."""
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt.strftime("%Y%m%d_%H%M%S")


def create_directory(path: Path) -> None:
    """Create directory and all parent directories if they don't exist."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log_error(f"Error creating directory {path}", e)
        raise


def list_files(directory: Path, extension: str) -> list[Path]:
    """List all files with given extension in directory."""
    if not directory.is_dir():
        logger.warning(f"Directory does not exist: {directory}")
        return []

    return sorted(directory.glob(f"*.{extension.lstrip('.')}"))


def safe_delete_file(file_path: Path) -> bool:
    """Safely delete a file if it exists.

    Returns:
        bool: True if file was deleted or didn't exist, False if deletion failed
    """
    try:
        file_path.unlink(missing_ok=True)
    except (OSError, PermissionError) as e:  # noqa: BLE001 # Catching file system and permission errors
        log_error(f"Error deleting file {file_path}", e)
        return False
    else:
        return True


def is_valid_image(file_path: Path) -> bool:
    """Check if a file has a valid image extension.

    Args:
        file_path: Path to the file to check

    Returns:
        bool: True if the file has a valid image extension, False otherwise
    """
    valid_extensions = {".png", ".jpg", ".jpeg"}
    return file_path.suffix.lower() in valid_extensions


def get_image_dimensions(file_path: Path) -> tuple[int, int] | None:
    """Get image dimensions if file is a valid image.

    Returns:
        Optional[tuple[int, int]]: (width, height) if valid image, None otherwise
    """
    try:
        with Image.open(file_path) as img:
            return img.size
    except (OSError, Image.UnidentifiedImageError):  # noqa: BLE001 # Catching file and image format errors
        return None


def log_error(message: str, exception: Exception) -> None:
    """Log an error message with exception details."""
    logger.error(f"{message}: {exception!s}")
