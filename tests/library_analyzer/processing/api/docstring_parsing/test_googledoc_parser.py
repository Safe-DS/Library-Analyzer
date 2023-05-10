import astroid
import pytest
from library_analyzer.processing.api.docstring_parsing import GoogleDocParser
from library_analyzer.processing.api.model import (
    AttributeAssignment,
    AttributeDocstring,
    ClassDocstring,
    FunctionDocstring,
    ParameterAssignment,
    ParameterDocstring,
    ResultDocstring
)


@pytest.fixture()
def googlestyledoc_parser() -> GoogleDocParser:
    return GoogleDocParser()


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
            ClassDocstring(
                description="Lorem ipsum. Code::\n\npass\n\nDolor sit amet.",
                full_docstring="Lorem ipsum. Code::\n\n    pass\n\nDolor sit amet.",
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
    googlestyledoc_parser: GoogleDocParser,
    python_code: str,
    expected_class_documentation: ClassDocstring,
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
            FunctionDocstring(
                description="Lorem ipsum. Code::\n\npass\n\nDolor sit amet.",
                full_docstring="Lorem ipsum. Code::\n\n    pass\n\nDolor sit amet.",
            ),
        ),
        (
            function_without_documentation,
            FunctionDocstring(
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
    googlestyledoc_parser: GoogleDocParser,
    python_code: str,
    expected_function_documentation: FunctionDocstring,
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

    Args:
        p (int): foo. Defaults to 1.
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
        no_type_no_default: no type and no default.
        type_no_default (int): type but no default.
        with_default (int): foo. Defaults to 2.
        *args (int): foo: *args
        **kwargs (int): foo: **kwargs
    """

    pass
'''

# language=python
function_with_attributes_and_parameters = '''
# noinspection PyUnresolvedReferences,PyIncorrectDocstring
def f():
    """Lorem ipsum.

    Dolor sit amet.

    Attributes:
        p (int): foo. Defaults to 2.

    Args:
        q (int): foo. Defaults to 2.

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
            ParameterDocstring(
                type="int",
                default_value="1",
                description="foo. Defaults to 1.",
            ),
        ),
        (
            class_with_parameters,
            "missing",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocstring(
                type="",
                default_value="",
                description="",
            ),
        ),
        (
            function_with_parameters,
            "no_type_no_default",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocstring(
                type="",
                default_value="",
                description="no type and no default.",
            ),
        ),
        (
            function_with_parameters,
            "type_no_default",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocstring(
                type="int",
                default_value="",
                description="type but no default.",
            ),
        ),
        (
            function_with_parameters,
            "with_default",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocstring(
                type="int",
                default_value="2",
                description="foo. Defaults to 2.",
            ),
        ),
        (
            function_with_parameters,
            "*args",
            ParameterAssignment.POSITIONAL_VARARG,
            ParameterDocstring(
                type="int",
                default_value="",
                description="foo: *args",
            ),
        ),
        (
            function_with_parameters,
            "**kwargs",
            ParameterAssignment.NAMED_VARARG,
            ParameterDocstring(
                type="int",
                default_value="",
                description="foo: **kwargs",
            ),
        ),
        (
            function_with_parameters,
            "missing",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocstring(type="", default_value="", description=""),
        ),
        (
            function_with_attributes_and_parameters,
            "q",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocstring(
                type="int",
                default_value="2",
                description="foo. Defaults to 2.",
            ),
        ),
        (
            function_with_attributes_and_parameters,
            "p",
            ParameterAssignment.POSITION_OR_NAME,
            ParameterDocstring(
                type="",
                default_value="",
                description="",
            ),
        )
    ],
    ids=[
        "existing class parameter",
        "missing class parameter",
        "function parameter with no type and no default",
        "function parameter with type and no default",
        "function parameter with default",
        "function parameter with positional vararg",
        "function parameter with named vararg",
        "missing function parameter",
        "function with attributes and parameters existing parameter",
        "function with attributes and parameters missing parameter"
    ],
)
def test_get_parameter_documentation(
    googlestyledoc_parser: GoogleDocParser,
    python_code: str,
    parameter_name: str,
    parameter_assigned_by: ParameterAssignment,
    expected_parameter_documentation: ParameterDocstring,
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


# language=python
class_with_attributes = '''
# noinspection PyUnresolvedReferences,PyIncorrectDocstring
class C:
    """Lorem ipsum.

    Dolor sit amet.

    Attributes:
        p (int): foo. Defaults to 1.
    """

    def __init__(self):
        pass
'''

# language=python
function_with_attributes = '''
# noinspection PyUnresolvedReferences,PyIncorrectDocstring
def f():
    """Lorem ipsum.

    Dolor sit amet.

    Attributes:
        no_type_no_default: no type and no default.
        type_no_default (int): type but no default.
        with_default (int): foo. Defaults to 2.
        *args (int): foo: *args
        **kwargs (int): foo: **kwargs
    """

    pass
'''

@pytest.mark.parametrize(
    ("python_code", "attribute_name", "attribute_assigned_by", "expected_attribute_documentation"),
    [
        (
            class_with_attributes,
            "p",
            AttributeAssignment.POSITION_OR_NAME,
            AttributeDocstring(
                type="int",
                default_value="1",
                description="foo. Defaults to 1.",
            ),
        ),
        (
            class_with_attributes,
            "missing",
            AttributeAssignment.POSITION_OR_NAME,
            AttributeDocstring(
                type="",
                default_value="",
                description="",
            ),
        ),
        (
            function_with_attributes,
            "no_type_no_default",
            AttributeAssignment.POSITION_OR_NAME,
            AttributeDocstring(
                type="",
                default_value="",
                description="no type and no default.",
            ),
        ),
        (
            function_with_attributes,
            "type_no_default",
            AttributeAssignment.POSITION_OR_NAME,
            AttributeDocstring(
                type="int",
                default_value="",
                description="type but no default.",
            ),
        ),
        (
            function_with_attributes,
            "with_default",
            AttributeAssignment.POSITION_OR_NAME,
            AttributeDocstring(
                type="int",
                default_value="2",
                description="foo. Defaults to 2.",
            ),
        ),
        (
            function_with_attributes,
            "*args",
            AttributeAssignment.POSITIONAL_VARARG,
            AttributeDocstring(
                type="int",
                default_value="",
                description="foo: *args",
            ),
        ),
        (
            function_with_attributes,
            "**kwargs",
            AttributeAssignment.NAMED_VARARG,
            AttributeDocstring(
                type="int",
                default_value="",
                description="foo: **kwargs",
            ),
        ),
        (
            function_with_attributes,
            "missing",
            AttributeAssignment.POSITION_OR_NAME,
            AttributeDocstring(type="", default_value="", description=""),
        ),
        (
            function_with_attributes_and_parameters,
            "p",
            AttributeAssignment.POSITION_OR_NAME,
            AttributeDocstring(
                type="int",
                default_value="2",
                description="foo. Defaults to 2.",
            ),
        ),
        (
            function_with_attributes_and_parameters,
            "q",
            AttributeAssignment.POSITION_OR_NAME,
            AttributeDocstring(
                type="",
                default_value="",
                description="",
            ),
        )
    ],
    ids=[
        "existing class attribute",
        "missing class attribute",
        "function attribute with no type and no default",
        "function attribute with type and no default",
        "function attribute with default",
        "function attribute with positional vararg",
        "function attribute with named vararg",
        "missing function attribute",
        "function with attributes and parameters existing attribute",
        "function with attributes and parameters missing attribute"
    ],
)
def test_get_attribute_documentation(
    googlestyledoc_parser: GoogleDocParser,
    python_code: str,
    attribute_name: str,
    attribute_assigned_by: AttributeAssignment,
    expected_attribute_documentation: AttributeDocstring,
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
        googlestyledoc_parser.get_attribute_documentation(node, attribute_name, attribute_assigned_by)
        == expected_attribute_documentation
    )


# language=python
function_with_return_value_and_type = '''
# noinspection PyUnresolvedReferences,PyIncorrectDocstring
def f():
    """Lorem ipsum.

    Dolor sit amet.

    Returns:
        int: this will be the return value.
    """

    pass
'''

# language=python
function_with_return_value_no_type = '''
# noinspection PyUnresolvedReferences,PyIncorrectDocstring
def f():
    """Lorem ipsum.

    Dolor sit amet.

    Returns:
        int
    """

    pass
'''

# language=python
function_without_return_value = '''
# noinspection PyUnresolvedReferences,PyIncorrectDocstring
def f():
    """Lorem ipsum.

    Dolor sit amet.
    """

    pass
'''


@pytest.mark.parametrize(
    ("python_code", "expected_return_documentation"),
    [
        (
            function_with_return_value_and_type,
            ResultDocstring(type="int", description="this will be the return value."),
        ),
        (
            function_with_return_value_no_type,
            ResultDocstring(type="", description="int"),
        ),
        (
            function_without_return_value,
            ResultDocstring(type="", description="")
        ),
    ],
    ids=[
        "existing return value and type",
        "existing return value no description",
        "function without return value"
    ],
)
def test_get_result_documentation(
    googlestyledoc_parser: GoogleDocParser,
    python_code: str,
    expected_return_documentation: ResultDocstring,
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
        googlestyledoc_parser.get_result_documentation(node)
        == expected_return_documentation
    )
