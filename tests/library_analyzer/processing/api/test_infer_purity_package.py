from pathlib import Path

from library_analyzer.cli._run_api import _run_api_command
from library_analyzer.processing.api.docstring_parsing import DocstringStyle


# TODO: change these to data folder
def test_run_api_command_safe_ds() -> None:
    _run_api_command("safe-ds",
                     Path(r"C:\Users\Lukas Radermacher\AppData\Local\pypoetry\Cache\virtualenvs\library-analyzer-FK1WveJV-py3.11\Lib\site-packages\safeds"),
                     Path(r"C:\Users\Lukas Radermacher\Desktop\Results"),
                     DocstringStyle.NUMPY
                     )


def test_run_api_command_small_module() -> None:
    _run_api_command("test_module",
                     Path(r"C:\Users\Lukas Radermacher\Desktop\Results\Tests"),
                     Path(r"C:\Users\Lukas Radermacher\Desktop\Results\Tests"),
                     DocstringStyle.NUMPY
                     )
