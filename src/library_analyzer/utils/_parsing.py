import textwrap

import astroid
from astroid.builder import AstroidBuilder


def parse_python_code(
    code: str,
    module_name: str = "",
    path: str = None,
    ast_builder: AstroidBuilder = None,
) -> astroid.Module:
    """Parse a source string in order to obtain an astroid AST from it.

    Parameters
    ----------
    code : str
        The code for the module.
    module_name : str
        The name for the module, if any
    path : str
        The path for the module
    ast_builder : AstroidBuilder
        The Astroid builder to use
    """
    if ast_builder is None:
        ast_builder = AstroidBuilder()

    code = textwrap.dedent(code)
    return ast_builder.string_build(code, modname=module_name, path=path)
