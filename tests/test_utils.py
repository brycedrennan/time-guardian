import time
from pathlib import Path

import pytest

from time_guardian.utils import (
    create_directory,
    format_timestamp,
    get_timestamp,
    is_valid_image,
    list_files,
    log_error,
    safe_delete_file,
)


def test_get_timestamp():
    current_time = int(time.time())
    assert current_time <= get_timestamp() <= current_time + 1


def test_format_timestamp():
    assert format_timestamp(1609459200) == "20210101_000000"


def test_create_directory(tmp_path):
    new_dir = tmp_path / "test_dir"
    create_directory(new_dir)
    assert new_dir.is_dir()
    create_directory(new_dir)  # Should not raise an exception


def test_list_files(tmp_path):
    (tmp_path / "file1.txt").touch()
    (tmp_path / "file2.txt").touch()
    assert len(list_files(tmp_path, "txt")) == 2


def test_safe_delete_file(tmp_path):
    test_file = tmp_path / "test_file.txt"
    test_file.touch()
    safe_delete_file(test_file)
    assert not test_file.exists()
    safe_delete_file(test_file)  # Should not raise an exception


@pytest.mark.parametrize(
    ("file_path", "expected"),
    [
        ("test.png", True),
        ("test.jpg", True),
        ("test.jpeg", True),
        ("test.txt", False),
        ("test", False),
    ],
)
def test_is_valid_image(file_path, expected):
    assert is_valid_image(Path(file_path)) == expected


def test_log_error(caplog):
    log_error("Test error", Exception("Test exception"))
    assert "Test error: Test exception" in caplog.text
