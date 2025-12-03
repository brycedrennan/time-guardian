"""Tests for process information functionality."""

from unittest.mock import MagicMock, patch

import psutil
import pytest

from time_guardian.processes import get_all_processes, get_process_info


@pytest.fixture
def mock_process():
    """Create a mock process with test data."""
    process = MagicMock()
    process.pid = 1234
    process.ppid.return_value = 1
    process.exe.return_value = "/usr/bin/test"
    process.cmdline.return_value = ["/usr/bin/test", "--arg1", "--arg2"]
    process.status.return_value = "running"
    return process


def test_get_process_info(mock_process):
    """Test getting information for a specific process."""
    with patch("psutil.Process", return_value=mock_process):
        info = get_process_info(1234)
        assert info is not None
        assert info["pid"] == 1234
        assert info["ppid"] == 1
        assert info["exe"] == "/usr/bin/test"
        assert info["cmdline"] == ["/usr/bin/test", "--arg1", "--arg2"]
        assert info["status"] == "running"


def test_get_process_info_no_such_process():
    """Test getting information for a non-existent process."""
    with patch("psutil.Process", side_effect=psutil.NoSuchProcess(1234)):
        info = get_process_info(1234)
        assert info is None


def test_get_process_info_access_denied():
    """Test getting information for a process with access denied."""
    with patch("psutil.Process", side_effect=psutil.AccessDenied()):
        info = get_process_info(1234)
        assert info is None


def test_get_all_processes(mock_process):
    """Test getting information for all processes."""
    mock_process.info = {
        "pid": 1234,
        "ppid": 1,
        "exe": "/usr/bin/test",
        "cmdline": ["/usr/bin/test", "--arg1", "--arg2"],
        "status": "running",
    }
    with patch("psutil.process_iter", return_value=[mock_process]):
        processes = get_all_processes()
        assert len(processes) == 1
        assert processes[0]["pid"] == 1234
        assert processes[0]["ppid"] == 1
        assert processes[0]["exe"] == "/usr/bin/test"
        assert processes[0]["cmdline"] == ["/usr/bin/test", "--arg1", "--arg2"]
        assert processes[0]["status"] == "running"


def test_get_all_processes_with_errors():
    """Test getting all processes when some processes raise errors."""
    error_process = MagicMock()
    error_process.info = {"pid": 5678}
    error_process.ppid.side_effect = psutil.NoSuchProcess(5678)

    good_process = MagicMock()
    good_process.info = {
        "pid": 1234,
        "ppid": 1,
        "exe": "/usr/bin/test",
        "cmdline": ["/usr/bin/test"],
        "status": "running",
    }
    good_process.pid = 1234
    good_process.ppid.return_value = 1
    good_process.exe.return_value = "/usr/bin/test"
    good_process.cmdline.return_value = ["/usr/bin/test"]
    good_process.status.return_value = "running"

    with patch("psutil.process_iter", return_value=[error_process, good_process]):
        processes = get_all_processes()
        assert len(processes) == 1
        assert processes[0]["pid"] == 1234
