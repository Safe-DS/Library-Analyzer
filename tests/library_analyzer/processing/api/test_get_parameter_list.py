import astroid
import pytest
from library_analyzer.processing.api import get_parameter_list
from library_analyzer.processing.api.docstring_parsing import (
    PlaintextDocstringParser,
)
from library_analyzer.processing.api.model import (
    Parameter,
    ParameterAssignment,
    ParameterDocstring,
)

global_function_empty_parameter_list = """
def f():
    pass
"""

global_function_full_parameter_list = """
def f(position_only, /, position_or_name, *, name_only = 0):
    pass
"""

global_function_parameter_list_with_positional_vararg = """
def f(*args, name_only = 0):
    pass
"""

global_function_parameter_list_with_named_vararg = """
def f(**kwargs):
    pass
"""


@pytest.mark.parametrize(
    ("python_code", "expected_parameter_list"),
    [
        (global_function_empty_parameter_list, []),
        (
            global_function_full_parameter_list,
            [
                Parameter(
                    id_="f/position_only",
                    name="position_only",
                    qname="f.position_only",
                    default_value=None,
                    assigned_by=ParameterAssignment.POSITION_ONLY,
                    is_public=True,
                    docstring=ParameterDocstring(),
                ),
                Parameter(
                    id_="f/position_or_name",
                    name="position_or_name",
                    qname="f.position_or_name",
                    default_value=None,
                    assigned_by=ParameterAssignment.POSITION_OR_NAME,
                    is_public=True,
                    docstring=ParameterDocstring(),
                ),
                Parameter(
                    id_="f/name_only",
                    name="name_only",
                    qname="f.name_only",
                    default_value="0",
                    assigned_by=ParameterAssignment.NAME_ONLY,
                    is_public=True,
                    docstring=ParameterDocstring(),
                ),
            ],
        ),
        (
            global_function_parameter_list_with_positional_vararg,
            [
                Parameter(
                    id_="f/args",
                    name="args",
                    qname="f.args",
                    default_value=None,
                    assigned_by=ParameterAssignment.POSITIONAL_VARARG,
                    is_public=True,
                    docstring=ParameterDocstring(),
                ),
                Parameter(
                    id_="f/name_only",
                    name="name_only",
                    qname="f.name_only",
                    default_value="0",
                    assigned_by=ParameterAssignment.NAME_ONLY,
                    is_public=True,
                    docstring=ParameterDocstring(),
                ),
            ],
        ),
        (
            global_function_parameter_list_with_named_vararg,
            [
                Parameter(
                    id_="f/kwargs",
                    name="kwargs",
                    qname="f.kwargs",
                    default_value=None,
                    assigned_by=ParameterAssignment.NAMED_VARARG,
                    is_public=True,
                    docstring=ParameterDocstring(),
                ),
            ],
        ),
    ],
    ids=[
        "empty parameter list",
        "full parameter list",
        "parameter list with positional vararg",
        "parameter list with named vararg",
    ],
)
def test_get_parameter_list_on_global_functions(python_code: str, expected_parameter_list: list) -> None:
    node = astroid.extract_node(python_code)
    assert isinstance(node, astroid.FunctionDef)

    actual_parameter_list = [
        it.to_dict()
        for it in get_parameter_list(
            docstring_parser=PlaintextDocstringParser(),
            function_node=node,
            function_id="f",
            function_qname="f",
            function_is_public=True,
        )
    ]

    expected_parameter_list = [it.to_dict() for it in expected_parameter_list]

    assert actual_parameter_list == expected_parameter_list


instance_method_parameter_list = """
class C:
    def f(self, p):
        pass
"""

static_method_parameter_list = """
class C:
    @staticmethod
    def f(p):
        pass
"""

class_method_parameter_list = """
class C:
    @classmethod
    def f(cls, p):
        pass
"""

instance_method_with_variadic_first_parameter = """
class C:
    def f(*self):
        pass
"""


@pytest.mark.parametrize(
    ("python_code", "expected_parameter_list"),
    [
        (
            instance_method_parameter_list,
            [
                Parameter(
                    id_="C/f/self",
                    name="self",
                    qname="C.f.self",
                    default_value=None,
                    assigned_by=ParameterAssignment.IMPLICIT,
                    is_public=True,
                    docstring=ParameterDocstring(),
                ),
                Parameter(
                    id_="C/f/p",
                    name="p",
                    qname="C.f.p",
                    default_value=None,
                    assigned_by=ParameterAssignment.POSITION_OR_NAME,
                    is_public=True,
                    docstring=ParameterDocstring(),
                ),
            ],
        ),
        (
            static_method_parameter_list,
            [
                Parameter(
                    id_="C/f/p",
                    name="p",
                    qname="C.f.p",
                    default_value=None,
                    assigned_by=ParameterAssignment.POSITION_OR_NAME,
                    is_public=True,
                    docstring=ParameterDocstring(),
                ),
            ],
        ),
        (
            class_method_parameter_list,
            [
                Parameter(
                    id_="C/f/cls",
                    name="cls",
                    qname="C.f.cls",
                    default_value=None,
                    assigned_by=ParameterAssignment.IMPLICIT,
                    is_public=True,
                    docstring=ParameterDocstring(),
                ),
                Parameter(
                    id_="C/f/p",
                    name="p",
                    qname="C.f.p",
                    default_value=None,
                    assigned_by=ParameterAssignment.POSITION_OR_NAME,
                    is_public=True,
                    docstring=ParameterDocstring(),
                ),
            ],
        ),
        (
            instance_method_with_variadic_first_parameter,
            [
                Parameter(
                    id_="C/f/self",
                    name="self",
                    qname="C.f.self",
                    default_value=None,
                    assigned_by=ParameterAssignment.POSITIONAL_VARARG,
                    is_public=True,
                    docstring=ParameterDocstring(),
                ),
            ],
        ),
    ],
    ids=[
        "instance method parameter list",
        "static method parameter list",
        "class method parameter list",
        "instance method with variadic first parameter",
    ],
)
def test_get_parameter_list_on_method(python_code: str, expected_parameter_list: list) -> None:
    node = astroid.extract_node(python_code)
    assert isinstance(node, astroid.ClassDef)

    for method in node.mymethods():
        if method.name == "f":
            node = method

    assert isinstance(node, astroid.FunctionDef)

    actual_parameter_list = [
        it.to_dict()
        for it in get_parameter_list(
            docstring_parser=PlaintextDocstringParser(),
            function_node=node,
            function_id="C/f",
            function_qname="C.f",
            function_is_public=True,
        )
    ]

    expected_parameter_list = [it.to_dict() for it in expected_parameter_list]

    assert actual_parameter_list == expected_parameter_list
