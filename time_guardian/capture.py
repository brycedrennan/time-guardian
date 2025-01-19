import logging
import time
from io import BytesIO
from pathlib import Path

import mss
import mss.tools
import schedule
import typer
from PIL import Image, UnidentifiedImageError

from time_guardian.storage import Storage

STORAGE_DIR = Path.home() / ".time-guardian"
storage = Storage(STORAGE_DIR)

logger = logging.getLogger(__name__)


def images_are_different(img1_bytes: bytes, img2_bytes: bytes, threshold: float = 0.01) -> bool:
    """Compare two images and return True if they are different.

    Args:
        img1_bytes: First image as PNG bytes
        img2_bytes: Second image as PNG bytes
        threshold: Minimum fraction of pixels that must be different (default: 0.01 or 1%)

    Returns:
        bool: True if images are different enough to exceed the threshold
    """
    try:
        img1 = Image.open(BytesIO(img1_bytes))
        img2 = Image.open(BytesIO(img2_bytes))

        if img1.size != img2.size:
            return True

        # Convert to RGB to ensure consistent comparison
        img1_rgb = img1.convert("RGB")
        img2_rgb = img2.convert("RGB")

        # Compare pixels
        pairs = zip(img1_rgb.getdata(), img2_rgb.getdata())
        diff_pixels = sum(1 for p1, p2 in pairs if p1 != p2)
        total_pixels = img1.size[0] * img1.size[1]

        return (diff_pixels / total_pixels) > threshold

    except (UnidentifiedImageError, Image.DecompressionBombError) as e:
        logger.error(f"Error comparing images: {e}")
        return True  # If comparison fails, assume images are different


def capture_screenshot() -> list[tuple[bytes, tuple[int, int]]]:
    """Capture screenshots from all monitors and return the bytes and resolution for each.

    Returns:
        list[tuple[bytes, tuple[int, int]]]: List of tuples containing screenshot data and resolution (width, height) for each monitor
    """
    logger.info("Capturing screenshots from all monitors...")

    def validate_monitors(monitors: list) -> None:
        if not monitors:
            raise IndexError("No monitors found")

    try:
        with mss.mss() as sct:
            validate_monitors(sct.monitors)
            screenshots = []
            # Skip index 0 as it represents the "all monitors" virtual monitor in mss
            for monitor_idx in range(1, len(sct.monitors)):
                monitor = sct.monitors[monitor_idx]
                screenshot = sct.grab(monitor)
                width = screenshot.width
                height = screenshot.height
                png_bytes = mss.tools.to_png(screenshot.rgb, (width, height))
                screenshots.append((png_bytes, (width, height)))
                logger.info(f"Screenshot captured successfully from monitor {monitor_idx} ({width}x{height})")
            return screenshots

    except IndexError:
        logger.error("No suitable monitors found for capturing screenshots")
        raise
    except mss.exception.ScreenShotError as e:
        logger.error(f"Screenshot capture failed: {e}")
        raise
    except (OSError, ValueError) as e:  # noqa: BLE001 # Catching specific image processing errors
        logger.error(f"Unexpected error capturing screenshots: {e}")
        raise


def start_tracking(
    duration: int | None,
    interval: int = 5,
) -> None:
    """Start tracking screen activity by taking periodic screenshots.

    Args:
        duration: Duration in minutes to track, or None for infinite tracking
        interval: Interval in seconds between screenshots
    """
    end_time = time.time() + duration * 60 if duration is not None else float("inf")
    job_count = 0
    frame_no = 0
    previous_screenshots: dict[int, bytes] = {}  # Store previous screenshots for each monitor

    def job() -> schedule.CancelJob | None:
        nonlocal job_count, frame_no
        if time.time() > end_time:
            return schedule.CancelJob

        try:
            screenshots = capture_screenshot()
            timestamp = int(time.time())
            for idx, (screenshot_data, resolution) in enumerate(screenshots):
                # Compare with previous screenshot for this monitor
                if idx not in previous_screenshots or images_are_different(screenshot_data, previous_screenshots[idx]):
                    storage.save_screenshot(
                        screenshot_data, timestamp, monitor_idx=idx, resolution=resolution, frame_no=frame_no
                    )
                    previous_screenshots[idx] = screenshot_data
                    job_count += 1
            frame_no += 1
        except (OSError, IndexError, mss.exception.ScreenShotError) as e:  # noqa: BLE001 # Catching specific screenshot errors
            logger.error(f"Failed to capture screenshots: {e}")
        return None

    schedule.every(interval).seconds.do(job)

    try:
        while time.time() < end_time:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Tracking interrupted by user")
    finally:
        schedule.clear()
        logger.info(f"Tracking completed. Captured {job_count} screenshots")


if __name__ == "__main__":
    typer.run(start_tracking)
