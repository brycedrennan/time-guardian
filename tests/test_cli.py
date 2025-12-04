"""Tests for CLI functionality."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from time_guardian.cli import app


@pytest.fixture
def mock_process():
    """Create a mock process with test data."""
    process = MagicMock()
    process.pid = 1234
    process.ppid.return_value = 1
    process.exe.return_value = "/usr/bin/test"
    process.cmdline.return_value = ["/usr/bin/test", "--arg1", "--arg2"]
    process.status.return_value = "running"
    process.username.return_value = "testuser"
    process.cpu_percent.return_value = 2.5
    process.memory_percent.return_value = 1.5
    process.create_time.return_value = 1234567890.0
    process.num_threads.return_value = 4
    return process


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
    with (
        patch("time_guardian.capture.start_tracking") as mock_start,
        patch("time_guardian.cli.check_screen_recording_permission", return_value=(True, "")),
    ):
        result = runner.invoke(app, ["track", "--duration", str(duration), "--interval", str(interval)])
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        mock_start.assert_called_once_with(duration, interval, enable_ai=True, min_changed_pixels=1000)


def test_analyze_command(runner, mock_storage):
    screenshots_dir = mock_storage / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)
    with (
        patch("time_guardian.analyze.process_screenshots") as mock_analyze,
        patch("time_guardian.report.generate_report") as mock_generate,
    ):
        mock_analyze.return_value = [("test.png", "Test activity")]
        result = runner.invoke(app, ["analyze-screenshots", "--screenshot-dir", str(screenshots_dir)])
        assert result.exit_code == 0
        mock_analyze.assert_called_once_with(str(screenshots_dir))
        mock_generate.assert_called_once()


def test_summary_command(runner, mock_storage):
    with patch("time_guardian.report.display_summary") as mock_display:
        mock_display.return_value = None

        result = runner.invoke(app, ["summary"])
        assert result.exit_code == 0
        mock_display.assert_called_once()


def test_track_command_error(runner):
    with patch("time_guardian.capture.start_tracking", side_effect=Exception("Test error")):
        result = runner.invoke(app, ["track", "--duration", "1", "--interval", "5"])
        assert result.exit_code != 0


def test_no_arguments(runner):
    result = runner.invoke(app)
    # Typer shows help when no_args_is_help=True, but exit code is 0
    assert "Usage" in result.stdout


def test_processes_command(runner, mock_process):
    """Test the processes command."""
    mock_process.info = {
        "pid": 1234,
        "ppid": 1,
        "exe": "/usr/bin/test",
        "cmdline": ["/usr/bin/test", "--arg1", "--arg2"],
        "status": "running",
        "name": "test",
    }
    with patch("time_guardian.processes.psutil.process_iter", return_value=[mock_process]):
        result = runner.invoke(app, ["processes"])
        assert result.exit_code == 0
        assert "Running Processes" in result.stdout
        assert "/usr/bin/test" in result.stdout
        assert "1234" in result.stdout
        assert "--arg1 --arg2" in result.stdout
        assert "running" in result.stdout


def test_processes_command_no_processes(runner):
    """Test the processes command when no processes are found."""
    with patch("time_guardian.processes.psutil.process_iter", return_value=[]):
        result = runner.invoke(app, ["processes"])
        assert result.exit_code == 0
        assert "No processes found" in result.stdout
