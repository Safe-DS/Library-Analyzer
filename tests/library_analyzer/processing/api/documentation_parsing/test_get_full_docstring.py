import astroid
import pytest
from library_analyzer.processing.api.documentation_parsing import get_full_docstring

class_with_multi_line_documentation = '''
class C:
    """
    Lorem ipsum.

    Dolor sit amet.
    """

    pass
'''

class_with_single_line_documentation = '''
class C:
    """Lorem ipsum."""

    pass
'''

class_without_documentation = """
class C:
    pass
"""

function_with_multi_line_documentation = '''
def f():
    """
    Lorem ipsum.

    Dolor sit amet.
    """

    pass
'''

function_with_single_line_documentation = '''
def f():
    """Lorem ipsum."""

    pass
'''

function_without_documentation = """
def f():
    pass
"""


@pytest.mark.parametrize(
    ("python_code", "expected_docstring"),
    [
        (class_with_multi_line_documentation, "Lorem ipsum.\n\nDolor sit amet."),
        (class_with_single_line_documentation, "Lorem ipsum."),
        (class_without_documentation, ""),
        (function_with_multi_line_documentation, "Lorem ipsum.\n\nDolor sit amet."),
        (function_with_single_line_documentation, "Lorem ipsum."),
        (function_without_documentation, ""),
    ],
    ids=[
        "class with multi line documentation",
        "class with single line documentation",
        "class without documentation",
        "function with multi line documentation",
        "function with single line documentation",
        "function without documentation",
    ],
)
def test_get_full_docstring(python_code: str, expected_docstring: str) -> None:
    node = astroid.extract_node(python_code)

    assert isinstance(node, astroid.ClassDef | astroid.FunctionDef)
    assert get_full_docstring(node) == expected_docstring
