import base64
import logging
from io import BytesIO
from pathlib import Path

import typer
from openai import OpenAI, OpenAIError
from PIL import Image

logger = logging.getLogger(__name__)

client = OpenAI()

STORAGE_DIR = Path.home() / ".time-guardian"


def process_screenshot(image_path: Path) -> str:
    """Process a single screenshot and return its description."""
    try:
        if not image_path.exists():
            logger.error(f"Image file not found: {image_path}")
            return "Image file not found"

        with Image.open(image_path) as img:
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe the computer activity in this screenshot."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}},
                    ],
                }
            ],
            max_tokens=300,  # Limit response length
        )
        if not response.choices:
            logger.error(f"No response from OpenAI API for {image_path}")
            return "Error processing image"
        return response.choices[0].message.content
    except OpenAIError as e:
        logger.error(f"OpenAI API error for {image_path}: {e}")
        return "Error processing image"
    except (OSError, ValueError) as e:  # noqa: BLE001 # Catching file and image processing errors
        logger.error(f"Error processing image {image_path}: {e}")
        return "Error processing image"


def process_screenshots(screenshot_dir: Path = Path("screenshots")) -> list[tuple[str, str]]:
    """Process all PNG screenshots in a directory and return their descriptions."""
    if not screenshot_dir.exists():
        logger.error(f"Screenshot directory not found: {screenshot_dir}")
        return []

    results = []
    for image_file in screenshot_dir.glob("*.png"):
        result = process_screenshot(image_file)
        logger.info(f"Processed {image_file.name}: {result}")
        results.append((image_file.name, result))
    return results


def main(screenshot_dir: Path = typer.Argument(Path("screenshots"), help="Directory containing screenshots")):
    """Main function to process screenshots and display results."""
    logging.basicConfig(level=logging.INFO)
    results = process_screenshots(screenshot_dir)
    for filename, description in results:
        typer.echo(f"{filename}: {description}")


if __name__ == "__main__":
    typer.run(main)
