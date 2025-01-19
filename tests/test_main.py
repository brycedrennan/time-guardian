from unittest.mock import patch

from typer.testing import CliRunner

from time_guardian.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Time Guardian version:" in result.stdout


@patch("time_guardian.capture.start_tracking")
def test_track_command(mock_start_tracking):
    result = runner.invoke(app, ["track", "--duration", "1", "--interval", "5"])
    assert result.exit_code == 0
    mock_start_tracking.assert_called_once()


@patch("time_guardian.analyze.process_screenshots")
@patch("time_guardian.report.generate_report")
def test_analyze_command(mock_process, mock_generate):
    result = runner.invoke(app, ["analyze-screenshots", "--output", "test_report.txt"])
    assert result.exit_code == 0
    mock_process.assert_called_once()
    mock_generate.assert_called_once()


@patch("time_guardian.report.display_summary")
def test_summary_command(mock_display_summary):
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = True
        result = runner.invoke(app, ["summary"])
        assert result.exit_code == 0
        mock_display_summary.assert_called_once()


def test_invalid_command():
    result = runner.invoke(app, ["invalid_command"])
    assert result.exit_code != 0


@patch("time_guardian.cli.app")
def test_main_entry_point(mock_app):
    from time_guardian.__main__ import main

    main()
    mock_app.assert_called_once()
