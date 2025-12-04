import os
import os.path
from pathlib import Path

import pytest

project_dir = str(Path(__file__).parent.parent)
tests_dir = os.path.join(project_dir, "tests")
test_data_dir = os.path.join(tests_dir, "data")


def pytest_collection_modifyitems(config, items):
    """Skip tests that require OpenAI API key if not set."""
    skip_openai = pytest.mark.skip(reason="OPENAI_API_KEY environment variable not set")
    if os.environ.get("OPENAI_API_KEY"):
        return

    # Test modules that directly or transitively import OpenAI-dependent code
    openai_dependent_tests = (
        "test_analyze",
        "test_ai_classifier",
        "test_capture",
        "test_workflow",
    )

    for item in items:
        # Skip tests in modules that import OpenAI at module level
        if any(test_name in item.nodeid for test_name in openai_dependent_tests):
            item.add_marker(skip_openai)
