def render_monitor_arrangement_to_text(monitors: list[dict], target_width: int) -> list[str]:
    """Render a visual representation of monitor arrangement as text.

    Args:
        monitors: List of monitor dictionaries from mss, where monitors[0] is the combined monitor
        target_width: Target width in characters for the visual representation

    Returns:
        List of strings, each representing a line of the visual arrangement
    """
    # Skip monitors[0] which represents "all monitors"
    monitors = monitors[1:]

    # Find bounds
    min_x = min(m["left"] for m in monitors)
    min_y = min(m["top"] for m in monitors)
    max_x = max(m["left"] + m["width"] for m in monitors)
    max_y = max(m["top"] + m["height"] for m in monitors)

    # Scale to reasonable terminal size
    scale_x = (max_x - min_x) / (target_width / 2)  # Divide width by 2 since we double it later
    scale_y = (max_y - min_y) / 15  # Fixed height scale
    scale = max(scale_x, scale_y, 1)  # Use larger scale to maintain aspect ratio

    # Create visual map
    visual = []
    for i, monitor in enumerate(monitors, 1):
        # Double the horizontal scale to compensate for character aspect ratio
        x1 = int(2 * (monitor["left"] - min_x) / scale)
        y1 = int((monitor["top"] - min_y) / scale)
        x2 = int(2 * (monitor["left"] + monitor["width"] - min_x) / scale)
        y2 = int((monitor["top"] + monitor["height"] - min_y) / scale)

        # Ensure we have enough rows
        while len(visual) <= y2:
            visual.append([" "] * (x2 + 1))
        # Ensure each row has enough columns
        for row in visual:
            while len(row) <= x2:
                row.append(" ")

        # Draw monitor borders
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                if y == y1 and x == x1:
                    visual[y][x] = "┌"
                elif y == y1 and x == x2:
                    visual[y][x] = "┐"
                elif y == y2 and x == x1:
                    visual[y][x] = "└"
                elif y == y2 and x == x2:
                    visual[y][x] = "┘"
                elif y in (y1, y2):
                    visual[y][x] = "─"
                elif x in (x1, x2):
                    visual[y][x] = "│"
                elif x == x1 + (x2 - x1) // 2 and y == y1 + (y2 - y1) // 2:
                    visual[y][x] = str(i)
                elif visual[y][x] == " ":
                    visual[y][x] = "·"

    # Convert the 2D array to a list of strings
    return ["".join(row) for row in visual]
