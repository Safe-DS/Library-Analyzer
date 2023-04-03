"""Parsing docstrings into a common format."""

from ._abstract_documentation_parser import AbstractDocstringParser
from ._create_docstring_parser import create_docstring_parser
from ._docstring_style import DocstringStyle
from ._epydoc_parser import EpydocParser
from ._helpers import get_description, get_full_docstring
from ._numpydoc_parser import NumpyDocParser
from ._plaintext_docstring_parser import PlaintextDocstringParser

__all__ = [
    "AbstractDocstringParser",
    "create_docstring_parser",
    "DocstringStyle",
    "EpydocParser",
    "get_description",
    "get_full_docstring",
    "NumpyDocParser",
    "PlaintextDocstringParser",
]
