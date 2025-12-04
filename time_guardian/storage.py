import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class Storage:
    def __init__(self, base_dir: Path = Path("time_guardian")):
        self.base_dir = base_dir
        self.screenshots_dir = self.base_dir / "screenshots"
        self.analysis_dir = self.base_dir / "analysis"
        self.window_screenshots_dir = self.base_dir / "window_screenshots"
        self._create_directories()

    def _create_directories(self):
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        self.window_screenshots_dir.mkdir(parents=True, exist_ok=True)

    def save_screenshot(
        self,
        np_img: np.ndarray,
        timestamp: int,
        frame_no: int = 0,
    ) -> Path:
        """Save a screenshot to disk.

        Args:
            screenshot: Screenshot data in bytes
            timestamp: Unix timestamp when screenshot was taken

        Returns:
            Path: Path where screenshot was saved
        """
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        dt_str = dt.strftime("%Y-%m-%d-%H-%M-%S")
        filepath = self.screenshots_dir / f"{dt_str}_F{frame_no}.png"

        rgb_img = np_img[..., ::-1]  # Reverse the color channels from BGR to RGB using numpy
        Image.fromarray(rgb_img).save(filepath, optimize=False)

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

    def save_window_screenshot(
        self,
        np_img: np.ndarray,
        window_id: int,
        app_name: str,
        window_name: str,
        timestamp: int,
        frame_no: int = 0,
        diff_mask: np.ndarray | None = None,
        window_mask: np.ndarray | None = None,
    ) -> tuple[Path, Path | None]:
        """Save a window-specific screenshot to disk.

        Args:
            np_img: Screenshot data as numpy array
            window_id: ID of the window
            app_name: Name of the application
            window_name: Name of the window
            timestamp: Unix timestamp when screenshot was taken
            frame_no: Frame number
            diff_mask: Optional boolean mask showing which pixels changed
            window_mask: Optional boolean mask showing which pixels are part of the window
        Returns:
            tuple: Path where screenshot was saved and path where diff mask was saved (if provided)
        """
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        dt_str = dt.strftime("%Y-%m-%d-%H-%M-%S")

        # Create a sanitized filename
        safe_app_name = "".join(c for c in app_name if c.isalnum() or c in (" ", "-", "_")).strip()
        safe_window_name = "".join(c for c in window_name if c.isalnum() or c in (" ", "-", "_")).strip()

        base_path = self.window_screenshots_dir / f"{dt_str}_F{frame_no}_{window_id}_{safe_app_name}_{safe_window_name}"
        img_path = base_path.with_suffix(".png")

        rgb_img = np_img[..., ::-1]  # Reverse the color channels from BGR to RGB using numpy
        Image.fromarray(rgb_img).save(img_path, optimize=False)

        mask_path = None
        if diff_mask is not None:
            mask_path = base_path.with_suffix(".mask.png")
            # Convert boolean mask to uint8 for saving as image
            mask_img = diff_mask.astype(np.uint8) * 255
            Image.fromarray(mask_img).save(mask_path, optimize=False)

        if window_mask is not None:
            mask_path = base_path.with_suffix(".window_mask.png")
            # Convert boolean mask to uint8 for saving as image
            mask_img = window_mask.astype(np.uint8) * 255
            Image.fromarray(mask_img).save(mask_path, optimize=False)

        return img_path, mask_path

    def save_window_analysis(
        self,
        window_id: int,
        app_name: str,
        window_name: str,
        timestamp: int,
        frame_no: int,
        classification: str,
        image_path: Path,
    ) -> Path:
        """Save analysis for a specific window screenshot.

        Args:
            window_id: ID of the window
            app_name: Name of the application
            window_name: Name of the window
            timestamp: Unix timestamp when screenshot was taken
            frame_no: Frame number
            classification: AI classification/description of the window content
            image_path: Path to the screenshot that was analyzed

        Returns:
            Path: Path where analysis was saved
        """
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        dt_str = dt.strftime("%Y-%m-%d-%H-%M-%S")

        analysis = {
            "timestamp": timestamp,
            "datetime": dt.isoformat(),
            "frame_no": frame_no,
            "window_id": window_id,
            "app_name": app_name,
            "window_name": window_name,
            "classification": classification,
            "image_path": str(image_path),
        }

        # Create a sanitized filename
        safe_app_name = "".join(c for c in app_name if c.isalnum() or c in (" ", "-", "_")).strip()
        filepath = self.analysis_dir / f"{dt_str}_F{frame_no}_{window_id}_{safe_app_name}.json"
        filepath.write_text(json.dumps(analysis, indent=2))
        logger.info(f"Window analysis saved: {filepath}")
        return filepath

    def get_all_window_analyses(self) -> list[dict[str, Any]]:
        """Get all window analysis results sorted by timestamp.

        Returns:
            list: List of analysis dictionaries sorted by timestamp
        """
        analyses = []
        for filepath in self.analysis_dir.glob("*.json"):
            try:
                content = json.loads(filepath.read_text())
                analyses.append(content)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Error reading analysis file {filepath}: {e}")
                continue
        return sorted(analyses, key=lambda x: (x.get("timestamp", 0), x.get("frame_no", 0)))
