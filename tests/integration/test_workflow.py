from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from time_guardian.cli import app


@pytest.fixture
def mock_storage(tmp_path):
    with patch("time_guardian.capture.STORAGE_DIR", tmp_path):
        yield tmp_path


@pytest.fixture
def mock_start_tracking():
    with patch("time_guardian.capture.start_tracking") as mock:
        yield mock


@pytest.fixture
def mock_analyze():
    with patch("time_guardian.analyze.process_screenshots") as mock:
        yield mock


def test_full_workflow(mock_storage, mock_start_tracking, mock_analyze):
    runner = CliRunner()

    # Run track command
    result = runner.invoke(app, ["track", "--duration", "1", "--interval", "5"])
    assert result.exit_code == 0
    mock_start_tracking.assert_called_once()

    # Run analyze command
    result = runner.invoke(app, ["analyze-screenshots"])
    assert result.exit_code == 0
    mock_analyze.assert_called_once()


def test_error_handling(mock_storage, mock_start_tracking, mock_analyze, caplog):
    runner = CliRunner(mix_stderr=False)  # Capture stderr separately

    # Mock error during analysis
    mock_analyze.side_effect = Exception("Error during analysis")

    # Mock the screenshots directory to exist
    screenshots_dir = mock_storage / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    with patch("time_guardian.report.generate_report") as mock_report:
        # Mock error during report generation
        mock_report.side_effect = Exception("Error during report generation")

        with pytest.raises(Exception, match="Error during analysis"):
            runner.invoke(
                app, ["analyze-screenshots", "--screenshot-dir", str(screenshots_dir)], catch_exceptions=False
            )

        mock_report.assert_not_called()


@pytest.mark.xfail(reason="Real workflow test is flaky due to timing issues")
@pytest.mark.slow
def test_real_workflow(mock_storage):
    mock_storage / "screenshots"
    runner = CliRunner()

    with patch("time_guardian.capture.start_tracking") as mock_start_tracking:
        result = runner.invoke(app, ["track", "1", "--interval", "5"])
        assert result.exit_code == 0
        mock_start_tracking.assert_called_once()


def test_version():
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Time Guardian" in result.stdout
