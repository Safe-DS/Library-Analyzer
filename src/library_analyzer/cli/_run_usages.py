from pathlib import Path

from library_analyzer.cli._read_and_write_file import _write_usages_file
from library_analyzer.processing.usages import find_usages


def _run_usages_command(
    package: str,
    client_dir_path: Path,
    out_dir_path: Path,
    n_processes: int,
    batch_size: int,
) -> None:
    """
    Find usages of API elements.

    Parameters
    ----------
    package : str
        The name of the package.
    client_dir_path : Path
        The path to the directory with the client code
    out_dir_path : Path
        The path to the output directory.
    n_processes : int
        The number of processes to use.
    batch_size : int
        The batch size to use.
    """
    usages = find_usages(package, client_dir_path, n_processes, batch_size)
    _write_usages_file(usages, package, out_dir_path)
