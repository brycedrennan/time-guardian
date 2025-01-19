import pytest

from time_guardian.visibility import calculate_visibility_bitmap


def test_calculate_visibility_basic():
    """Test basic visibility calculation with non-overlapping windows."""
    displays = [{"bounds": {"x": 0, "y": 0, "width": 1000, "height": 1000}}]

    windows = [
        {
            "window_id": 1,
            "position": {"x": 0, "y": 0},
            "size": {"width": 100, "height": 100},
            "layer": 0,
            "stack_order": 1,
        },
        {
            "window_id": 2,
            "position": {"x": 200, "y": 200},
            "size": {"width": 100, "height": 100},
            "layer": 0,
            "stack_order": 2,
        },
    ]

    visibility = calculate_visibility_bitmap(windows, displays)
    assert len(visibility) == 2
    assert visibility[1] == pytest.approx(100.0)  # Window 1 fully visible
    assert visibility[2] == pytest.approx(100.0)  # Window 2 fully visible


def test_calculate_visibility_overlapping():
    """Test visibility calculation with overlapping windows."""
    displays = [{"bounds": {"x": 0, "y": 0, "width": 1000, "height": 1000}}]

    windows = [
        {
            "window_id": 1,
            "position": {"x": 0, "y": 0},
            "size": {"width": 200, "height": 200},
            "layer": 0,
            "stack_order": 1,  # Bottom window
        },
        {
            "window_id": 2,
            "position": {"x": 100, "y": 100},
            "size": {"width": 200, "height": 200},
            "layer": 0,
            "stack_order": 2,  # Top window, overlaps bottom-right quarter of window 1
        },
    ]

    visibility = calculate_visibility_bitmap(windows, displays)
    assert len(visibility) == 2
    assert visibility[1] == pytest.approx(75.0)  # Window 1 is 75% visible (top-left quarter covered)
    assert visibility[2] == pytest.approx(100.0)  # Window 2 fully visible


def test_calculate_visibility_multiple_displays():
    """Test visibility calculation with windows across multiple displays."""
    displays = [
        {"bounds": {"x": 0, "y": 0, "width": 1000, "height": 1000}},
        {"bounds": {"x": 1000, "y": 0, "width": 1000, "height": 1000}},
    ]

    windows = [
        {
            "window_id": 1,
            "position": {"x": 900, "y": 0},
            "size": {"width": 200, "height": 200},
            "layer": 0,
            "stack_order": 1,
        },
    ]

    visibility = calculate_visibility_bitmap(windows, displays)
    assert len(visibility) == 1
    assert visibility[1] == pytest.approx(100.0)  # Window should be fully visible across displays


def test_calculate_visibility_layered():
    """Test visibility calculation with windows in different layers."""
    displays = [{"bounds": {"x": 0, "y": 0, "width": 1000, "height": 1000}}]

    windows = [
        {
            "window_id": 1,
            "position": {"x": 0, "y": 0},
            "size": {"width": 200, "height": 200},
            "layer": 0,  # Bottom layer
            "stack_order": 1,
        },
        {
            "window_id": 2,
            "position": {"x": 100, "y": 100},
            "size": {"width": 200, "height": 200},
            "layer": 1,  # Top layer
            "stack_order": 1,
        },
    ]

    visibility = calculate_visibility_bitmap(windows, displays)
    assert len(visibility) == 2
    assert visibility[1] == pytest.approx(75.0)  # Window in bottom layer partially covered
    assert visibility[2] == pytest.approx(100.0)  # Window in top layer fully visible
