from unittest.mock import MagicMock, patch

import pytest

from time_guardian.report import Report, display_summary, generate_report


@pytest.fixture
def mock_storage():
    with patch("time_guardian.report.Storage") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_ai_classifier():
    with patch("time_guardian.report.AIClassifier") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def report(mock_storage, mock_ai_classifier):
    return Report(mock_storage)


def test_generate_report(report, tmp_path):
    output_path = tmp_path / "report.txt"
    report.storage.get_all_window_analyses.return_value = [
        {
            "app_name": "TestApp",
            "window_name": "Test Window",
            "classification": "Test activity",
            "datetime": "2025-01-01T00:00:00",
        }
    ]
    report.ai_classifier.summarize_activity.return_value = "AI summary of activities"

    report.generate_report(output_path)

    assert output_path.exists()
    content = output_path.read_text()
    assert "Test activity" in content
    assert "AI summary of activities" in content


def test_display_summary(report, capsys):
    report.storage.get_all_window_analyses.return_value = [
        {
            "app_name": "TestApp",
            "window_name": "Test Window",
            "classification": "Test activity",
            "datetime": "2025-01-01T00:00:00",
        },
        {
            "app_name": "TestApp",
            "window_name": "Test Window 2",
            "classification": "Another activity",
            "datetime": "2025-01-01T00:01:00",
        },
        {
            "app_name": "OtherApp",
            "window_name": "Other Window",
            "classification": "Third activity",
            "datetime": "2025-01-01T00:02:00",
        },
    ]
    report.ai_classifier.summarize_activity.return_value = "AI summary"

    report.display_summary()

    captured = capsys.readouterr()
    assert "TestApp" in captured.out
    assert "AI summary" in captured.out


def test_summarize_activities(report):
    activities = [{"classification": "Activity 1"}, {"classification": "Activity 2"}]
    report.ai_classifier.summarize_activity.return_value = "Summary of activities"

    result = report.summarize_activities(activities)

    assert result == "Summary of activities"
    report.ai_classifier.summarize_activity.assert_called_once_with(activities)


def test_generate_report_function(tmp_path):
    output_path = tmp_path / "test_report.txt"
    with patch("time_guardian.report.Report") as MockReport:
        mock_instance = MagicMock()
        MockReport.return_value = mock_instance

        generate_report(output_path)

        mock_instance.generate_report.assert_called_once_with(output_path)


def test_display_summary_function():
    with patch("time_guardian.report.Report") as MockReport:
        mock_instance = MagicMock()
        MockReport.return_value = mock_instance

        display_summary()

        mock_instance.display_summary.assert_called_once()
