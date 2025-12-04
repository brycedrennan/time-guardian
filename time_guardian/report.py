import logging
from collections import Counter
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import openai
from rich.console import Console
from rich.table import Table

from time_guardian.ai_classifier import AIClassifier
from time_guardian.storage import Storage

logger = logging.getLogger(__name__)
console = Console()

STORAGE_DIR = Path.home() / ".time-guardian"


class Report:
    """Handles report generation and summary display for Time Guardian."""

    def __init__(self, storage: Storage):
        """Initialize the report generator.

        Args:
            storage: Storage instance for accessing analysis results
        """
        self.storage = storage
        self.ai_classifier = AIClassifier()

    def generate_report(self, output_path: Path) -> None:
        """Generate a detailed report of activities and save it to the specified path.

        Args:
            output_path: Path to save the report

        Raises:
            OSError: If there are issues writing to the output file
        """
        activities = self.storage.get_all_window_analyses()
        if not activities:
            logger.warning("No analysis results found")
            console.print("[yellow]No analysis results found.[/yellow]")
            return

        # Group activities by app
        app_activities: dict[str, list[dict]] = {}
        for activity in activities:
            app_name = activity.get("app_name", "Unknown")
            if app_name not in app_activities:
                app_activities[app_name] = []
            app_activities[app_name].append(activity)

        with output_path.open("w") as f:
            f.write("Time Guardian Activity Report\n")
            f.write("=============================\n\n")
            f.write(f"Generated at: {datetime.now(timezone.utc).isoformat()}\n")
            f.write(f"Total activities analyzed: {len(activities)}\n\n")

            # Summary by app
            f.write("Activity by Application\n")
            f.write("-----------------------\n\n")
            for app_name, app_acts in sorted(app_activities.items(), key=lambda x: -len(x[1])):
                f.write(f"[{app_name}] - {len(app_acts)} events\n")
                for act in app_acts[:5]:  # Show first 5 per app
                    f.write(f"  • {act.get('datetime', 'Unknown time')}: {act.get('classification', 'No description')}\n")
                if len(app_acts) > 5:
                    f.write(f"  ... and {len(app_acts) - 5} more\n")
                f.write("\n")

            # Full timeline
            f.write("\nFull Timeline\n")
            f.write("-------------\n\n")
            for activity in activities:
                dt = activity.get("datetime", "Unknown")
                app = activity.get("app_name", "Unknown")
                window = activity.get("window_name", "")
                classification = activity.get("classification", "No description")
                window_info = f" - {window}" if window else ""
                f.write(f"[{dt}] {app}{window_info}\n")
                f.write(f"    {classification}\n\n")

            # Add AI summary
            ai_summary = self.summarize_activities(activities)
            f.write("\nAI Summary\n")
            f.write("==========\n\n")
            f.write(f"{ai_summary}\n")

        logger.info(f"Report generated: {output_path}")
        console.print(f"Report saved to [bold cyan]{output_path}[/bold cyan]")

    def display_summary(self) -> None:
        """Display a summary of screen time activities."""
        activities = self.storage.get_all_window_analyses()
        if not activities:
            console.print("[yellow]No activities found. Run 'time-guardian track' first.[/yellow]")
            return

        # Count by app
        app_counter = Counter(a.get("app_name", "Unknown") for a in activities)

        # Display app summary table
        table = Table(title=f"Activity Summary ({len(activities)} total events)")
        table.add_column("Application", style="green")
        table.add_column("Events", style="cyan", justify="right")

        for app, count in app_counter.most_common():
            table.add_row(app, str(count))

        console.print(table)

        # Show recent activities
        console.print("\n[bold]Recent Activity:[/bold]")
        for activity in activities[-10:]:
            dt = activity.get("datetime", "Unknown")[:19]  # Trim to readable format
            app = activity.get("app_name", "Unknown")
            classification = activity.get("classification", "No description")
            # Truncate long classifications
            if len(classification) > 80:
                classification = classification[:77] + "..."
            console.print(f"  [dim]{dt}[/dim] [green]{app}[/green]: {classification}")

        # Display AI summary
        if len(activities) >= 3:
            console.print("\n[bold]AI Summary:[/bold]")
            ai_summary = self.summarize_activities(activities)
            console.print(ai_summary)

    def summarize_activities(self, activities: Sequence[dict[str, Any]]) -> str:
        """Generate an AI-powered summary of activities.

        Args:
            activities: List of activity dictionaries with descriptions

        Returns:
            str: AI-generated summary of activities
        """
        if not activities:
            return "No activities to summarize."

        try:
            return self.ai_classifier.summarize_activity(activities)
        except (openai.OpenAIError, ValueError, KeyError) as e:
            logger.error(f"Error summarizing activities: {e}")
            return "Unable to generate AI summary"


def generate_report(output_path: Path) -> None:
    """Generate a report and save it to the specified path.

    Args:
        output_path: Path to save the report
    """
    storage = Storage(STORAGE_DIR)
    report = Report(storage)
    report.generate_report(output_path)


def display_summary(report_path: Path | None = None) -> None:
    """Display a summary of screen time activities.
    
    Args:
        report_path: Ignored (kept for CLI compatibility). Summary is generated from stored analyses.
    """
    storage = Storage(STORAGE_DIR)
    report = Report(storage)
    report.display_summary()
