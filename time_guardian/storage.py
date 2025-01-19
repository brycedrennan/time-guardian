import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class Storage:
    def __init__(self, base_dir: Path = Path("time_guardian")):
        self.base_dir = base_dir
        self.screenshots_dir = self.base_dir / "screenshots"
        self.analysis_dir = self.base_dir / "analysis"
        self._create_directories()

    def _create_directories(self):
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.analysis_dir.mkdir(parents=True, exist_ok=True)

    def save_screenshot(
        self,
        screenshot: bytes,
        timestamp: int,
        monitor_idx: int = 0,
        resolution: tuple[int, int] | None = None,
        frame_no: int = 0,
    ) -> Path:
        """Save a screenshot to disk.

        Args:
            screenshot: Screenshot data in bytes
            timestamp: Unix timestamp when screenshot was taken
            monitor_idx: Index of the monitor (0 for primary monitor)
            resolution: Tuple of (width, height) for the monitor resolution

        Returns:
            Path: Path where screenshot was saved
        """
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        dt_str = dt.strftime("%Y-%m-%d-%H-%M-%S")
        res_str = f"_{resolution[0]}x{resolution[1]}" if resolution else ""
        filepath = self.screenshots_dir / f"{dt_str}_F{frame_no}_M{monitor_idx}{res_str}.png"
        try:
            filepath.write_bytes(screenshot)
            logger.info(f"Screenshot saved: {filepath}")
        except OSError as e:
            logger.error(f"IOError saving screenshot: {e}")
            raise
        except (TypeError, ValueError) as e:  # noqa: BLE001 # Catching specific data handling errors
            logger.error(f"Error saving screenshot: {e}")
            raise
        else:
            return filepath

    def save_analysis(self, analysis: dict[str, str], timestamp: int) -> Path:
        filepath = self.analysis_dir / f"analysis_{timestamp}.json"
        try:
            filepath.write_text(json.dumps(analysis))
            logger.info(f"Analysis saved: {filepath}")
        except OSError as e:
            logger.error(f"IOError saving analysis: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON encoding error: {e}")
            raise
        except Exception as e:  # noqa: BLE001 # Catching unexpected errors to ensure proper error logging
            logger.error(f"Unexpected error saving analysis: {e}")
            raise
        else:
            return filepath

    def get_screenshots(self) -> list[Path]:
        return list(self.screenshots_dir.glob("*.png"))

    def get_analysis_results(self) -> list[Path]:
        return list(self.analysis_dir.glob("*.json"))

    def get_analysis_by_timestamp(self, timestamp: int) -> dict[str, str] | None:
        filepath = self.analysis_dir / f"analysis_{timestamp}.json"
        if not filepath.exists():
            return None

        try:
            content = filepath.read_text()
        except Exception as e:  # noqa: BLE001 # Catching file read errors to return None
            logger.error(f"Error reading file {filepath}: {e}")
            return None

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error for {filepath}: {e}")
            return None
        except Exception as e:  # noqa: BLE001 # Catching unexpected errors to ensure proper error logging
            logger.error(f"Unexpected error reading analysis {filepath}: {e}")
            return None
