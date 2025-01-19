import json
from pathlib import Path
from unittest.mock import patch

import pytest

from time_guardian.storage import Storage


@pytest.fixture
def storage(tmp_path):
    return Storage(base_dir=tmp_path)


@pytest.mark.parametrize(
    ("method", "data", "expected_path", "extra_args"),
    [
        ("save_screenshot", b"screenshot_data", "screenshots/2009-02-13-23-31-30_F0_M0.png", {"monitor_idx": 0}),
        ("save_screenshot", b"screenshot_data", "screenshots/2009-02-13-23-31-30_F0_M1.png", {"monitor_idx": 1}),
        ("save_analysis", {"classification": "coding"}, "analysis/analysis_1234567890.json", {}),
    ],
)
def test_save_methods(storage, method, data, expected_path, extra_args):
    with patch("pathlib.Path.write_bytes" if method == "save_screenshot" else "pathlib.Path.write_text") as mock_write:
        filepath = getattr(storage, method)(data, 1234567890, **extra_args)
        assert filepath == storage.base_dir / expected_path
        mock_write.assert_called_once()


@pytest.mark.parametrize(
    ("method", "glob_pattern"),
    [
        ("get_screenshots", "*.png"),
        ("get_analysis_results", "*.json"),
    ],
)
def test_get_methods(storage, method, glob_pattern):
    with patch("pathlib.Path.glob") as mock_glob:
        mock_glob.return_value = [Path(f"file1{glob_pattern[-4:]}"), Path(f"file2{glob_pattern[-4:]}")]
        results = getattr(storage, method)()
        assert len(results) == 2
        assert all(isinstance(r, Path) for r in results)
        mock_glob.assert_called_once_with(glob_pattern)


def test_get_analysis_by_timestamp(storage):
    mock_content = '{"classification": "browsing"}'
    with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.read_text", return_value=mock_content):
        result = storage.get_analysis_by_timestamp(1234567890)
        assert result == {"classification": "browsing"}


def test_get_analysis_by_timestamp_not_found(storage):
    with patch("pathlib.Path.exists", return_value=False):
        result = storage.get_analysis_by_timestamp(1234567890)
        assert result is None


def test_save_screenshot_error(storage):
    with pytest.raises(IOError), patch("pathlib.Path.write_bytes", side_effect=OSError("Permission denied")):
        storage.save_screenshot(b"data", 1234567890)


def test_save_analysis_json_error(storage):
    with (
        pytest.raises(json.JSONDecodeError),
        patch("json.dumps", side_effect=json.JSONDecodeError("Invalid JSON", "", 0)),
    ):
        storage.save_analysis({"invalid": object()}, 1234567890)
