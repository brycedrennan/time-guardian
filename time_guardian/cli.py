import logging
from pathlib import Path

import typer
from mss import mss
from PIL import Image
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from time_guardian import __version__, analyze, capture, report
from time_guardian.monitors import render_monitor_arrangement_to_text
from time_guardian.perf import timer
from time_guardian.processes import get_all_processes
from time_guardian.windows import get_displays, get_window_info

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
def windows(
    show_all: bool = typer.Option(False, "--all", help="Show all windows instead of just layer 0 windows"),
):
    """Display information about visible windows on screen. By default, only shows layer 0 windows."""
    setup_logging()
    windows = get_window_info(all_layers=show_all)

    if not windows:
        if show_all:
            console.print("No visible windows found")
        else:
            console.print("No layer 0 windows found. Use --all to see all windows.")
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


@app.command()
def monitors(
    width: int = typer.Option(90, "--width", "-w", help="Target width in characters for the visual representation"),
):
    """Display information about connected monitors."""
    setup_logging()

    with mss() as sct:
        monitors = sct.monitors

        # Show total resolution first
        total = monitors[0]
        console.print(f"Total logical resolution: [bold cyan]{total['width']}x{total['height']}[/]\n")

        visual = render_monitor_arrangement_to_text(monitors, width)
        # Print the visual representation
        console.print("\n[bold]Monitor Arrangement:[/]")
        for row in visual:
            console.print(row)
        console.print()

        table = Table(title="Connected Monitors")
        table.add_column("Monitor", justify="right")
        table.add_column("Position")
        table.add_column("Size")
        table.add_column("Is Primary")

        for i, monitor in enumerate(monitors[1:], 1):  # Skip index 0 which represents "all monitors"
            table.add_row(
                str(i),
                f"x={monitor['left']}, y={monitor['top']}",
                f"{monitor['width']}x{monitor['height']}",
                "✓" if monitor.get("is_primary") else "✗",
            )

        console.print(table)


@app.command()
def processes():
    """Display information about all running processes."""
    setup_logging()
    processes = get_all_processes()

    if not processes:
        console.print("No processes found")
        return

    table = Table(title="Running Processes")
    table.add_column("PID", justify="right")
    table.add_column("Parent PID", justify="right")
    table.add_column("Status")
    table.add_column("Executable")
    table.add_column("Command")

    # Sort by executable path, using empty string for None to handle missing executables
    for proc in sorted(processes, key=lambda x: x.get("exe", "") or ""):
        cmdline = proc.get("cmdline")
        cmd_str = " ".join(cmdline) if cmdline else "-"

        table.add_row(
            str(proc["pid"]),
            str(proc["ppid"]),
            proc.get("status", "-"),
            proc.get("exe", "-") or "-",
            cmd_str,
        )

    console.print(table)


@app.command()
def perfcheck():
    """Check performance of various operations."""
    setup_logging()

    capture.screenshotter.cache_clear()
    with timer("Getting screenshotter (uncached)"):
        capture.screenshotter()
    with timer("Getting screenshotter (cached)"):
        capture.screenshotter()

    with timer("Getting all processes 1"):
        get_all_processes()
    with timer("Getting all processes 2"):
        get_all_processes()

    for i in range(5):
        with timer(f"Getting displays {i}"):
            get_displays()

    for i in range(5):
        with timer(f"Getting window info, all_layers=True, show_visibility=False, {i}"):
            get_window_info(all_layers=True, show_visibility=False)
    for i in range(5):
        with timer(f"Getting window info, all_layers=True, show_visibility=True, {i}"):
            get_window_info(all_layers=True, show_visibility=True)

    for i in range(5):
        with timer(f"Getting window info, all_layers=False, show_visibility=False, {i}"):
            get_window_info(all_layers=False, show_visibility=False)
    for i in range(5):
        with timer(f"Getting window info, all_layers=False, show_visibility=True, {i}"):
            get_window_info(all_layers=False, show_visibility=True)

    for i in range(5):
        with timer(f"get screenshot, {i}"):
            capture.capture_screenshot()


@app.command()
def screenshot(
    output: str = typer.Option("screenshot.png", "--output", "-o", help="Output file path for screenshot"),
):
    """Take a screenshot and save it to the specified path."""
    setup_logging()
    console.print(f"Taking screenshot and saving to [bold cyan]{output}[/][yellow]...[/]")
    with timer("capture_screenshot"):
        np_img = capture.capture_screenshot()

    # Convert BGR to RGB since capture_screenshot returns BGR format
    rgb_img = np_img[..., ::-1]

    with timer("saved image"):
        Image.fromarray(rgb_img).save(output, optimize=False)
    console.print(f"Screenshot saved to [bold cyan]{output}[/]")
    return 0


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
