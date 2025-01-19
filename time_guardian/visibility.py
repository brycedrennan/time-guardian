import colorsys
import logging
import time
from pathlib import Path

import numpy as np
from PIL import Image


def generate_distinct_colors(n: int) -> list[tuple[int, int, int]]:
    """Generate n visually distinct RGB colors using HSV color space.

    Args:
        n: Number of distinct colors needed

    Returns:
        List of RGB tuples with values from 0-255
    """
    if n <= 0:
        return []

    # Use golden ratio for even spacing in hue
    golden_ratio = 0.618033988749895
    colors = []
    h = 0.1  # Start hue at 0.1 to avoid pure red

    for i in range(n):
        # Use fixed saturation and value for consistent brightness
        hsv = (h, 0.95, 0.95)
        # Convert to RGB (0-1 range)
        rgb = colorsys.hsv_to_rgb(*hsv)
        # Convert to 0-255 range
        rgb_int = tuple(int(x * 255) for x in rgb)
        colors.append(rgb_int)
        h = (h + golden_ratio) % 1.0

    return colors


def calculate_visibility_bitmap(windows, displays, save_path: Path | None = None, include_layers: tuple[int] = ()):
    """Calculate the actual visible percentage of each window using a bitmap approach.

    Args:
        windows: List of window dictionaries containing position and size information
        displays: List of display dictionaries containing bounds information
        save_path: Optional path to save the visibility bitmap image

    Returns:
        dict: Window IDs mapped to their actual visible percentages
    """
    bitmap_start = time.perf_counter()

    # Find the total screen bounds
    min_x = min(d["bounds"]["x"] for d in displays)
    min_y = min(d["bounds"]["y"] for d in displays)
    max_x = max(d["bounds"]["x"] + d["bounds"]["width"] for d in displays)
    max_y = max(d["bounds"]["y"] + d["bounds"]["height"] for d in displays)

    # Create dimensions
    width = int(max_x - min_x)
    height = int(max_y - min_y)

    # Create a numpy array storing window IDs (using int32 for plenty of window IDs)
    bitmap = np.zeros((height, width), dtype=np.int32)

    # Sort windows by layer and stack order (higher stack_order means more in front)
    sorted_windows = sorted(windows, key=lambda w: (w["layer"], w["stack_order"]))

    if include_layers:
        sorted_windows = [w for w in sorted_windows if w["layer"] in include_layers]

    # Calculate total pixels for each window
    total_pixels = {w["window_id"]: int(w["size"]["width"] * w["size"]["height"]) for w in sorted_windows}

    # Draw windows from back to front directly with window IDs
    for i, window in enumerate(sorted_windows, start=1):
        pos = window["position"]
        size = window["size"]
        # Adjust coordinates relative to the bitmap origin
        x1 = int(pos["x"] - min_x)
        y1 = int(pos["y"] - min_y)
        x2 = int(x1 + size["width"])
        y2 = int(y1 + size["height"])

        # Set the window ID in the bitmap
        bitmap[y1:y2, x1:x2] = i

    bitmap_end = time.perf_counter()
    logging.info(f"Bitmap creation took {(bitmap_end - bitmap_start) * 1000:.2f}ms")

    # Count visible pixels for each window
    count_start = time.perf_counter()

    # Get counts of each window ID
    unique_ids, counts = np.unique(bitmap, return_counts=True)
    count_lookup = dict(zip(unique_ids, counts))

    # Map counts back to window IDs (skipping 0 which is background)
    window_pixels = {}
    for window_id, window in zip(range(1, len(sorted_windows) + 1), sorted_windows):
        visible_pixels = count_lookup.get(window_id, 0)

        if total_pixels[window["window_id"]] > 0:
            window_pixels[window["window_id"]] = (visible_pixels / total_pixels[window["window_id"]]) * 100

    count_end = time.perf_counter()
    logging.info(f"Pixel counting took {(count_end - count_start) * 1000:.2f}ms")

    # Save visualization if requested
    if save_path:
        save_start = time.perf_counter()
        # Get unique window IDs from bitmap (excluding 0/background)
        unique_ids = unique_ids[unique_ids != 0]  # exclude background

        # Generate colors only when saving
        distinct_colors = generate_distinct_colors(len(unique_ids) + 1)  # +1 for background
        # Create color mapping for each window ID
        color_map = {id_: distinct_colors[i + 1] for i, id_ in enumerate(unique_ids)}

        # Create RGB image
        rgb_image = np.zeros((height, width, 3), dtype=np.uint8)

        # Map window IDs to colors
        for window_id, color in color_map.items():
            mask = bitmap == window_id
            for c in range(3):
                rgb_image[mask, c] = color[c]

        # Save the image
        Image.fromarray(rgb_image).save(save_path)
        save_end = time.perf_counter()
        logging.info(f"Bitmap save took {(save_end - save_start) * 1000:.2f}ms")

    return window_pixels
