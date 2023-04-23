# Todo Class with Attributes
import astroid
import pytest
from library_analyzer.processing.api.docstring_parsing import NumpyDocParser
from library_analyzer.processing.api.model import (
    ClassDocumentation,
    FunctionDocumentation,
    ParameterAssignment,
    ParameterDocumentation,
    ReturnDocumentation,
    AttributeDocumentation,
    AttributeAssignment
)


@pytest.fixture()
def numpydoc_parser() -> NumpyDocParser:
    return NumpyDocParser()


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
    numpydoc_parser: NumpyDocParser,
    python_code: str,
    expected_class_documentation: ClassDocumentation,
) -> None:
    node = astroid.extract_node(python_code)

    assert isinstance(node, astroid.ClassDef)
    assert numpydoc_parser.get_class_documentation(node) == expected_class_documentation


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
            FunctionDocumentation(description=""),
        ),
    ],
    ids=[
        "function with documentation",
        "function without documentation",
    ],
)
def test_get_function_documentation(
    numpydoc_parser: NumpyDocParser,
    python_code: str,
    expected_function_documentation: FunctionDocumentation,
) -> None:
    node = astroid.extract_node(python_code)

    assert isinstance(node, astroid.FunctionDef)
    assert numpydoc_parser.get_function_documentation(node) == expected_function_documentation


# language=python
class_with_parameters = '''
# noinspection PyUnresolvedReferences,PyIncorrectDocstring
class C:
    """
    Lorem ipsum.

    Dolor sit amet.

    Parameters
    ----------
    p : int, default=1
        foo
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
    no_type_no_default
        foo: no_type_no_default. Code::

            pass
    type_no_default : int
        foo: type_no_default
    optional_unknown_default : int, optional
        foo: optional_unknown_default
    with_default_syntax_1 : int, default 1
        foo: with_default_syntax_1
    with_default_syntax_2 : int, default: 2
        foo: with_default_syntax_2
    with_default_syntax_3 : int, default=3
        foo: with_default_syntax_3
    grouped_parameter_1, grouped_parameter_2 : int, default=4
        foo: grouped_parameter_1 and grouped_parameter_2
    *args : int
        foo: *args
    **kwargs : int
        foo: **kwargs
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
                description="foo",
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
                description="foo: no_type_no_default. Code::\n\n    pass",
            ),
        ),
        (
            function_with_parameters,
            "type_no_default",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocumentation(
                type="int",
                default_value="",
                description="foo: type_no_default",
            ),
        ),
        (
            function_with_parameters,
            "optional_unknown_default",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocumentation(
                type="int",
                default_value="",
                description="foo: optional_unknown_default",
            ),
        ),
        (
            function_with_parameters,
            "with_default_syntax_1",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocumentation(
                type="int",
                default_value="1",
                description="foo: with_default_syntax_1",
            ),
        ),
        (
            function_with_parameters,
            "with_default_syntax_2",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocumentation(type="int", default_value="2", description="foo: with_default_syntax_2"),
        ),
        (
            function_with_parameters,
            "with_default_syntax_3",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocumentation(type="int", default_value="3", description="foo: with_default_syntax_3"),
        ),
        (
            function_with_parameters,
            "grouped_parameter_1",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocumentation(
                type="int",
                default_value="4",
                description="foo: grouped_parameter_1 and grouped_parameter_2",
            ),
        ),
        (
            function_with_parameters,
            "grouped_parameter_2",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocumentation(
                type="int",
                default_value="4",
                description="foo: grouped_parameter_1 and grouped_parameter_2",
            ),
        ),
        (
            function_with_parameters,
            "args",
            ParameterAssignment.POSITIONAL_VARARG,
            ParameterDocumentation(
                type="int",
                default_value="",
                description="foo: *args",
            ),
        ),
        (
            function_with_parameters,
            "kwargs",
            ParameterAssignment.NAMED_VARARG,
            ParameterDocumentation(
                type="int",
                default_value="",
                description="foo: **kwargs",
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
        "function parameter with optional unknown default",
        "function parameter with default syntax 1 (just space)",
        "function parameter with default syntax 2 (colon)",
        "function parameter with default syntax 3 (equals)",
        "function parameter with grouped parameters 1",
        "function parameter with grouped parameters 2",
        "function parameter with positional vararg",
        "function parameter with named vararg",
        "missing function parameter",
    ],
)
def test_get_parameter_documentation(
    numpydoc_parser: NumpyDocParser,
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
        numpydoc_parser.get_parameter_documentation(node, parameter_name, parameter_assigned_by)
        == expected_parameter_documentation
    )


# language=python
class_with_attributes = '''
# noinspection PyUnresolvedReferences,PyIncorrectDocstring
class C:
    """
    Lorem ipsum.

    Dolor sit amet.

    Attributes
    ----------
    p : int, default=1
        foo
    """

    def __init__(self):
        pass
'''


@pytest.mark.parametrize(
    ("python_code", "attribute_name", "attribute_assigned_by", "expected_attribute_documentation"),
    [
        (
            class_with_attributes,
            "p",
            AttributeAssignment.POSITION_OR_NAME,
            AttributeDocumentation(
                type="int",
                default_value="1",
                description="foo",
            ),
        ),
        (
            class_with_attributes,
            "missing",
            AttributeAssignment.POSITION_OR_NAME,
            AttributeDocumentation(
                type="",
                default_value="",
                description="",
            ),
        )
    ],
    ids=[
        "existing class attribute",
        "missing class attribute"
    ],
)
def test_get_class_attribute_documentation(
    numpydoc_parser: NumpyDocParser,
    python_code: str,
    attribute_name: str,
    attribute_assigned_by: AttributeAssignment,
    expected_attribute_documentation: AttributeDocumentation,
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
        numpydoc_parser.get_parameter_documentation(node, attribute_name, attribute_assigned_by)
        == expected_attribute_documentation
    )


# language=python
function_with_return_value_and_type = '''
# noinspection PyUnresolvedReferences,PyIncorrectDocstring
def f():
    """
    Lorem ipsum.

    Dolor sit amet.

    Returns
    -------
    int
        this will be the return value
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

    Returns
    -------
    int
        this will be the return value
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
    numpydoc_parser: NumpyDocParser,
    python_code: str,
    expected_return_documentation: ReturnDocumentation,
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
        numpydoc_parser.get_return_documentation(node)
        == expected_return_documentation
    )
