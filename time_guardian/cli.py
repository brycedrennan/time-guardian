import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from time_guardian import __version__, analyze, capture, report
from time_guardian.windows import get_window_info

app = typer.Typer(
    help="AI-powered time travel for your screen",
    no_args_is_help=True,
    add_completion=False,
    name="time-guardian",
    pretty_exceptions_show_locals=False,
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
    duration: int | None = typer.Option(
        None, help="Duration in minutes to track screen activity (default: run forever)"
    ),
    interval: int = typer.Option(5, help="Interval in seconds between screenshots"),
):
    """Start tracking screen activity by capturing screenshots."""
    setup_logging()
    if duration is None:
        console.print("Starting screen tracking [bold cyan]forever[/] (press Ctrl+C to stop)[yellow]...[/]")
    else:
        console.print(f"Starting screen tracking for [bold cyan]{duration}[/] minutes[yellow]...[/]")
    console.print(f"Taking screenshots every [bold cyan]{interval}[/] seconds")

    capture.start_tracking(duration, interval)
    return 0


@app.command()
def analyze_screenshots(
    screenshot_dir: str = typer.Option(
        "screenshots", "--screenshot-dir", "-s", help="Directory containing screenshots"
    ),
    output: str = typer.Option("report.txt", "--output", "-o", help="Output file path for analysis report"),
):
    """Analyze screenshots and generate a report."""
    setup_logging()
    screenshot_path = Path(screenshot_dir).resolve()
    if not screenshot_path.exists():
        logger.error(f"Screenshot directory {screenshot_dir} does not exist")
        raise typer.Exit(code=1)

    console.print(f"Analyzing screenshots in [bold cyan]{screenshot_dir}[/][yellow]...[/]")
    results = analyze.process_screenshots(str(screenshot_path))

    if not results:
        logger.warning("No screenshots found to analyze")
        return 0

    report.generate_report(Path(output))
    console.print(f"\nAnalysis complete! Report saved to [bold cyan]{output}[/]")
    return 0


@app.command()
def summary(
    report_file: str = typer.Option("report.txt", "--report-file", "-r", help="Report file to summarize"),
):
    """Display a summary of the analysis report."""
    setup_logging()
    report_path = Path(report_file)
    if not report_path.exists():
        logger.error(f"Report file {report_file} does not exist")
        raise typer.Exit(code=1)

    report.display_summary(report_path)
    return 0


@app.command()
def version():
    """Display version information."""
    console.print(f"Time Guardian version: {__version__}")
    return 0


@app.command()
def windows():
    """Display information about all visible windows on screen."""
    setup_logging()
    windows = get_window_info()

    if not windows:
        console.print("No visible windows found")
        return

    table = Table(title="Window Locations")
    table.add_column("ID", justify="right")
    table.add_column("PID", justify="right")
    table.add_column("Application")
    table.add_column("Window")
    table.add_column("Position")
    table.add_column("Size")
    table.add_column("Layer", justify="right")
    table.add_column("Stack", justify="right")
    table.add_column("Visible %", justify="right")
    table.add_column("Display", justify="right")

    for window in windows:
        pos = window["position"]
        size = window["size"]
        table.add_row(
            str(window["window_id"]),
            str(window["pid"]),
            window["app_name"],
            window["window_name"] or "-",
            f"x={pos['x']:.0f}, y={pos['y']:.0f}",
            f"{size['width']:.0f}x{size['height']:.0f}",
            str(window["layer"]),
            str(window["stack_order"]),
            f"{window['visible_percent']:.0f}%",
            str(window["display"]),
        )

    console.print(table)


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
