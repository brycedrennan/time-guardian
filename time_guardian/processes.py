"""Module for getting information about running processes."""

import logging
from typing import Any

import psutil

logger = logging.getLogger(__name__)


def get_process_info(pid: int) -> dict[str, Any] | None:
    """Get detailed information about a specific process.

    Args:
        pid: Process ID to get information for

    Returns:
        dict: Process information including pid, ppid, exe, cmdline, and status
        None: If process not found or access denied
    """
    try:
        proc = psutil.Process(pid)
        return {
            "pid": proc.pid,
            "ppid": proc.ppid(),
            "exe": proc.exe(),
            "cmdline": proc.cmdline(),
            "status": proc.status(),
            "name": proc.name(),
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
        logger.debug(f"Could not get info for process {pid}: {e}")
        return None


def get_all_processes() -> list[dict[str, Any]]:
    """Get information about all running processes.

    Returns:
        list: List of dictionaries containing process information
    """
    processes = []
    for proc in psutil.process_iter(["pid", "ppid", "exe", "cmdline", "status", "name"]):
        try:
            proc_info = proc.info
            # Ensure we have all required fields
            if not all(k in proc_info for k in ["pid", "ppid", "exe", "cmdline", "status", "name"]):
                proc_info = {
                    "pid": proc.pid,
                    "ppid": proc.ppid(),
                    "exe": proc.exe(),
                    "cmdline": proc.cmdline(),
                    "status": proc.status(),
                    "name": proc.name(),
                }
            processes.append(proc_info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return processes
