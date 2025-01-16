import logging
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler

from time_guardian import __version__, analyze, capture, report

app = typer.Typer(
    help="AI-powered time travel for your screen", no_args_is_help=True, add_completion=False, name="time-guardian"
)

console = Console()
logger = logging.getLogger(__name__)


def setup_logging():
    """Set up logging with rich formatting."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True)],
    )


@app.command()
def track(
    duration: int = typer.Argument(..., help="Duration in minutes to track screen activity"),
    interval: int = typer.Option(5, help="Interval in seconds between screenshots"),
    output_dir: str = typer.Option("screenshots", "--output-dir", "-o", help="Directory to save screenshots"),
):
    """Start tracking screen activity by capturing screenshots."""
    try:
        setup_logging()
        output_path = Path(output_dir)
        console.print(f"Starting screen tracking for [bold cyan]{duration}[/] minutes[yellow]...[/]")
        console.print(f"Taking screenshots every [bold cyan]{interval}[/] seconds")
        console.print(f"Saving screenshots to: [magenta]{output_path.absolute()}[/]")

        capture.start_tracking(duration, interval)
    except KeyboardInterrupt:
        console.print("\nTracking interrupted by user")
        sys.exit(0)
    except Exception as e:  # noqa: BLE001 # Catching all errors to ensure proper error reporting
        console.print(f"Error: {e}")
        sys.exit(1)


@app.command()
def analyze_cmd(
    screenshot_dir: str = typer.Option(
        "screenshots", "--screenshot-dir", "-s", help="Directory containing screenshots"
    ),
    output: str = typer.Option("report.txt", "--output", "-o", help="Output file path for analysis report"),
):
    """Analyze captured screen activity using AI classification."""
    try:
        setup_logging()
        screenshots_path = Path(screenshot_dir)
        output_path = Path(output)
        console.print(f"Analyzing screenshots from: {screenshots_path.absolute()}")

        if not screenshots_path.exists():
            error_msg = f"Screenshot directory not found: {screenshots_path}"
            logger.error(error_msg)
            console.print(f"Error: {error_msg}")
            sys.exit(1)

        results = analyze.process_screenshots(screenshots_path)
        if not results:
            error_msg = "No screenshots found to analyze"
            logger.error(error_msg)
            console.print(f"Error: {error_msg}")
            sys.exit(1)

        report.generate_report(output_path)
        console.print(f"Analysis report saved to: {output_path.absolute()}")
    except Exception as e:  # noqa: BLE001 # Catching all errors to ensure proper error reporting
        error_msg = f"Error during analysis: {e}"
        logger.error(error_msg)
        console.print(f"Error: {error_msg}")
        sys.exit(1)


@app.command()
def summary(
    report_file: str = typer.Option("report.txt", "--report-file", "-r", help="Report file to summarize"),
):
    """Display a summary of screen time activities."""
    try:
        setup_logging()
        report_path = Path(report_file)
        if not report_path.exists():
            logger.error(f"Report file not found: {report_path}")
            sys.exit(1)

        report.display_summary(report_path)
    except (OSError, ValueError) as e:
        logger.error(f"Error displaying summary: {e}")
        sys.exit(1)


@app.command()
def version():
    """Display the current version of Time Guardian."""
    console.print(f"Time Guardian version: {__version__}")


def main():
    """Main entry point for the CLI."""
    try:
        app()
    except (OSError, ValueError, RuntimeError) as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
