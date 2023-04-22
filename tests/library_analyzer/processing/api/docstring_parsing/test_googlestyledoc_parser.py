# Todo Function with return value
import astroid
import pytest
from library_analyzer.processing.api.docstring_parsing import GooglestyledocParser
from library_analyzer.processing.api.model import (
    ClassDocumentation,
    FunctionDocumentation,
    ParameterAssignment,
    ParameterDocumentation,
)


@pytest.fixture()
def googlestyledoc_parser() -> GooglestyledocParser:
    return GooglestyledocParser()


class_with_documentation = '''
class C:
    """
    Lorem ipsum. Code::

        pass

    Dolor sit amet.
    """
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
            ClassDocumentation(
                description="Lorem ipsum. Code::\n\npass\n\nDolor sit amet.",
                full_docstring="Lorem ipsum. Code::\n\n    pass\n\nDolor sit amet.",
            ),
        ),
        (
            class_without_documentation,
            ClassDocumentation(
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
    googlestyledoc_parser: GooglestyledocParser,
    python_code: str,
    expected_class_documentation: ClassDocumentation,
) -> None:
    node = astroid.extract_node(python_code)

    assert isinstance(node, astroid.ClassDef)
    assert googlestyledoc_parser.get_class_documentation(node) == expected_class_documentation


# language=python
function_with_documentation = '''
def f():
    """
    Lorem ipsum. Code::

        pass

    Dolor sit amet.
    """

    pass
'''

# language=python
function_without_documentation = """
def f():
    pass
"""


@pytest.mark.parametrize(
    ("python_code", "expected_function_documentation"),
    [
        (
            function_with_documentation,
            FunctionDocumentation(
                description="Lorem ipsum. Code::\n\npass\n\nDolor sit amet.",
                full_docstring="Lorem ipsum. Code::\n\n    pass\n\nDolor sit amet.",
            ),
        ),
        (
            function_without_documentation,
            FunctionDocumentation(
                description="",
                full_docstring="",
            ),
        ),
    ],
    ids=[
        "function with documentation",
        "function without documentation",
    ],
)
def test_get_function_documentation(
    googlestyledoc_parser: GooglestyledocParser,
    python_code: str,
    expected_function_documentation: FunctionDocumentation,
) -> None:
    node = astroid.extract_node(python_code)

    assert isinstance(node, astroid.FunctionDef)
    assert googlestyledoc_parser.get_function_documentation(node) == expected_function_documentation


# language=python
class_with_parameters = '''
# noinspection PyUnresolvedReferences,PyIncorrectDocstring
class C:
    """Lorem ipsum.

    Dolor sit amet.

    Attributes:
        p (int): foo defaults to 1
    """

    def __init__(self):
        pass
'''

# language=python
function_with_parameters = '''
# noinspection PyUnresolvedReferences,PyIncorrectDocstring
def f():
    """Lorem ipsum.

    Dolor sit amet.

    Args:
        no_type_no_default: no type and no default
        type_no_default (int): type but no default
        with_default (int): foo that defaults to 2

    Returns:
        float: this will be the return value
    """

    pass
'''


@pytest.mark.parametrize(
    ("python_code", "parameter_name", "parameter_assigned_by", "expected_parameter_documentation"),
    [
        (
            class_with_parameters,
            "p",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocumentation(
                type="int",
                default_value="1",
                description="foo defaults to 1",
            ),
        ),
        (
            class_with_parameters,
            "missing",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocumentation(
                type="",
                default_value="",
                description="",
            ),
        ),
        (
            function_with_parameters,
            "no_type_no_default",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocumentation(
                type="",
                default_value="",
                description="no type and no default",
            ),
        ),
        (
            function_with_parameters,
            "type_no_default",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocumentation(
                type="int",
                default_value="",
                description="type but no default",
            ),
        ),
        (
            function_with_parameters,
            "with_default",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocumentation(
                type="int",
                default_value="2",
                description="foo that defaults to 2",
            ),
        ),
        (
            function_with_parameters,
            "missing",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocumentation(type="", default_value="", description=""),
        ),
    ],
    ids=[
        "existing class parameter",
        "missing class parameter",
        "function parameter with no type and no default",
        "function parameter with type and no default",
        "function parameter with default",
        "missing function parameter",
    ],
)
def test_get_parameter_documentation(
    googlestyledoc_parser: GooglestyledocParser,
    python_code: str,
    parameter_name: str,
    parameter_assigned_by: ParameterAssignment,
    expected_parameter_documentation: ParameterDocumentation,
) -> None:
    node = astroid.extract_node(python_code)
    assert isinstance(node, astroid.ClassDef | astroid.FunctionDef)

    # Find the constructor
    if isinstance(node, astroid.ClassDef):
        for method in node.mymethods():
            if method.name == "__init__":
                node = method

    assert isinstance(node, astroid.FunctionDef)
    assert (
        googlestyledoc_parser.get_parameter_documentation(node, parameter_name, parameter_assigned_by)
        == expected_parameter_documentation
    )
