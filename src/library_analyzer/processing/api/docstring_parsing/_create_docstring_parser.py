from ._numpydoc_parser import NumpyDocParser
from ._plaintext_docstring_parser import PlaintextDocstringParser
from ._docstring_style import DocstringStyle
from ._epydoc_parser import EpydocParser


def create_docstring_parser(style: DocstringStyle):
    if style == DocstringStyle.NUMPY:
        return NumpyDocParser()
    if style == DocstringStyle.EPYDOC:
        return EpydocParser()
    else:  # TODO: cover other cases
        return PlaintextDocstringParser()
