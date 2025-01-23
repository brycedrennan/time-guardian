import colorsys
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


def create_window_bitmap(windows, displays) -> np.ndarray:
    """Create a bitmap representation of windows where each pixel contains the window ID.

    Args:
        windows: List of window dictionaries containing position and size information
        displays: List of display dictionaries containing bounds information

    Returns:
        np.ndarray: numpy array where each pixel contains the window ID
    """
    # Find the total screen bounds
    min_x = min(d["bounds"]["x"] for d in displays)
    min_y = min(d["bounds"]["y"] for d in displays)
    max_x = max(d["bounds"]["x"] + d["bounds"]["width"] for d in displays)
    max_y = max(d["bounds"]["y"] + d["bounds"]["height"] for d in displays)

    # Create dimensions
    width = int(max_x - min_x)
    height = int(max_y - min_y)

    # Use uint16 since we're unlikely to have more than 65535 windows
    bitmap = np.zeros((height, width), dtype=np.uint32, order="C")  # Use C-contiguous memory layout

    # Sort windows by layer and stack order (higher stack_order means more in front)
    windows = sorted(windows, key=lambda w: (w["layer"], w["stack_order"]))

    # Pre-calculate all coordinates and create window masks
    for w in windows:
        x1 = int(w["position"]["x"] - min_x)
        y1 = int(w["position"]["y"] - min_y)
        x2 = x1 + int(w["size"]["width"])
        y2 = y1 + int(w["size"]["height"])
        # Use numpy's where for efficient assignment
        bitmap[y1:y2, x1:x2] = w["window_id"]

    return bitmap


def render_window_bitmap(bitmap: np.ndarray, window_ids: list) -> Image.Image:
    """Render a window bitmap as a colorful PIL Image.

    Args:
        bitmap: numpy array where each pixel contains the window ID (1-based)

    Returns:
        PIL.Image: RGB image where each window is rendered in a distinct color
    """
    # Ensure window_ids includes 0 for background
    if window_ids is not None and 0 not in window_ids:
        window_ids = [0, *list(window_ids)]
    unique_ids = np.array(window_ids)

    max_id = int(unique_ids.max())
    color_lookup = np.zeros((max_id + 1, 3), dtype=np.uint8)  # Zeros = black background
    # Skip index 0 when assigning colors to keep background black
    color_lookup[unique_ids[unique_ids > 0]] = np.array(generate_distinct_colors(len(unique_ids) - 1), dtype=np.uint8)

    rgb_image = np.empty((*bitmap.shape, 3), dtype=np.uint8)
    np.take(color_lookup, bitmap, axis=0, out=rgb_image)

    image = Image.fromarray(rgb_image, mode="RGB")

    return image


def add_visibility_pct(windows, displays, save_path: Path | None = None):
    """Calculate the actual visible percentage of each window using a bitmap approach.

    Args:
        windows: List of window dictionaries containing position and size information
        displays: List of display dictionaries containing bounds information
        save_path: Optional path to save the visibility bitmap image

    Returns:
        dict: Window IDs mapped to their actual visible percentages
    """
    bitmap = create_window_bitmap(windows, displays)

    # Get counts of each window ID using optimized numpy operations
    # Pre-allocate counts array based on max window ID
    max_id = max(w["window_id"] for w in windows)
    counts = np.zeros(max_id + 1, dtype=np.int64)
    # Use add.at which is optimized for this use case
    np.add.at(counts, bitmap.ravel(), 1)
    # Get only the window IDs that exist in the bitmap
    window_ids = np.nonzero(counts)[0]
    counts = counts[window_ids]

    # Create lookup dictionary and arrays for vectorized operations
    window_lookup = {w["window_id"]: w for w in windows}
    window_sizes = np.zeros(max_id + 1, dtype=np.int64)
    for w in windows:
        window_sizes[w["window_id"]] = int(w["size"]["width"] * w["size"]["height"])
        w["visible_pixels"] = 0
        w["visible_percent"] = 0

    # Map counts back to window IDs using vectorized operations
    # Calculate percentages for all windows at once
    window_sizes_filtered = window_sizes[window_ids]
    mask = window_sizes_filtered > 0
    percentages = np.zeros_like(counts, dtype=np.float64)
    percentages[mask] = (counts[mask] / window_sizes_filtered[mask]) * 100

    # Update window dictionaries with results
    for window_id, pixel_count, percent in zip(window_ids, counts, percentages):
        window = window_lookup.get(window_id)
        if window:
            window["visible_pixels"] = int(pixel_count)
            window["visible_percent"] = float(percent)

    # Save visualization if requested
    if save_path:
        image = render_window_bitmap(bitmap, window_ids)
        image.save(save_path)
