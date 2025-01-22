from pathlib import Path

from Quartz import (
    CGDisplayBounds,
    CGGetActiveDisplayList,
    CGWindowListCopyWindowInfo,
    kCGNullWindowID,
    kCGWindowListOptionOnScreenOnly,
)

from time_guardian.visibility import add_visibility_pct


def get_displays():
    """Get information about all connected displays."""
    # Get number of displays
    (err, displays, num_displays) = CGGetActiveDisplayList(32, None, None)
    if err:
        return []

    display_info = []
    for i, display in enumerate(displays[:num_displays]):
        bounds = CGDisplayBounds(display)
        display_info.append(
            {
                "id": i + 1,
                "bounds": {
                    "x": bounds.origin.x,
                    "y": bounds.origin.y,
                    "width": bounds.size.width,
                    "height": bounds.size.height,
                },
            }
        )
    return display_info


def get_window_display(window_bounds, displays):
    """Determine which display a window is primarily on."""
    window_center_x = window_bounds["X"] + window_bounds["Width"] / 2
    window_center_y = window_bounds["Y"] + window_bounds["Height"] / 2

    for display in displays:
        bounds = display["bounds"]
        if (
            bounds["x"] <= window_center_x <= bounds["x"] + bounds["width"]
            and bounds["y"] <= window_center_y <= bounds["y"] + bounds["height"]
        ):
            return display["id"]
    return 1  # Default to first display if not found


def get_window_info(all_layers: bool = True):
    """Get information about visible windows on screen.

    Args:
        all_layers: If True, return windows from all layers. If False, only return layer 0 windows.
    """
    window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)

    displays = get_displays()
    windows = []

    # Group windows by layer
    layer_groups = {}
    for idx, window in enumerate(window_list):
        layer = window.get("kCGWindowLayer", 0)
        if not all_layers and layer != 0:
            continue
        if layer not in layer_groups:
            layer_groups[layer] = []
        # Store original index to preserve front-to-back ordering within layer
        layer_groups[layer].append((idx, window))

    # Process windows layer by layer, preserving ordering within each layer
    for layer in sorted(layer_groups.keys()):
        # Sort windows within layer by their original index (reverse because higher indices are more in front)
        layer_windows = sorted(layer_groups[layer], key=lambda x: x[0], reverse=True)

        for stack_order, (_, window) in enumerate(layer_windows, 1):
            app_name = window.get("kCGWindowOwnerName", "Unknown")
            bounds = window.get("kCGWindowBounds")
            window_name = window.get("kCGWindowName", "")
            window.get("kCGWindowIsOnscreen", True)
            window_id = window.get("kCGWindowNumber", 0)
            pid = window.get("kCGWindowOwnerPID", 0)

            if bounds:
                display_id = get_window_display(bounds, displays)
                windows.append(
                    {
                        "window_id": window_id,
                        "pid": pid,
                        "app_name": app_name,
                        "window_name": window_name,
                        "position": {"x": bounds["X"], "y": bounds["Y"]},
                        "size": {"height": bounds["Height"], "width": bounds["Width"]},
                        "layer": layer,
                        "stack_order": stack_order,  # 1 is frontmost within the layer
                        "display": display_id,
                    }
                )

    # Calculate actual visibility percentages
    if windows:
        save_path = Path.home() / ".time-guardian" / "visibility_bitmap.png"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path = None
        add_visibility_pct(windows, displays, save_path=save_path)

    return windows
