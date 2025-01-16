import base64
import logging
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path

from openai import OpenAI, OpenAIError
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)


class AIClassifier:
    """Classifies images using OpenAI's GPT-4 Vision API."""

    def __init__(self):
        """Initialize the AI classifier with OpenAI client."""
        self.client = OpenAI()

    def _encode_image(self, image_path: Path) -> str:
        """Encode an image file to base64 string.

        Args:
            image_path: Path to the image file

        Returns:
            str: Base64 encoded image data

        Raises:
            FileNotFoundError: If image file doesn't exist
            UnidentifiedImageError: If file is not a valid image
        """
        if not image_path.exists():
            msg = f"Image file not found: {image_path}"
            raise FileNotFoundError(msg)

        try:
            with Image.open(image_path) as img:
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                return base64.b64encode(buffered.getvalue()).decode("utf-8")
        except UnidentifiedImageError:
            msg = f"Not a valid image file: {image_path}"
            raise UnidentifiedImageError(msg)

    def classify_image(self, image_path: Path) -> dict[str, str]:
        """Classify a single image using OpenAI's vision model."""
        if not image_path.exists():
            error_msg = f"Image file not found: {image_path.name}"
            logging.error(error_msg)
            return {"error": error_msg}

        try:
            base64_image = self._encode_image(image_path)
        except (OSError, ValueError) as e:  # noqa: BLE001 # Catching file and image processing errors
            error_msg = f"Error processing image: {e}"
            logging.error(error_msg)
            return {"error": error_msg}

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "What activity is shown in this screenshot? Respond with just the activity name, no explanation.",
                            },
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
                        ],
                    }
                ],
                max_tokens=300,
            )

            if not response.choices:
                error_msg = "No response from OpenAI API"
                logging.error(error_msg)
                return {"error": error_msg}

            return {"classification": response.choices[0].message.content}
        except OpenAIError as e:
            error_msg = f"OpenAI API error: {e}"
            logging.error(error_msg)
            return {"error": error_msg}

    def classify_batch(self, image_paths: Sequence[Path]) -> list[dict[str, str]]:
        """Classify multiple images and return the results.

        Args:
            image_paths: Sequence of paths to image files

        Returns:
            list: List of classification results for each image
        """
        if not image_paths:
            logger.warning("No images provided for batch classification")
            return []

        results = []
        for image_path in image_paths:
            result = self.classify_image(image_path)
            results.append(result)
        return results

    def summarize_activity(self, classifications: list[dict[str, str]]) -> str:
        """Generate an AI-powered summary of computer activities."""
        if not classifications:
            return "Unable to generate AI summary"

        try:
            activities_text = "\n".join([c.get("classification", "Unknown") for c in classifications])
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": f"Summarize these computer activities:\n{activities_text}"}],
                max_tokens=300,
            )
            return response.choices[0].message.content.strip()
        except OpenAIError as e:
            error_msg = f"OpenAI API error: {e!s}"
            logging.error(error_msg)
            return "Unable to generate AI summary"
        except (KeyError, ValueError) as e:  # noqa: BLE001 # Catching data structure and parsing errors
            error_msg = f"Error generating summary: {e!s}"
            logging.error(error_msg)
            return "Unable to generate AI summary"
