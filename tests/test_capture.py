from unittest.mock import MagicMock, patch

import pytest
import schedule

from time_guardian.capture import capture_screenshot, start_tracking


@pytest.fixture
def mock_mss():
    with patch("time_guardian.capture.mss.mss") as mock:
        yield mock


def test_capture_screenshot(mock_mss, tmp_path):
    mock_sct = MagicMock()
    mock_mss.return_value.__enter__.return_value = mock_sct
    mock_sct.monitors = [
        {"top": 0, "left": 0, "width": 1920, "height": 1080},
        {"top": 0, "left": 0, "width": 1920, "height": 1080},
    ]

    # Mock the screenshot object
    mock_screenshot = MagicMock()
    mock_screenshot.rgb = b"fake_image_data"
    mock_screenshot.width = 1920
    mock_screenshot.height = 1080
    mock_sct.grab.return_value = mock_screenshot

    # Clear the lru_cache for screenshotter
    with patch("time_guardian.capture.screenshotter") as mock_screenshotter:
        mock_screenshotter.cache_clear()
        mock_screenshotter.return_value = mock_sct
        result = capture_screenshot()

        mock_sct.grab.assert_called_once()
        assert result is not None


def test_capture_screenshot_error(mock_mss, tmp_path):
    mock_sct = MagicMock()
    mock_mss.return_value.__enter__.return_value = mock_sct
    mock_sct.monitors = [
        {"top": 0, "left": 0, "width": 3840, "height": 1080},  # Combined monitor
        {"top": 0, "left": 0, "width": 1920, "height": 1080},  # Individual monitor
    ]
    mock_sct.grab.side_effect = Exception("Mocked error")

    # Clear the lru_cache for screenshotter
    with patch("time_guardian.capture.screenshotter") as mock_screenshotter:
        mock_screenshotter.cache_clear()
        mock_screenshotter.return_value = mock_sct
        with pytest.raises(Exception, match="Mocked error"):
            capture_screenshot()


@patch("time_guardian.capture.schedule")
@patch("time_guardian.capture.time")
def test_start_tracking(mock_time, mock_schedule):
    # Mock time.time to return values that will make the loop run twice and then exit
    mock_time.time.side_effect = [
        0,
        30,
        30,
        90,
    ]  # First call sets end_time to 60 (1 min), subsequent calls check loop condition
    mock_time.sleep = MagicMock()

    # Mock schedule
    mock_job = MagicMock()
    mock_schedule.every.return_value.seconds.do.return_value = mock_job
    mock_schedule.CancelJob = schedule.CancelJob

    start_tracking(1, 5)  # 1 minute duration

    # Verify schedule was set up correctly
    mock_schedule.every.assert_called_once_with(5)
    mock_schedule.every.return_value.seconds.do.assert_called_once()
    assert mock_schedule.run_pending.call_count >= 1
    mock_schedule.clear.assert_called_once()


@patch("time_guardian.capture.schedule")
@patch("time_guardian.capture.time")
def test_start_tracking_keyboard_interrupt(mock_time, mock_schedule):
    mock_time.time.side_effect = [0, 10]
    mock_schedule.run_pending.side_effect = KeyboardInterrupt()

    start_tracking(1, 5)

    assert mock_schedule.every.call_count == 1
    assert mock_schedule.run_pending.call_count == 1
