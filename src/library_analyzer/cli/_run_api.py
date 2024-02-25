from pathlib import Path

from library_analyzer.processing.api import get_api
from library_analyzer.processing.api.docstring_parsing import DocstringStyle
# from library_analyzer.processing.api.purity_analysis import get_purity_results
from library_analyzer.processing.dependencies import get_dependencies


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
        The style of docstrings that is used in the library.
    """
    api = get_api(package, src_dir_path, docstring_style)
    out_file_api = out_dir_path.joinpath(f"{package}__api.json")
    api.to_json_file(out_file_api)

    api_dependencies = get_dependencies(api)
    out_file_api_dependencies = out_dir_path.joinpath(f"{package}__api_dependencies.json")
    api_dependencies.to_json_file(out_file_api_dependencies)

    # api_purity = get_purity_results(src_dir_path)
    # out_file_api_purity = out_dir_path.joinpath(f"{package}__api_purity.json")
    # api_purity.to_json_file(out_file_api_purity)
