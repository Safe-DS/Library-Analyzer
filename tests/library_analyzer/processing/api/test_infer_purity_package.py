from pathlib import Path

import pytest
from library_analyzer.cli._run_api import _run_api_command
from library_analyzer.processing.api.docstring_parsing import DocstringStyle
from library_analyzer.processing.api.purity_analysis.model import Impure, Pure


def test_run_api_command_safe_ds():
    _run_api_command("safe-ds",
                     Path(r"C:\Users\Lukas Radermacher\AppData\Local\pypoetry\Cache\virtualenvs\library-analyzer-FK1WveJV-py3.11\Lib\site-packages\safeds"),
                     Path(r"C:\Users\Lukas Radermacher\Desktop\Results"),
                     DocstringStyle.NUMPY
                     )


def test_run_api_command_small_module():
    _run_api_command("test_module",
                     Path(r"C:\Users\Lukas Radermacher\Desktop\Results\Tests"),
                     Path(r"C:\Users\Lukas Radermacher\Desktop\Results\Tests"),
                     DocstringStyle.NUMPY
                     )

# @pytest.mark.parametrize(
#     ("(package: str, src_dir_path: Path)", "expected_json"),
#     [
#         (
#             {
#                 "fun1.line2": Impure({
#                      "FileWrite.StringLiteral.stdout",
#                 }),
#                 "fun2.line6": Pure(),
#                 "fun3.line9": Impure({
#                     "FileWrite.StringLiteral.stdout",
#                 }),
#             },
#             {
#                 "NOPACKAGENAME": {
#                     "NOMODULENAME": {
#                         "fun1.line2": {
#                             "purity": "Impure",
#                             "reasons": {"FileWrite.StringLiteral.stdout"}
#                         },
#                         "fun2.line6": {
#                             "purity": "Pure",
#                             "reasons": {}
#                         },
#                         "fun3.line9": {
#                             "purity": "Impure",
#                             "reasons": {"FileWrite.StringLiteral.stdout"}
#                         },
#                     }
#                 }
#             }
#         )
#     ]
# )
# def test_to_json_file():
#     # api_purity = get_purity_results(package, src_dir_path)
#     # out_file_api_purity = out_dir_path.joinpath(f"{package}__api_purity.json")
#     # api_purity.to_json_file(out_file_api_purity)
#     pass
