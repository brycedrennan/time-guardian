from contextlib import contextmanager
from time import perf_counter


@contextmanager
def timer(description: str | None = None):
    """Context manager for measuring execution time of code blocks.

    Args:
        description: Optional description of what is being timed

    Yields:
        None

    Example:
        with timer("Processing data"):
            process_data()
    """
    start = perf_counter()
    try:
        yield
    finally:
        elapsed = (perf_counter() - start) * 1000
        if description:
            print(f"{description}: {elapsed:.1f} ms")
        else:
            print(f"Elapsed time: {elapsed:.1f} ms")
