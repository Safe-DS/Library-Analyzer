from pathlib import Path

from library_analyzer.processing.api import get_api
from library_analyzer.processing.api.docstring_parsing import DocstringStyle
from library_analyzer.processing.dependencies import get_dependencies

from ._read_and_write_file import _write_api_dependency_file, _write_api_file


def _run_api_command(
    package: str,
    src_dir_path: Path,
    out_dir_path: Path,
    docstring_style: DocstringStyle,
) -> None:
    """
    List the API of a package.

    Parameters
    ----------
    package : str
        The name of the package.
    src_dir_path : Path
        The path to the source directory of the package.
    out_dir_path : Path
        The path to the output directory.
    docstring_style : DocstringStyle
        The style of docstrings to use.
    """
    api = get_api(package, src_dir_path, docstring_style)
    api_dependencies = get_dependencies(api)

    _write_api_file(api, out_dir_path)
    _write_api_dependency_file(api, api_dependencies, out_dir_path)
