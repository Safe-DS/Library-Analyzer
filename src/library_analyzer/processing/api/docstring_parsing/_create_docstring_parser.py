from __future__ import annotations

from typing import TYPE_CHECKING

from ._docstring_style import DocstringStyle
from ._epydoc_parser import EpydocParser
from ._numpydoc_parser import NumpyDocParser
from ._plaintext_docstring_parser import PlaintextDocstringParser

if TYPE_CHECKING:
    from ._abstract_docstring_parser import AbstractDocstringParser


def create_docstring_parser(style: DocstringStyle) -> AbstractDocstringParser:
    if style == DocstringStyle.NUMPY:
        return NumpyDocParser()
    if style == DocstringStyle.EPYDOC:
        return EpydocParser()
    else:  # TODO: cover other cases
        return PlaintextDocstringParser()
