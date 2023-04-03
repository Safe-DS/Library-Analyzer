from pathlib import Path

from library_analyzer.processing.api import get_api
from library_analyzer.processing.api.docstring_parsing import DocstringStyle
from library_analyzer.processing.dependencies import get_dependencies

from ._read_and_write_file import _write_api_dependency_file, _write_api_file
from ._shared_constants import _API_KEY


def _run_api_command(
    package: str,
    src_dir_path: Path,
    out_dir_path: Path,
    docstring_style: DocstringStyle,
    result_dict: dict | None = None,
) -> None:
    api = get_api(package, src_dir_path, docstring_style)
    api_dependencies = get_dependencies(api)

    api_file_path = _write_api_file(api, out_dir_path)
    _write_api_dependency_file(api, api_dependencies, out_dir_path)

    if result_dict is not None:
        result_dict[_API_KEY] = api_file_path
