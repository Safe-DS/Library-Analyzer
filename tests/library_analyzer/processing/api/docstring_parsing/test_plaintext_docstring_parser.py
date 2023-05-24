import astroid
import pytest
from library_analyzer.processing.api.docstring_parsing import (
    PlaintextDocstringParser,
)
from library_analyzer.processing.api.model import (
    ClassDocstring,
    FunctionDocstring,
    ParameterAssignment,
    ParameterDocstring,
)


@pytest.fixture()
def plaintext_docstring_parser() -> PlaintextDocstringParser:
    return PlaintextDocstringParser()


class_with_documentation = '''
class C:
    """
    Lorem ipsum.

    Dolor sit amet.
    """

    def __init__(self, p: int):
        pass
'''

class_without_documentation = """
class C:
    pass
"""


@pytest.mark.parametrize(
    ("python_code", "expected_class_documentation"),
    [
        (
            class_with_documentation,
            ClassDocstring(
                description="Lorem ipsum.\n\nDolor sit amet.",
                full_docstring="Lorem ipsum.\n\nDolor sit amet.",
            ),
        ),
        (
            class_without_documentation,
            ClassDocstring(
                description="",
                full_docstring="",
            ),
        ),
    ],
    ids=[
        "class with documentation",
        "class without documentation",
    ],
)
def test_get_class_documentation(
    plaintext_docstring_parser: PlaintextDocstringParser,
    python_code: str,
    expected_class_documentation: ClassDocstring,
) -> None:
    node = astroid.extract_node(python_code)

    assert isinstance(node, astroid.ClassDef)
    assert plaintext_docstring_parser.get_class_documentation(node) == expected_class_documentation


function_with_documentation = '''
def f(p: int):
    """
    Lorem ipsum.

    Dolor sit amet.
    """

    pass
'''

function_without_documentation = """
def f(p: int):
    pass
"""


@pytest.mark.parametrize(
    ("python_code", "expected_function_documentation"),
    [
        (
            function_with_documentation,
            FunctionDocstring(
                description="Lorem ipsum.\n\nDolor sit amet.",
                full_docstring="Lorem ipsum.\n\nDolor sit amet.",
            ),
        ),
        (
            function_without_documentation,
            FunctionDocstring(description=""),
        ),
    ],
    ids=[
        "function with documentation",
        "function without documentation",
    ],
)
def test_get_function_documentation(
    plaintext_docstring_parser: PlaintextDocstringParser,
    python_code: str,
    expected_function_documentation: FunctionDocstring,
) -> None:
    node = astroid.extract_node(python_code)

    assert isinstance(node, astroid.FunctionDef)
    assert plaintext_docstring_parser.get_function_documentation(node) == expected_function_documentation


@pytest.mark.parametrize(
    ("python_code", "parameter_name", "expected_parameter_documentation"),
    [
        (
            function_with_documentation,
            "p",
            ParameterDocstring(
                type="",
                default_value="",
                description="",
            ),
        ),
        (
            function_without_documentation,
            "p",
            ParameterDocstring(
                type="",
                default_value="",
                description="",
            ),
        ),
    ],
    ids=[
        "function with documentation",
        "function without documentation",
    ],
)
def test_get_parameter_documentation(
    plaintext_docstring_parser: PlaintextDocstringParser,
    python_code: str,
    parameter_name: str,
    expected_parameter_documentation: ParameterDocstring,
) -> None:
    node = astroid.extract_node(python_code)
    assert isinstance(node, astroid.FunctionDef)
    assert (
        plaintext_docstring_parser.get_parameter_documentation(
            node,
            parameter_name,
            ParameterAssignment.POSITION_OR_NAME,
        )
        == expected_parameter_documentation
    )
