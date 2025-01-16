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
        try:
            analysis_files = self.storage.get_analysis_results()
            if not analysis_files:
                logger.warning("No analysis results found")
                return

            activities = []
            for file in analysis_files:
                result = self.storage.get_analysis_by_timestamp(file)
                if result:
                    activities.append(result)

            with output_path.open("w") as f:
                f.write("Time Guardian Activity Report\n")
                f.write("=========================\n\n")
                f.write(f"Generated at: {datetime.now(timezone.utc).isoformat()}\n\n")

                if not activities:
                    f.write("No activities recorded.\n")
                    return

                for activity in activities:
                    f.write(f"Activity: {activity['classification']}\n\n")

                # Add AI summary
                ai_summary = self.summarize_activities(activities)
                f.write("\nAI Summary\n")
                f.write("==========\n\n")
                f.write(f"{ai_summary}\n")

            logger.info(f"Report generated: {output_path}")
        except OSError as e:
            logger.error(f"IO error generating report: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating report: {e}")
            raise

    def display_summary(self) -> None:
        """Display a summary of screen time activities.

        Raises:
            Exception: If there are issues retrieving or processing activities
        """
        try:
            analysis_files = self.storage.get_analysis_results()
            if not analysis_files:
                console.print("[yellow]No activities found.[/yellow]")
                return

            activities = []
            activity_counter = Counter()

            for file in analysis_files:
                result = self.storage.get_analysis_by_timestamp(file)
                if result:
                    activities.append(result)
                    activity_counter[result["classification"]] += 1

            if not activities:
                console.print("[yellow]No activities found.[/yellow]")
                return

            # Display activity counts
            table = Table(title="Activity Summary")
            table.add_column("Activity", style="green")
            table.add_column("Count", style="cyan", justify="right")

            for activity, count in activity_counter.most_common():
                table.add_row(activity, str(count))

            console.print(table)

            # Display AI summary
            ai_summary = self.summarize_activities(activities)
            if ai_summary:
                console.print("\n[bold]AI Summary[/bold]")
                console.print(ai_summary)

        except Exception as e:
            logger.error(f"Error displaying summary: {e}")
            raise

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
        except (openai.OpenAIError, ValueError, KeyError) as e:  # noqa: BLE001 # Catching API and data structure errors
            logger.error(f"Error summarizing activities: {e}")
            return "Unable to generate AI summary"


def generate_report(output_path: Path) -> None:
    """Generate a report and save it to the specified path.

    Args:
        output_path: Path to save the report
    """
    storage = Storage()
    report = Report(storage)
    report.generate_report(output_path)


def display_summary() -> None:
    """Display a summary of screen time activities."""
    storage = Storage()
    report = Report(storage)
    report.display_summary()
