from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from time_guardian.cli import app


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_storage(tmp_path):
    screenshots_dir = tmp_path / "screenshots"
    screenshots_dir.mkdir()
    return tmp_path


def test_version(runner):
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Time Guardian" in result.stdout


def test_invalid_command(runner):
    result = runner.invoke(app, ["invalid"])
    assert result.exit_code != 0


@pytest.mark.parametrize(("duration", "interval"), [(30, 10), (60, 5)])
def test_track_command(runner, mock_storage, duration, interval):
    mock_storage / "screenshots"
    with patch("time_guardian.capture.start_tracking") as mock_start:
        result = runner.invoke(app, ["track", str(duration), "--interval", str(interval)])
        assert result.exit_code == 0
        mock_start.assert_called_once()


def test_analyze_command(runner, mock_storage):
    mock_storage / "screenshots"
    with patch("time_guardian.analyze.process_screenshots") as mock_analyze:
        mock_analyze.return_value = [("test.png", "Test activity")]
        result = runner.invoke(app, ["analyze-cmd"])
        assert result.exit_code == 0
        mock_analyze.assert_called_once()


def test_summary_command(runner, mock_storage):
    # Create a mock report file
    report_path = mock_storage / "report.txt"
    report_path.write_text("Test report content")

    with patch("time_guardian.report.display_summary") as mock_display, patch("pathlib.Path.exists") as mock_exists:
        # Mock the report file existence check
        mock_exists.return_value = True
        mock_display.return_value = None

        result = runner.invoke(app, ["summary", "--report-file", str(report_path)])
        assert result.exit_code == 0
        mock_display.assert_called_once()


def test_track_command_error(runner):
    with patch("time_guardian.capture.start_tracking", side_effect=Exception("Test error")):
        result = runner.invoke(app, ["track", "1", "--interval", "5"])
        assert result.exit_code != 0
        assert "Error" in result.stdout


def test_no_arguments(runner):
    result = runner.invoke(app)
    assert result.exit_code == 0  # Typer shows help by default
    assert "Usage" in result.stdout
