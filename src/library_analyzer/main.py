"""The entrypoint to the program."""

import time

from library_analyzer.cli import cli


def main() -> None:
    """The entrypoint to the program."""
    start_time = time.time()

    cli()

    print("\n============================================================")  # noqa: T201
    print(f"Program ran in {time.time() - start_time}s")  # noqa: T201
