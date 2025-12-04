import logging
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
import schedule
import typer

from time_guardian.ai_classifier import AIClassifier
from time_guardian.storage import Storage
from time_guardian.visibility import create_window_bitmap, render_window_bitmap
from time_guardian.windows import get_displays, get_window_info

STORAGE_DIR = Path.home() / ".time-guardian"
storage = Storage(STORAGE_DIR)

logger = logging.getLogger(__name__)

# Lazy-loaded AI classifier (only created when needed)
_classifier: AIClassifier | None = None


def get_classifier() -> AIClassifier:
    """Get or create the AI classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = AIClassifier()
    return _classifier


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
    """Get a cached MSS instance for monitor info only."""
    from time_guardian.mss_enhanced import MSS

    return MSS()


def capture_screenshot():
    """Capture a screenshot of all monitors.
    
    Creates a fresh MSS instance for each capture to avoid data caching issues
    on macOS where the raw buffer may not update within a single process.
    """
    from time_guardian.mss_enhanced import MSS
    
    # Use fresh MSS instance for each grab to avoid caching issues
    with MSS() as sct:
        monitor = sct.monitors[0]
        s = sct.grab(monitor)
        scale_factor = int(s.height / monitor["height"])
        
        # Create numpy view of raw buffer with strided access for scaling
        np_view = np.ndarray(
            shape=(s.height // scale_factor, s.width // scale_factor, 3),
            dtype=np.uint8,
            buffer=s.raw,
            strides=(s.width * (scale_factor * 4), scale_factor * 4, 1),
        )
        
        # Copy the data before MSS context closes
        np_img = np_view.copy()

    return np_img


def start_tracking(
    duration: int | None,
    interval: int = 5,
    enable_ai: bool = True,
    min_changed_pixels: int = 1000,
) -> None:
    """Start tracking screen activity by taking periodic screenshots.

    Args:
        duration: Duration in minutes to track, or None for infinite tracking
        interval: Interval in seconds between screenshots
        enable_ai: Whether to use AI to classify window contents (default: True)
        min_changed_pixels: Minimum number of changed pixels to trigger analysis (default: 1000)
    """
    end_time = time.time() + duration * 60 if duration is not None else float("inf")
    frame_no = 0
    previous_screenshot = None

    # Get classifier only if AI is enabled
    classifier = get_classifier() if enable_ai else None
    if enable_ai:
        logger.info("AI classification enabled - will analyze changed windows")

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
        image.save(str(STORAGE_DIR / "window_bitmap.png"))

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
        
        # Track windows that changed for this frame
        changed_windows = []
        
        for window_id, count in diff_counts.items():
            window_id = int(window_id)
            window = window_lookup.get(window_id)
            if not window:
                continue
            if count > min_changed_pixels:
                logger.info(
                    f"Frame {frame_no}: {window['app_name']} - {window['window_name']} changed {count} pixels"
                )

                # Get window bounds in display coordinates
                x = int(window["position"]["x"]) + int(offset_x)
                y = int(window["position"]["y"]) + int(offset_y)
                width = int(window["size"]["width"])
                height = int(window["size"]["height"])

                # Crop both the mask and image to the window bounds
                cropped_bitmap = window_bitmap[y : y + height, x : x + width]
                cropped_img = np_img[y : y + height, x : x + width].copy()
                cropped_diff_mask = diff_mask[y : y + height, x : x + width]

                cropped_window_mask = cropped_bitmap == window_id

                cropped_img[~cropped_window_mask] = 0
                cropped_diff_mask[~cropped_window_mask] = 0
                
                # Save the window-specific screenshot
                img_path, _ = storage.save_window_screenshot(
                    cropped_img,
                    window_id,
                    window["app_name"],
                    window["window_name"],
                    timestamp,
                    frame_no,
                )
                
                changed_windows.append({
                    "window": window,
                    "img_path": img_path,
                    "pixel_count": count,
                })
        
        # Classify changed windows with AI
        if classifier and changed_windows:
            for item in changed_windows:
                window = item["window"]
                img_path = item["img_path"]
                
                logger.info(f"Classifying: {window['app_name']} - {window['window_name']}")
                result = classifier.classify_image(img_path)
                
                if "classification" in result:
                    classification = result["classification"]
                    logger.info(f"  → {classification}")
                    
                    # Save the analysis
                    storage.save_window_analysis(
                        window_id=window["window_id"],
                        app_name=window["app_name"],
                        window_name=window["window_name"],
                        timestamp=timestamp,
                        frame_no=frame_no,
                        classification=classification,
                        image_path=img_path,
                    )
                elif "error" in result:
                    logger.warning(f"  → Classification failed: {result['error']}")
        
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
