import logging
from pathlib import Path

import astroid

from library_analyzer.processing.api.model import API
from library_analyzer.utils import ASTWalker

from ._ast_visitor import _AstVisitor
from ._file_filters import _is_test_file
from ._package_metadata import (
    distribution,
    distribution_version,
    package_files,
    package_root,
)
from .docstring_parsing import DocstringStyle, create_docstring_parser


def get_api(
    package_name: str,
    root: Path | None = None,
    docstring_style: DocstringStyle = DocstringStyle.PLAINTEXT,
) -> API:
    if root is None:
        root = package_root(package_name)
    dist = distribution(package_name) or ""
    dist_version = distribution_version(dist) or ""
    files = package_files(root)

    api = API(dist, package_name, dist_version)
    docstring_parser = create_docstring_parser(docstring_style)
    callable_visitor = _AstVisitor(docstring_parser, api)
    walker = ASTWalker(callable_visitor)

    for file in files:
        posix_path = Path(file).as_posix()
        logging.info(
            "Working on file {posix_path}",
            extra={"posix_path": posix_path},
        )

        if _is_test_file(posix_path):
            logging.info("Skipping test file")
            continue

        with Path(file).open(encoding="utf-8") as f:
            source = f.read()
            walker.walk(astroid.parse(source, module_name=__module_name(root, Path(file)), path=file))

    return callable_visitor.api


def __module_name(root: Path, file: Path) -> str:
    relative_path = file.relative_to(root.parent).as_posix()
    return str(relative_path).replace(".py", "").replace("/", ".")
