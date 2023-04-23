import astroid
import pytest
from library_analyzer.processing.api.docstring_parsing import EpydocParser
from library_analyzer.processing.api.model import (
    ClassDocumentation,
    FunctionDocumentation,
    ParameterAssignment,
    ParameterDocumentation,
    ReturnDocumentation
)


@pytest.fixture()
def epydoc_parser() -> EpydocParser:
    return EpydocParser()


# language=python
class_with_documentation = '''
class C:
    """
    Lorem ipsum. Code::

        pass

    Dolor sit amet.
    """
'''

# language=python
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
    epydoc_parser: EpydocParser,
    python_code: str,
    expected_class_documentation: ClassDocumentation,
) -> None:
    node = astroid.extract_node(python_code)

    assert isinstance(node, astroid.ClassDef)
    assert epydoc_parser.get_class_documentation(node) == expected_class_documentation


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
    epydoc_parser: EpydocParser,
    python_code: str,
    expected_function_documentation: FunctionDocumentation,
) -> None:
    node = astroid.extract_node(python_code)

    assert isinstance(node, astroid.FunctionDef)
    assert epydoc_parser.get_function_documentation(node) == expected_function_documentation


# language=python
class_with_parameters = '''
# noinspection PyUnresolvedReferences,PyIncorrectDocstring
class C:
    """
    Lorem ipsum.

    Dolor sit amet.

    @param p: foo defaults to 1
    @type p: int
    """

    def __init__(self):
        pass
'''

# language=python
class_with_parameters_2 = '''
# noinspection PyUnresolvedReferences,PyIncorrectDocstring
class C:
    """
    Lorem ipsum.

    Dolor sit amet.

    @ivar p: foo defaults to 1
    @type p: int
    """

    def __init__(self):
        pass
'''

# language=python
function_with_parameters = '''
# noinspection PyUnresolvedReferences,PyIncorrectDocstring
def f():
    """
    Lorem ipsum.

    Dolor sit amet.

    Parameters
    ----------
    @param no_type_no_default: no type and no default
    @param type_no_default: type but no default
    @type type_no_default: int
    @param with_default: foo that defaults to 2
    @type with_default: int
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
            class_with_parameters_2,
            "p",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocumentation(
                type="int",
                default_value="1",
                description="foo defaults to 1",
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
    epydoc_parser: EpydocParser,
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
        epydoc_parser.get_parameter_documentation(node, parameter_name, parameter_assigned_by)
        == expected_parameter_documentation
    )

# language=python
function_with_return_value_and_type = '''
# noinspection PyUnresolvedReferences,PyIncorrectDocstring
def f():
    """
    Lorem ipsum.

    Dolor sit amet.

    @return: return value
    @rtype: float
    """

    pass
'''

# language=python
function_with_return_value_no_type = '''
# noinspection PyUnresolvedReferences,PyIncorrectDocstring
def f():
    """
    Lorem ipsum.

    Dolor sit amet.

    @return: return value
    """

    pass
'''

# language=python
function_without_return_value = '''
# noinspection PyUnresolvedReferences,PyIncorrectDocstring
def f():
    """
    Lorem ipsum.

    Dolor sit amet.
    """

    pass
'''


@pytest.mark.parametrize(
    ("python_code", "expected_return_documentation"),
    [
        (
            function_with_return_value_and_type,
            ParameterDocumentation(type="", description=""),
        ),
        (
            function_with_return_value_no_type,
            ParameterDocumentation(type="", description=""),
        ),
        (
            function_without_return_value,
            ParameterDocumentation(type="", description="")
        ),
    ],
    ids=[
        "existing return value and type",
        "existing return value no type",
        "function without return value"
    ],
)
def test_get_return_documentation(
    epydoc_parser: EpydocParser,
    python_code: str,
    expected_return_documentation: ParameterDocumentation,
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
        epydoc_parser.get_return_documentation(node)
        == expected_return_documentation
    )
