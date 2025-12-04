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


def check_screen_recording_permission() -> tuple[bool, str]:
    """Check if screen recording permission is granted on macOS.
    
    macOS doesn't provide a direct API to check this permission. Instead,
    when permission is denied, screenshots return the desktop wallpaper or
    a solid color instead of actual window content. We detect this by:
    1. Taking a screenshot
    2. Checking if it has enough color variance to be real screen content
    
    Returns:
        tuple: (has_permission: bool, message: str)
    """
    import platform
    
    if platform.system() != "Darwin":
        return True, "Not on macOS - no permission check needed"
    
    try:
        import numpy as np
        from time_guardian.mss_enhanced import MSS
        
        # Take a test screenshot
        with MSS() as sct:
            screenshot = sct.grab(sct.monitors[0])
            
            # Convert to numpy array for analysis
            img = np.array(screenshot)
            
            # Check 1: Count unique colors in a sample region
            # Real screen content typically has thousands of unique colors
            # Desktop wallpaper or solid color has very few
            h, w = img.shape[:2]
            
            # Sample multiple regions across the screen
            regions = [
                img[h//4:h//4+100, w//4:w//4+100],      # Top-left quadrant
                img[h//2:h//2+100, w//2:w//2+100],      # Center
                img[3*h//4:3*h//4+100, 3*w//4:3*w//4+100],  # Bottom-right quadrant
            ]
            
            total_unique = 0
            for region in regions:
                colors = region.reshape(-1, region.shape[-1])
                unique = len(np.unique(colors, axis=0))
                total_unique += unique
            
            avg_unique = total_unique / len(regions)
            
            # Check 2: Pixel variance - real content has high variance
            variance = np.var(img)
            
            # Check 3: Are the sampled regions nearly identical? (suggests wallpaper)
            region_means = [r.mean() for r in regions]
            region_variance = np.var(region_means)
            
            # Thresholds determined empirically:
            # - Real screen content: 1000+ unique colors per region, high variance
            # - Desktop wallpaper/blocked: Very few unique colors
            # 
            # We use unique colors as the primary indicator since variance
            # can be misleading with gradient wallpapers
            
            is_likely_wallpaper = avg_unique < 200  # Real screens have 1000+ unique colors per 100x100 region
            
            if is_likely_wallpaper:
                # Get the terminal that's likely running us
                import os
                terminal_hint = ""
                term_program = os.environ.get("TERM_PROGRAM", "")
                if term_program:
                    terminal_hint = f" (detected: {term_program})"
                
                msg = (
                    "Screen recording permission appears to be DENIED.\n"
                    f"Screenshots show only desktop wallpaper, not actual window content.\n"
                    f"(Detected: {int(avg_unique)} unique colors, variance={variance:.0f})\n\n"
                    "To fix this:\n"
                    f"1. Open System Settings > Privacy & Security > Screen Recording\n"
                    f"2. Enable permission for your terminal app{terminal_hint}\n"
                    "3. RESTART the terminal completely after granting permission\n"
                    "4. Run this check again to verify"
                )
                return False, msg
            
            return True, f"Screen recording permission OK ({int(avg_unique)} unique colors, variance={variance:.0f})"
        
    except ImportError as e:
        return False, f"Required module not available: {e}"
    except Exception as e:
        return False, f"Error checking screen recording permission: {e}"
