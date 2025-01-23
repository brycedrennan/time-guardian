import logging
import time
from functools import lru_cache
from pathlib import Path

import mss
import mss.tools
import numpy as np
import schedule
import typer

from time_guardian.storage import Storage
from time_guardian.visibility import create_window_bitmap, render_window_bitmap
from time_guardian.windows import get_displays, get_window_info

STORAGE_DIR = Path.home() / ".time-guardian"
storage = Storage(STORAGE_DIR)

logger = logging.getLogger(__name__)


def images_are_different(img1: np.array, img2: np.array, threshold: float = 0.001) -> bool:
    """Compare two images and return True if they are different.

    Args:
        img1: First image as numpy array
        img2: Second image as numpy array
        threshold: Minimum fraction of pixels that must be different (default: 0.001 or 0.1%)

    Returns:
        bool: True if images are different enough to exceed the threshold
    """

    if img1.shape != img2.shape:
        return True

    # Compare pixels
    diff_pixels = np.sum(img1 != img2)
    total_pixels = img1.size

    return (diff_pixels / total_pixels) > threshold


def compute_image_diff(img1: np.array, img2: np.array) -> np.array:
    """Compute the difference array between two images.

    Args:
        img1: First image as numpy array
        img2: Second image as numpy array

    Returns:
        np.array: Array of differences between the images. Zero values indicate matching pixels.
    """

    if img1.shape != img2.shape:
        raise ValueError("Images must have the same shape")

    # Compute absolute difference between images
    return np.abs(img1.astype(np.int16) - img2.astype(np.int16))


def has_significant_diff(img1: np.array, img2: np.array, threshold: float = 0.001) -> bool:
    """Determine if two images are significantly different based on pixel differences.

    Args:
        img1: First image as numpy array
        img2: Second image as numpy array
        threshold: Minimum fraction of pixels that must be different (default: 0.001 or 0.1%)

    Returns:
        bool: True if images are different enough to exceed the threshold
    """
    if img1.shape != img2.shape:
        return True

    diff = compute_image_diff(img1, img2)
    diff_pixels = np.count_nonzero(diff)
    total_pixels = img1.size

    return (diff_pixels / total_pixels) > threshold


@lru_cache
def screenshotter():
    return mss.mss()


def capture_screenshot():
    sct = screenshotter()
    displays = get_displays()
    min_y = min(d["bounds"]["y"] for d in displays)
    max_y = max(d["bounds"]["y"] + d["bounds"]["height"] for d in displays)
    logical_display_height = max_y - min_y

    # Get raw pixels from the screen, save it to a Numpy array
    np_img = np.array(sct.grab(sct.monitors[0]))

    # if the monitors are using scaling, reduce the screenshot to the logical display height
    if np_img.shape[0] > logical_display_height:
        scale_factor = int(np_img.shape[0] / logical_display_height)
        np_img = np_img[::scale_factor, ::scale_factor, :3]

    return np_img


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
    frame_no = 0
    previous_screenshot = None

    def job() -> schedule.CancelJob | None:
        nonlocal frame_no, previous_screenshot
        if time.time() > end_time:
            return schedule.CancelJob

        displays = get_displays()

        offset_x = min(d["bounds"]["x"] for d in displays) * -1
        offset_y = min(d["bounds"]["y"] for d in displays) * -1

        np_img = capture_screenshot()
        timestamp = int(time.time())

        if previous_screenshot is None:
            storage.save_screenshot(np_img, timestamp, frame_no=frame_no)
            previous_screenshot = np_img
            frame_no += 1
            return None

        windows = get_window_info(show_visibility=False, all_layers=False)
        window_ids = [window["window_id"] for window in windows]
        window_bitmap = create_window_bitmap(windows, displays)
        image = render_window_bitmap(window_bitmap, window_ids)
        image.save("/Users/bryce/.time-guardian/window_bitmap.png")

        # Calculate absolute pixel differences across all channels
        pixel_diffs = np.abs(np_img.astype(np.int16) - previous_screenshot.astype(np.int16))
        # Consider a pixel changed if the sum of channel differences exceeds threshold
        threshold = 50  # Adjust this value to control sensitivity
        diff_mask = pixel_diffs.sum(axis=2) > threshold

        window_bitmap_diff = window_bitmap * diff_mask

        # count the number of unique values in window_bitmap_diff
        unique_values, counts = np.unique(window_bitmap_diff, return_counts=True)
        del window_bitmap_diff
        diff_counts = dict(zip(unique_values, counts))

        window_lookup = {window["window_id"]: window for window in windows}
        # print which windows have changed
        for window_id, count in diff_counts.items():
            window_id = int(window_id)
            window = window_lookup.get(window_id)
            if not window:
                continue
            if count > 1000:
                print(
                    f"{frame_no} - Window {window_id} - {window['app_name']} - {window['window_name']} has changed {count} pixels"
                )

                # Get window bounds in display coordinates
                x = int(window["position"]["x"]) + int(offset_x)
                y = int(window["position"]["y"]) + int(offset_y)
                width = int(window["size"]["width"])
                height = int(window["size"]["height"])

                # Crop both the mask and image to the window bounds
                cropped_bitmap = window_bitmap[y : y + height, x : x + width]
                cropped_img = np_img[y : y + height, x : x + width]
                cropped_diff_mask = diff_mask[y : y + height, x : x + width]

                cropped_window_mask = cropped_bitmap == window_id

                cropped_img[~cropped_window_mask] = 0
                cropped_diff_mask[~cropped_window_mask] = 0
                # Save the window-specific screenshot and diff mask
                storage.save_window_screenshot(
                    cropped_img,
                    window_id,
                    window["app_name"],
                    window["window_name"],
                    timestamp,
                    frame_no,
                    # diff_mask=cropped_diff_mask,
                    # window_mask=cropped_window_mask
                )
        previous_screenshot = np_img
        frame_no += 1
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
        logger.info(f"Tracking completed. Captured {frame_no} screenshots")


if __name__ == "__main__":
    typer.run(start_tracking)
