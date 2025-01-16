import logging
import time
from pathlib import Path

import mss
import mss.tools
import schedule
import typer

from time_guardian.storage import Storage

STORAGE_DIR = Path.home() / ".time-guardian"
storage = Storage(STORAGE_DIR)

logger = logging.getLogger(__name__)


def capture_screenshot() -> list[bytes]:
    """Capture screenshots from all monitors and return the bytes for each.

    Returns:
        list[bytes]: List of screenshot data for each monitor
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
                screenshots.append(png_bytes)
                logger.info(f"Screenshot captured successfully from monitor {monitor_idx}")
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
    duration: int,
    interval: int = 5,
) -> None:
    """Start tracking screen activity by taking periodic screenshots.

    Args:
        duration: Duration in minutes to track
        interval: Interval in seconds between screenshots
    """
    end_time = time.time() + duration * 60
    job_count = 0

    def job() -> schedule.CancelJob | None:
        nonlocal job_count
        if time.time() > end_time:
            return schedule.CancelJob

        try:
            screenshots = capture_screenshot()
            timestamp = int(time.time())
            for idx, screenshot_data in enumerate(screenshots):
                storage.save_screenshot(screenshot_data, timestamp, monitor_idx=idx)
            job_count += 1
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
