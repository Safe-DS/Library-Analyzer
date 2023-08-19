from __future__ import annotations

from dataclasses import dataclass, field

import astroid
import pytest
from library_analyzer.processing.api import (
    ClassScope,
    MemberAccess,
    MemberAccessTarget,
    MemberAccessValue,
    Scope,
    NodeID,
    _calc_node_id,
    _get_module_data,
    ReferenceNode,
    _create_unspecified_references,
    _find_references,
    get_base_expression,
    resolve_references,
)


@dataclass
class SimpleScope:
    node_name: str | None
    children: list[SimpleScope] | None

@dataclass
class SimpleClassScope(SimpleScope):
    class_variables: list[str]
    instance_variables: list[str]
    super_class: list[str] = field(default_factory=list)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (
            """
                def variable():
                    var1 = 20
            """,
            ["AssignName.var1"],
        ),
        (
            """
                def parameter(a):
                    var1 = a
            """,
            ["AssignName.a", "AssignName.var1", "Name.a"],
        ),
        (
            """
                def glob():
                    global glob1
            """,
            [],
        ),
        (
            """
                def glob():
                    global glob1
                    var1 = glob1
            """,
            ["AssignName.var1", "Name.glob1"],
        ),
        (
            """
                def class_attr():
                    var1 = A.class_attr
            """,
            ["AssignName.var1", "MemberAccess.A.class_attr"],
        ),
        (
            """
                def instance_attr():
                    b = B()
                    var1 = b.instance_attr
            """,
            ["AssignName.b", "AssignName.var1", "MemberAccess.b.instance_attr"],
        ),
        (
            """
                def chain():
                    var1 = test.instance_attr.field.next_field
            """,
            [
                "AssignName.var1",
                "MemberAccess.test.instance_attr.field.next_field",
                "MemberAccess.test.instance_attr.field",
                "MemberAccess.test.instance_attr",
            ],
        ),
        (
            """
                def chain_reversed():
                    test.instance_attr.field.next_field = var1
            """,
            [
                "MemberAccess.test.instance_attr.field.next_field",
                "MemberAccess.test.instance_attr.field",
                "MemberAccess.test.instance_attr",
                "Name.var1",
            ],
        ),
        (
            """
                def assign_attr():
                    a.res = 1
            """,
            ["MemberAccess.a.res"],
        ),
        (
            """
                def aug_assign():
                    var1 += 1
            """,
            ["AssignName.var1"],
        ),
        (
            """
                def assign_return():
                    return var1
            """,
            ["Name.var1"],
        ),
        (
            """
                def while_loop():
                    while var1 > 0:
                        do_something()
            """,
            ["Name.var1"],
        ),
        (
            """
                def for_loop():
                    for var1 in range(10):
                        do_something()
            """,
            ["AssignName.var1"],
        ),
        (
            """
                def if_state():
                    if var1 > 0:
                        do_something()
            """,
            ["Name.var1"],
        ),
        (
            """
                def if_else_state():
                    if var1 > 0:
                        do_something()
                    else:
                        do_something_else()
            """,
            ["Name.var1"],
        ),
        (
            """
                def if_elif_state():
                    if var1 & True:
                        do_something()
                    elif var1 | var2:
                        do_something_else()
            """,
            ["Name.var1", "Name.var1", "Name.var2"],
        ),
        (
            """
                def ann_assign():
                    var1: int = 10
            """,
            ["AssignName.var1"],
        ),
        (
            """
                def func_call():
                    var1 = func(var2)
            """,
            ["AssignName.var1", "Name.var2"],
        ),
        (
            """
                def func_call_par(param):
                    var1 = param + func(param)
            """,
            ["AssignName.param", "AssignName.var1", "Name.param", "Name.param"],
        ),
        (
            """
                def bin_op():
                    var1 = 20 + var2
            """,
            ["AssignName.var1", "Name.var2"],
        ),
        (
            """
                def bool_op():
                    var1 = True and var2
            """,
            ["AssignName.var1", "Name.var2"],
        ),
        (
            """
                import math

                def local_import():
                    var1 = math.pi
                    return var1
            """,
            ["Import.math", "AssignName.var1", "MemberAccess.math.pi", "Name.var1"]
        ),
        (
            """
                from math import pi

                def local_import():
                    var1 = pi
                    return var1
            """,
            ["ImportFrom.math.pi", "AssignName.var1", "Name.test", "Name.var1"]
        ),
        (
            """
                from math import pi as test

                def local_import():
                    var1 = test
                    return var1
            """,
            ["ImportFrom.math.pi.test", "AssignName.var1", "Name.test", "Name.var1"]
        ),
        (
            """
                from collections.abc import Callable
                from typing import Any

                import astroid

                _EnterAndLeaveFunctions = tuple[
                    Callable[[astroid.NodeNG], None] | None,
                    Callable[[astroid.NodeNG], None] | None,
                ]


                class ASTWalker:
                    def __init__(self, handler: Any) -> None:
                        self._handler = handler
                        self._cache: dict[type, _EnterAndLeaveFunctions] = {}

                    def walk(self, node: astroid.NodeNG) -> None:
                        self.__walk(node, set())

                    def __walk(self, node: astroid.NodeNG, visited_nodes: set[astroid.NodeNG]) -> None:
                        if node in visited_nodes:
                            raise AssertionError("Node visited twice")
                        visited_nodes.add(node)

                        self.__enter(node)
                        for child_node in node.get_children():
                            self.__walk(child_node, visited_nodes)
                        self.__leave(node)

                    def __enter(self, node: astroid.NodeNG) -> None:
                        method = self.__get_callbacks(node)[0]
                        if method is not None:
                            method(node)

                    def __leave(self, node: astroid.NodeNG) -> None:
                        method = self.__get_callbacks(node)[1]
                        if method is not None:
                            method(node)

                    def __get_callbacks(self, node: astroid.NodeNG) -> _EnterAndLeaveFunctions:
                        klass = node.__class__
                        methods = self._cache.get(klass)

                        if methods is None:
                            handler = self._handler
                            class_name = klass.__name__.lower()
                            enter_method = getattr(handler, f"enter_{class_name}", getattr(handler, "enter_default", None))
                            leave_method = getattr(handler, f"leave_{class_name}", getattr(handler, "leave_default", None))
                            self._cache[klass] = (enter_method, leave_method)
                        else:
                            enter_method, leave_method = methods

                        return enter_method, leave_method

            """, [""]
        ),
    ],
    ids=[
        "Assign",
        "Assign Parameter",
        "Global unused",
        "Global and Assign",
        "Assign Class Attribute",
        "Assign Instance Attribute",
        "Assign MemberAccess as value",
        "Assign MemberAccess as target",
        "AssignAttr",
        "AugAssign",
        "Return",
        "While",
        "For",
        "If",
        "If Else",
        "If Elif",
        "AnnAssign",
        "FuncCall",
        "FuncCall Parameter",
        "BinOp",
        "BoolOp",
        "Import",
        "Import From",
        "Import From As",
        "ASTWalker"
    ],
)
def test_get_name_nodes(code: str, expected: str) -> None:
    names_list = _get_module_data(code).names_list

    assert_names_list(names_list, expected)


def assert_names_list(names_list: list[astroid.Name], expected: str) -> None:
    names_list = transform_names_list(names_list)
    assert names_list == expected


def transform_names_list(names_list: list[astroid.Name]) -> list[str]:
    names_list_transformed = []
    for name in names_list:
        if isinstance(name, astroid.Name | astroid.AssignName):
            names_list_transformed.append(f"{name.__class__.__name__}.{name.name}")
        elif isinstance(name, MemberAccess):
            result = transform_member_access(name)
            names_list_transformed.append(f"MemberAccess.{result}")

    return names_list_transformed


def transform_member_access(member_access: MemberAccess) -> str:
    attribute_names = []

    while isinstance(member_access, MemberAccess):
        attribute_names.append(member_access.value.name)
        member_access = member_access.expression
    if isinstance(member_access, astroid.Name):
        attribute_names.append(member_access.name)

    return ".".join(reversed(attribute_names))


@pytest.mark.parametrize(
    ("node", "expected"),
    [
        (
            astroid.Module("numpy"),
            "numpy.numpy.0.0",
        ),
        (
            astroid.ClassDef("A", lineno=2, col_offset=3, parent=astroid.Module("numpy")),
            "numpy.A.2.3",
        ),
        (
            astroid.FunctionDef(
                "local_func",
                lineno=1,
                col_offset=0,
                parent=astroid.ClassDef("A", lineno=2, col_offset=3),
            ),
            "A.local_func.1.0",
        ),
        (
            astroid.FunctionDef(
                "global_func",
                lineno=1,
                col_offset=0,
                parent=astroid.ClassDef("A", lineno=2, col_offset=3, parent=astroid.Module("numpy")),
            ),
            "numpy.global_func.1.0",
        ),
        (
            astroid.AssignName(
                "var1",
                lineno=1,
                col_offset=5,
                parent=astroid.FunctionDef("func1", lineno=1, col_offset=0),
            ),
            "func1.var1.1.5",
        ),
        (
            astroid.Name("var2", lineno=20, col_offset=0, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
            "func1.var2.20.0",
        ),
        (
            astroid.Name(
                "glob",
                lineno=20,
                col_offset=0,
                parent=astroid.FunctionDef(
                    "func1",
                    lineno=1,
                    col_offset=0,
                    parent=astroid.ClassDef("A", lineno=2, col_offset=3, parent=astroid.Module("numpy")),
                ),
            ),
            "numpy.glob.20.0",
        ),
        (
            astroid.Import(names=[("numpy", None)], lineno=1, col_offset=0, parent=astroid.Module("my_module")),
            "my_module.numpy.1.0",
        ),
        (
            astroid.Import(names=[("numpy", None), ("sys", None)], lineno=1, col_offset=0,
                           parent=astroid.Module("my_module")),
            "my_module.numpy.1.0",
        # TODO: this is a problem since one node can contain multiple imports and therefore each one needs its own id
        ),
        (
            astroid.Import(names=[("numpy", "np")], lineno=1, col_offset=0, parent=astroid.Module("my_module")),
            "my_module.np.1.0",
        ),
        (
            astroid.ImportFrom(fromname='math', names=[('sqrt', None)], level=0, lineno=1, col_offset=0,
                               parent=astroid.Module("my_module")),
            "my_module.sqrt.1.0",
        ),
        (
            astroid.ImportFrom(fromname='math', names=[('sqrt', 's')], level=0, lineno=1, col_offset=0,
                               parent=astroid.Module("my_module")),
            "my_module.s.1.0",
        )
    ],
    ids=[
        "Module",
        "ClassDef (parent Module)",
        "FunctionDef (parent ClassDef)",
        "FunctionDef (parent ClassDef, parent Module)",
        "AssignName (parent FunctionDef)",
        "Name (parent FunctionDef)",
        "Name (parent FunctionDef, parent ClassDef, parent Module)",
        "Import",
        "Import multiple",
        "Import as",
        "Import From",
        "Import From as",
    ],
)
def test_calc_node_id(
    node: astroid.Module | astroid.ClassDef | astroid.FunctionDef | astroid.AssignName | astroid.Name,
    expected: str,
) -> None:
    result = _calc_node_id(node)
    assert result.__str__() == expected


@pytest.mark.parametrize(
    ("node", "expected"),
    [
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0))],
            [ReferenceNode(astroid.Name("var1", lineno=1, col_offset=4),
                           Scope(astroid.Name("var1", lineno=1, col_offset=4), NodeID(astroid.Module(""), "var1", 1, 4),
                                 []))]
        ),
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
             astroid.Name("var2", lineno=2, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
             astroid.Name("var3", lineno=30, col_offset=4,
                          parent=astroid.FunctionDef("func2", lineno=1, col_offset=0))],
            [ReferenceNode(astroid.Name("var1", lineno=1, col_offset=4),
                           Scope(astroid.Name("var1", lineno=1, col_offset=4), NodeID(astroid.Module(""), "var1", 1, 4),
                                 [])),
             ReferenceNode(astroid.Name("var2", lineno=2, col_offset=4),
                           Scope(astroid.Name("var2", lineno=2, col_offset=4), NodeID(astroid.Module(""), "var2", 2, 4),
                                 [])),
             ReferenceNode(astroid.Name("var3", lineno=30, col_offset=4),
                           Scope(astroid.Name("var3", lineno=30, col_offset=4),
                                 NodeID(astroid.Module(""), "var3", 30, 4), []))]
        ),
        (
            [astroid.AssignName("var1", lineno=12, col_offset=42,
                                parent=astroid.FunctionDef("func1", lineno=1, col_offset=0))],
            [ReferenceNode(astroid.AssignName("var1", lineno=12, col_offset=42),
                           Scope(astroid.AssignName("var1", lineno=12, col_offset=42),
                                 NodeID(astroid.Module(""), "var1", 12, 42), []))]
        ),
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
             astroid.AssignName("var2", lineno=1, col_offset=8,
                                parent=astroid.FunctionDef("func1", lineno=1, col_offset=0))],
            [ReferenceNode(astroid.Name("var1", lineno=1, col_offset=4),
                           Scope(astroid.Name("var1", lineno=1, col_offset=4), NodeID(astroid.Module(""), "var1", 1, 4),
                                 [])),
             ReferenceNode(astroid.AssignName("var2", lineno=1, col_offset=8),
                           Scope(astroid.AssignName("var2", lineno=1, col_offset=8),
                                 NodeID(astroid.Module(""), "var2", 1, 8), []))]
        ),
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.ClassDef("MyClass", lineno=1, col_offset=0))],
            [ReferenceNode(astroid.Name("var1", lineno=1, col_offset=4),
                           Scope(astroid.Name("var1", lineno=1, col_offset=4), NodeID(astroid.Module(""), "var1", 1, 4),
                                 []))]
        ),
        (
            [astroid.Name("glob", lineno=1, col_offset=4, parent=astroid.Module("mod"))],
            [ReferenceNode(astroid.Name("glob", lineno=1, col_offset=4),
                           Scope(astroid.Name("glob", lineno=1, col_offset=4),
                                 NodeID(astroid.Module("mod"), "glob", 1, 4), []))]
        ),
        (
            [],
            []
        ),
    ],
    ids=[
        "Name FunctionDef",
        "Multiple Names FunctionDef",
        "AssignName FunctionDef",
        "Name and AssignName FunctionDef",
        "Name ClassDef",
        "Name Module",
        "Empty list",
    ]
)
def test_create_references(node: list[astroid.Name | astroid.AssignName], expected: list[ReferenceNode]) -> None:
    result = _create_unspecified_references(node)[0]
    assert result == expected
    assert_reference_list_equal(result, expected)


# TODO: rewrite this test since the results are no longer just prototypes


def assert_reference_list_equal(result: list[ReferenceNode], expected: list[ReferenceNode]) -> None:
    """ Assert reference list equality.

    The result data as well as the expected data in this test is simplified, so it is easier to compare the results.
    The real results name and scope are objects and not strings"""
    result = [
        ReferenceNode(name.name.name, name.scope.children.__class__.__name__, name.referenced_symbols) for name in
        result]
    expected = [
        ReferenceNode(name.name.name, name.scope.children.__class__.__name__, name.referenced_symbols) for name in
        expected]
    assert result == expected


# TODO: test this when resolve reference is implemented (disabled for now due to test failures)
# def test_add_target_references() -> None:
#     raise NotImplementedError("Test not implemented")


@dataclass
class ReferenceTestNode:
    name: str
    scope: str
    referenced_symbols: list[str]


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "local variable in function scope"
            """
def local_var():
    var1 = 1
    return var1
            """,  # language= None
            [ReferenceTestNode("var1.line4", "FunctionDef.local_var", ["LocalVariable.var1.line3"])]
        ),
        (  # language=Python "parameter in function scope"
            """
def local_parameter(pos_arg):
    return 2 * pos_arg
            """,  # language= None
            [ReferenceTestNode("pos_arg.line3", "FunctionDef.local_parameter", ["Parameter.pos_arg.line2"])]
        ),
        (  # language=Python "parameter in function scope with keyword only"
            """
def local_parameter(*, key_arg_only):
    return 2 * key_arg_only
            """,  # language= None
            [ReferenceTestNode("key_arg_only.line3", "FunctionDef.local_parameter", ["Parameter.key_arg_only.line2"])]
        ), (  # language=Python "parameter in function scope with positional only"
            """
def local_parameter(pos_arg_only, /):
    return 2 * pos_arg_only
            """,  # language= None
            [ReferenceTestNode("pos_arg_only.line3", "FunctionDef.local_parameter", ["Parameter.pos_arg_only.line2"])]
        ),
        (  # language=Python "parameter in function scope with default value"
            """
def local_parameter(def_arg=10):
    return def_arg
            """,  # language= None
            [ReferenceTestNode("def_arg.line3", "FunctionDef.local_parameter", ["Parameter.def_arg.line2"])]
        ),
        (  # language=Python "parameter in function scope with type annotation"
            """
def local_parameter(def_arg: int):
    return def_arg
            """,  # language= None
            [ReferenceTestNode("def_arg.line3", "FunctionDef.local_parameter", ["Parameter.def_arg.line2"])]
        ),
        (  # language=Python "parameter in function scope with *args"
            """
def local_parameter(*args):
    return args
            """,  # language= None
            [ReferenceTestNode("args.line3", "FunctionDef.local_parameter", ["Parameter.args.line2"])]
        ),
        (  # language=Python "parameter in function scope with **kwargs"
            """
def local_parameter(**kwargs):
    return kwargs
            """,  # language= None
            [ReferenceTestNode("kwargs.line3", "FunctionDef.local_parameter", ["Parameter.kwargs.line2"])]
        ),
        (  # language=Python "parameter in function scope with *args and **kwargs"
            """
def local_parameter(*args, **kwargs):
    return args, kwargs
            """,  # language= None
            [ReferenceTestNode("args.line3", "FunctionDef.local_parameter", ["Parameter.args.line2"]),
             ReferenceTestNode("kwargs.line3", "FunctionDef.local_parameter", ["Parameter.kwargs.line2"])]
        ),
        (  # language=Python "two parameters in function scope"
            """
def local_double_parameter(a, b):
    return a, b
            """,  # language= None
            [ReferenceTestNode("a.line3", "FunctionDef.local_double_parameter", ["Parameter.a.line2"]),
             ReferenceTestNode("b.line3", "FunctionDef.local_double_parameter", ["Parameter.b.line2"])]
        ),
        (  # language=Python "global variable in module scope"
            """
glob1 = 10
glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line3", "Module.", ["GlobalVariable.glob1.line2"])]
        ),
        (  # language=Python "global variable in class scope"
            """
glob1 = 10
class A:
    global glob1
    glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line5", "ClassDef.A", ["GlobalVariable.glob1.line2"])]
        ),
        (  # language=Python "global variable in function scope"
            """
glob1 = 10
def local_global():
    global glob1

    return glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line6", "FunctionDef.local_global", ["GlobalVariable.glob1.line2"])]
        ),
        (  # language=Python "global variable in function scope but after definition"
            """
def local_global():
    global glob1

    return glob1

glob1 = 10
            """,  # language= None
            [ReferenceTestNode("glob1.line5", "FunctionDef.local_global", ["GlobalVariable.glob1.line7"])]
        ),
        (  # language=Python "global variable in class scope and function scope"
            """
glob1 = 10
class A:
    global glob1
    glob1

def local_global():
    global glob1

    return glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line5", "ClassDef.A", ["GlobalVariable.glob1.line2"]),
             ReferenceTestNode("glob1.line10", "FunctionDef.local_global", ["GlobalVariable.glob1.line2"])]
        ),
        (  # language=Python "access of global variable without global keyword"
            """
glob1 = 10
def local_global_access():
    return glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line4", "FunctionDef.local_global_access", ["GlobalVariable.glob1.line2"])]
        ),
        (  # language=Python "local variable in function scope shadowing global variable without global keyword"
            """
glob1 = 10
def local_global_shadow():
    glob1 = 20

    return glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line6", "FunctionDef.local_global_shadow",
                               ["GlobalVariable.glob1.line2", "LocalVariable.glob1.line4"])]
        ),
        (  # language=Python "two globals in class scope"
            """
glob1 = 10
glob2 = 20
class A:
    global glob1, glob2
    glob1, glob2
            """,  # language= None
            [ReferenceTestNode("glob1.line6", "ClassDef.A", ["GlobalVariable.glob1.line2"]),
             ReferenceTestNode("glob2.line6", "ClassDef.A", ["GlobalVariable.glob2.line3"])]
        ),
        (  # language=Python "class attribute value"
            """
class A:
    class_attr1 = 20

A.class_attr1
            """,  # language=none
            [ReferenceTestNode("A.class_attr1.line5", "Module.", ["ClassVariable.A.class_attr1.line3"])]
        ),
        (  # language=Python "class attribute target"
            """
class A:
    class_attr1 = 20

A.class_attr1 = 30
A.class_attr1
            """,  # language=none
            [ReferenceTestNode("A.class_attr1.line6", "Module.", ["ClassVariable.A.class_attr1.line5",
                                                                  "ClassVariable.A.class_attr1.line3"])]
        ),
        (  # language=Python "chained class attribute"
            """
class A:
    class_attr1 = 20

class B:
    upper_class: A = A

b = B()
x = b.upper_class.class_attr1
            """,  # language=none
            [ReferenceTestNode("B.line8", "Module.", ["GlobalVariable.B.line5"]),
             ReferenceTestNode("b.upper_class.class_attr1.line9", "Module.", ["ClassVariable.A.class_attr1.line3"]),
             ReferenceTestNode("b.upper_class.line9", "Module.", ["ClassVariable.B.upper_class.line6"]),
             ReferenceTestNode("b.line9", "Module.", ["GlobalVariable.b.line8"])]
        ),
        (  # language=Python "instance attribute value"
            """
class B:
    def __init__(self):
        self.instance_attr1 = 10

b = B()
var1 = b.instance_attr1
            """,  # language=none
            [ReferenceTestNode("B.line6", "Module.", ["GlobalVariable.B.line2"]),
             ReferenceTestNode("b.line7", "Module.", ["GlobalVariable.b.line6"]),
             ReferenceTestNode("b.instance_attr1.line7", "Module.", ["InstanceVariable.b.instance_attr1.line4"])]
        ),
        (  # language=Python "instance attribute target"
            """
class B:
    def __init__(self):
        self.instance_attr1 = 10

b = B()
b.instance_attr1 = 1
b.instance_attr1
            """,  # language=none
            [ReferenceTestNode("B.line6", "Module.", ["GlobalVariable.B.line2"]),
             ReferenceTestNode("b.line7", "Module.", ["GlobalVariable.b.line6"]),
             ReferenceTestNode("b.instance_attr1.line8", "Module.", ["ClassVariable.b.instance_attr1.line7",
                                                                     "InstanceVariable.b.instance_attr1.line4"])
             ]
        ),
        (  # language=Python "instance attribute with parameter"
            """
class B:
    def __init__(self, name: str):
        self.name = name

b = B("test")
b.name
            """,  # language=none
            [ReferenceTestNode("B.line6", "Module.", ["GlobalVariable.B.line2"]),
             ReferenceTestNode("name.line4", "FunctionDef.__init__", ["Parameter.name.line3"]),
             ReferenceTestNode("b.line7", "Module.", ["GlobalVariable.b.line6"]),
             ReferenceTestNode("b.name.line7", "Module.", ["InstanceVariable.b.name.line4"])]
        ),
        (  # language=Python "instance attribute with parameter and class attribute"
            """
class X:
    class_attr = 10

    def __init__(self, name: str):
        self.name = name

x = X("test")
x.name
x.class_attr
            """,  # language=none
            [ReferenceTestNode("X.line8", "Module.", ["GlobalVariable.X.line2"]),
             ReferenceTestNode("name.line6", "FunctionDef.__init__", ["Parameter.name.line5"]),
             ReferenceTestNode("x.line9", "Module.", ["GlobalVariable.x.line8"]),
             ReferenceTestNode("x.name.line9", "Module.", ["InstanceVariable.x.name.line6"]),
             ReferenceTestNode("x.line10", "Module.", ["GlobalVariable.x.line8"]),
             ReferenceTestNode("x.class_attr.line10", "Module.", ["ClassVariable.X.class_attr.line3"])]
        ),
        (  # language=Python "chained class attribute and instance attribute"
            """
class A:
    def __init__(self):
        self.name = 10

class B:
    upper_class: A = A()

b = B()
x = b.upper_class.name
            """,  # language=none
            [ReferenceTestNode("A.line7", "ClassDef.B", ["GlobalVariable.A.line2"]),
             ReferenceTestNode("B.line9", "Module.", ["GlobalVariable.B.line6"]),
             ReferenceTestNode("b.upper_class.name.line10", "Module.", ["InstanceVariable.upper_class.name.line4"]),
             ReferenceTestNode("b.upper_class.line10", "Module.", ["ClassVariable.B.upper_class.line7"]),
             ReferenceTestNode("b.line10", "Module.", ["GlobalVariable.b.line9"])
             ]
        ),
        (  # language=Python "chained instance attributes"
            """
class A:
    def __init__(self):
        self.b = B()

class B:
    def __init__(self):
        self.c = C()

class C:
    def __init__(self):
        self.name = "name"

a = A()
a.b.c.name
            """,  # language=none
            [ReferenceTestNode("B.line4", "ClassDef.A", ["GlobalVariable.A.line2"]),
             ReferenceTestNode("C.line8", "ClassDef.B", ["GlobalVariable.B.line6"]),
             ReferenceTestNode("A.line12", "Module.", ["GlobalVariable.A.line2"]),
             ReferenceTestNode("a.b.c.name.line13", "Module.", ["InstanceVariable.c.name.line11"]),
             ReferenceTestNode("a.b.c.line13", "Module.", ["InstanceVariable.b.c.line8"]),
             ReferenceTestNode("a.b.line13", "Module.", ["InstanceVariable.a.b.line4"]),
             ReferenceTestNode("a.line13", "Module.", ["GlobalVariable.a.line12"])]
        ),
        (  # language=Python "two classes with same signature"
            """
class A:
    def __init__(self, name: str):
        self.name = name

class B:
    def __init__(self, name: str):
        self.name = name

a = A("value")
b = B("test")
a.name
b.name
            """,  # language=none
            [ReferenceTestNode("A.line10", "Module.", ["GlobalVariable.A.line2"]),
             ReferenceTestNode("B.line11", "Module.", ["GlobalVariable.B.line6"]),
             ReferenceTestNode("name.line4", "FunctionDef.__init__", ["Parameter.name.line3"]),
             ReferenceTestNode("name.line8", "FunctionDef.__init__", ["Parameter.name.line7"]),
             ReferenceTestNode("a.name.line12", "Module.", ["InstanceVariable.a.name.line4",  # class A
                                                            "InstanceVariable.b.name.line8"]),  # class B
             ReferenceTestNode("b.name.line13", "Module.", ["InstanceVariable.a.name.line4",  # class A
                                                            "InstanceVariable.b.name.line8"])]  # class B
        ),
        (  # language=Python "getter function with self"
            """
class C:
    state: int = 0

    def get_state(self):
        return self.state
            """,  # language= None
            [ReferenceTestNode("self.state.line6", "FunctionDef.get_state", ["ClassVariable.C.state.line3"])]
        ),
        (  # language=Python "getter function with classname"
            """
class C:
    state: int = 0

    def get_state(self):
        return C.state
            """,  # language= None
            [ReferenceTestNode("C.state.line6", "FunctionDef.get_state", ["ClassVariable.C.state.line3"])]
        ),
        (  # language=Python "setter function with self"
            """
class C:
    state: int = 0

    def set_state(self, state):
        self.state = state
            """,  # language= None
            [ReferenceTestNode("state.line6", "FunctionDef.set_state", ["Parameter.state.line5"])]
        ),  # TODO: what do we do with self.state?
        (  # language=Python "setter function with self different name"
            """
class C:
    stateX: int = 0

    def set_state(self, state):
        self.stateX = state
            """,  # language= None
            [ReferenceTestNode("state.line6", "FunctionDef.set_state", ["Parameter.state.line5"])]
        ),  # TODO: what do we do with self.stateX?
        (  # language=Python "setter function with classname different name"
            """
class C:
    stateX: int = 0

    def set_state(self, state):
        C.stateX = state
            """,  # language= None
            [ReferenceTestNode("state.line6", "FunctionDef.set_state", ["Parameter.state.line5"])]
        ),  # TODO: what do we do with C.stateX?
        (  # language=Python "if statement global scope"
            """
var1 = 10
if var1 > 0:
    var1
        """,  # language=none
            [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line4", "Module.", ["GlobalVariable.var1.line2"])]
        ),
        (  # language=Python "if else statement global scope"
            """
var1 = 10
if var1 > 0:
    var1
else:
    2 * var1
        """,  # language=none
            [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line4", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line6", "Module.", ["GlobalVariable.var1.line2"])]
        ),
        (  # language=Python "if elif else statement global scope"
            """
var1 = 10
if var1 > 0:
    var1
elif var1 < 0:
    -var1
else:
    var1
        """,  # language=none
            [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line4", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line5", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line6", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line8", "Module.", ["GlobalVariable.var1.line2"])]
        ),
        (  # language=Python "if in statement global scope"
            """
var1 = [1, 2, 3]
if 1 in var1:
    var1
        """,  # language=none
            [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line4", "Module.", ["GlobalVariable.var1.line2"])]
        ),
        (  # language=Python "for loop with global runtime variable global scope"
            """
var1 = 10
for i in range(var1):
    i
        """,  # language=none
            [ReferenceTestNode("range.line3", "Module.", ["Builtin.range"]),
             ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("i.line4", "Module.", ["GlobalVariable.i.line3"])]
        ),
        (  # language=Python "for loop wih local runtime variable local scope"
            """
var1 = 10
def func1():
    for i in range(var1):
        i
        """,  # language=none
            [ReferenceTestNode("range.line4", "FunctionDef.func1", ["Builtin.range"]),
             ReferenceTestNode("var1.line4", "FunctionDef.func1", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("i.line5", "FunctionDef.func1", ["LocalVariable.i.line4"])]
        ),
        (  # language=Python "for loop with local runtime variable global scope"
            """
nums = ["one", "two", "three"]
for num in nums:
    num
        """,  # language=none
            [ReferenceTestNode("nums.line3", "Module.", ["GlobalVariable.nums.line2"]),
             ReferenceTestNode("num.line4", "Module.", ["GlobalVariable.num.line3"])]
        ),
        (  # language=Python "for loop in list comprehension global scope"
            """
nums = ["one", "two", "three"]
lengths = [len(num) for num in nums]  # TODO: list comprehension should get its own scope (LATER: for further improvement)
lengths
        """,  # language=none
            [ReferenceTestNode("len.line3", "Module.", ["Builtin.len"]),
             ReferenceTestNode("num.line3", "List.", ["LocalVariable.num.line3"]),
             ReferenceTestNode("nums.line3", "Module.", ["GlobalVariable.nums.line2"]),
             ReferenceTestNode("lengths.line4", "Module.", ["GlobalVariable.lengths.line3"])]
        ),
        (  # language=Python "while loop global scope"
            """
var1 = 10
while var1 > 0:
    var1
        """,  # language=none
            [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line4", "Module.", ["GlobalVariable.var1.line2"])]
        ),
        (  # language=Python "match statement global scope"
            """
var1 = 10
match var1:
    case 1: var1
    case 2: 2 * var1
    case (a, b): var1, a, b  # TODO: Match should get its own scope (LATER: for further improvement)  maybe add its parent
        """,  # language=none
            [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line4", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line5", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line6", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("a.line6", "Module.", ["GlobalVariable.a.line6"]),  # TODO: ask Lars
             ReferenceTestNode("b.line6", "Module.", ["GlobalVariable.b.line6"])]  # TODO: ask Lars if this is true GlobalVariable
        ),
        (  # language=Python "try except statement global scope"
            """
num1 = 2
num2 = 0
try:
    result = num1 / num2
    result
except ZeroDivisionError as zde:   # TODO: zde is not detected as a global variable # TODO: Except should get its own scope (LATER: for further improvement)
    zde
        """,  # language=none
            [ReferenceTestNode("num1.line5", "Module.", ["GlobalVariable.num1.line2"]),
             ReferenceTestNode("num2.line5", "Module.", ["GlobalVariable.num2.line3"]),
             ReferenceTestNode("result.line6", "Module.", ["GlobalVariable.result.line5"]),
             ReferenceTestNode("zde.line8", "Module.", ["GlobalVariable.zde.line7"])]
        ),
        (  # language=Python "array and indexed array global scope"
            """
arr = [1, 2, 3]
val = arr
res = arr[0]
arr[0] = 10
            """,  # language=none
            [ReferenceTestNode("arr.line3", "Module.", ["GlobalVariable.arr.line2"]),
             ReferenceTestNode("arr.line4", "Module.", ["GlobalVariable.arr.line2"]),
             ReferenceTestNode("arr.line5", "Module.", ["GlobalVariable.arr.line2"])]
        ),
        (  # language=Python "dictionary global scope"
            """
dictionary = {"key1": 1, "key2": 2}
dictionary["key1"] = 0
            """,  # language=none
            [ReferenceTestNode("dictionary.line3", "Module.", ["GlobalVariable.dictionary.line2"])]
        ),
        (  # language=Python "map function global scope"
            """
numbers = [1, 2, 3, 4, 5]

def square(x):
    return x ** 2

squares = list(map(square, numbers))
squares
            """,  # language=none
            [ReferenceTestNode("list.line7", "Module.", ["Builtin.list"]),
             ReferenceTestNode("map.line7", "Module.", ["Builtin.map"]),
             ReferenceTestNode("x.line5", "FunctionDef.square", ["Parameter.x.line4"]),
             ReferenceTestNode("square.line7", "Module.", ["GlobalVariable.square.line4"]),
             ReferenceTestNode("numbers.line7", "Module.", ["GlobalVariable.numbers.line2"]),
             ReferenceTestNode("squares.line8", "Module.", ["GlobalVariable.squares.line7"])]
        ),
        (  # language=Python "two variables"
            """
x = 10
y = 20
x + y
            """,  # language=none
            [ReferenceTestNode("x.line4", "Module.", ["GlobalVariable.x.line2"]),
             ReferenceTestNode("y.line4", "Module.", ["GlobalVariable.y.line3"])]
        ),
        (  # language=Python "double return"
            """
def double_return(a, b):
    return a, b

x, y = double_return(10, 20)
x, y
            """,  # language=none
            [ReferenceTestNode("double_return.line5", "Module.", ["GlobalVariable.double_return.line2"]),
             ReferenceTestNode("a.line3", "FunctionDef.double_return", ["Parameter.a.line2"]),
             ReferenceTestNode("b.line3", "FunctionDef.double_return", ["Parameter.b.line2"]),
             ReferenceTestNode("x.line6", "Module.", ["GlobalVariable.x.line5"]),
             ReferenceTestNode("y.line6", "Module.", ["GlobalVariable.y.line5"])]
        ),
        (  # language=Python "reassignment"
            """
x = 10
x = 20
x
            """,  # language=none
            [ReferenceTestNode("x.line4", "Module.", ["GlobalVariable.x.line2", "GlobalVariable.x.line3"])]
        ),
        (  # language=Python "vars with comma"
            """
x = 10
y = 20
x, y
            """,  # language=none
            [ReferenceTestNode("x.line4", "Module.", ["GlobalVariable.x.line2"]),
             ReferenceTestNode("y.line4", "Module.", ["GlobalVariable.y.line3"])]
        ),
        (  # language=Python "f-string"
            """
x = 10
y = 20
f"{x} + {y} = {x + y}"
            """,  # language=none
            [ReferenceTestNode("x.line4", "Module.", ["GlobalVariable.x.line2"]),
             ReferenceTestNode("y.line4", "Module.", ["GlobalVariable.y.line3"]),
             ReferenceTestNode("x.line4", "Module.", ["GlobalVariable.x.line2"]),
             ReferenceTestNode("y.line4", "Module.", ["GlobalVariable.y.line3"])]
        ),
        (  # language=Python "multiple references in one line"
            """
var1 = 10
var2 = 20

res = var1 + var2 - (var1 * var2)
            """,  # language=none
            [ReferenceTestNode("var1.line5", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var2.line5", "Module.", ["GlobalVariable.var2.line3"]),
             ReferenceTestNode("var1.line5", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var2.line5", "Module.", ["GlobalVariable.var2.line3"])]
        ),
        (  # language=Python "walrus operator"
            """
y = (x := 3) + 10
x, y
            """,  # language=none
            [ReferenceTestNode("x.line3", "Module.", ["GlobalVariable.x.line2"]),
             ReferenceTestNode("y.line3", "Module.", ["GlobalVariable.y.line2"])]
        ),
        (  # language=Python "variable swap"
            """
a = 1
b = 2
a, b = b, a
            """,  # language=none
            [ReferenceTestNode("b.line4", "Module.", ["GlobalVariable.b.line3", "GlobalVariable.b.line4"]),
             ReferenceTestNode("a.line4", "Module.", ["GlobalVariable.a.line2", "GlobalVariable.a.line4"])]
        ),
        (  # language=Python "aliases"
            """
a = 10
b = a
c = b
c
            """,  # language=none
            [ReferenceTestNode("a.line3", "Module.", ["GlobalVariable.a.line2"]),
             ReferenceTestNode("b.line4", "Module.", ["GlobalVariable.b.line3"]),
             ReferenceTestNode("c.line5", "Module.", ["GlobalVariable.c.line4"])]
        ),
        (  # language=Python "builtin function call"
            """
print("Hello, World!")
            """,  # language=none
            [ReferenceTestNode("print.line2", "Module.", ["Builtin.print"])]
        ),
        (  # language=Python "function call shadowing builtin function"
            """
print("Hello, World!")

def print(s):
    pass

print("Hello, World!")
            """,  # language=none
            [ReferenceTestNode("print.line2", "Module.", ["GlobalVariable.print.line4", "Builtin.print", ]),
             ReferenceTestNode("print.line7", "Module.", ["GlobalVariable.print.line4", "Builtin.print", ])]
        ),
        (  # language=Python "function call"
            """
def f():
    pass

f()
            """,  # language=none
            [ReferenceTestNode("f.line5", "Module.", ["GlobalVariable.f.line2"])]
        ),
        (  # language=Python "function call with parameter"
            """
def f(a):
    return a

x = 10
f(x)
            """,  # language=none
            [ReferenceTestNode("f.line6", "Module.", ["GlobalVariable.f.line2"]),
             ReferenceTestNode("a.line3", "FunctionDef.f", ["Parameter.a.line2"]),
             ReferenceTestNode("x.line6", "Module.", ["GlobalVariable.x.line5"])]
        ),
        (  # language=Python "function call with keyword parameter"
            """
def f(value):
    return value

x = 10
f(value=x)
            """,  # language=none
            [ReferenceTestNode("f.line6", "Module.", ["GlobalVariable.f.line2"]),
             ReferenceTestNode("value.line3", "FunctionDef.f", ["Parameter.value.line2"]),
             ReferenceTestNode("x.line6", "Module.", ["GlobalVariable.x.line5"])]
        ),
        (  # language=Python "function call as value"
            """
def f(a):
    return a

x = f(10)
            """,  # language=none
            [ReferenceTestNode("f.line5", "Module.", ["GlobalVariable.f.line2"]),
             ReferenceTestNode("a.line3", "FunctionDef.f", ["Parameter.a.line2"])]
        ),
        (  # language=Python "nested function call"
            """
def f(a):
    return a * 2

f(f(f(10)))
            """,  # language=none
            [ReferenceTestNode("f.line5", "Module.", ["GlobalVariable.f.line2"]),
             ReferenceTestNode("f.line5", "Module.", ["GlobalVariable.f.line2"]),
             ReferenceTestNode("f.line5", "Module.", ["GlobalVariable.f.line2"]),
             ReferenceTestNode("a.line3", "FunctionDef.f", ["Parameter.a.line2"])]
        ),
        (  # language=Python "nested function call with parameter"
            """
def f(a):
    return a * 2

x = 10
f(f(x))
            """,  # language=none
            [ReferenceTestNode("f.line6", "Module.", ["GlobalVariable.f.line2"]),
             ReferenceTestNode("f.line6", "Module.", ["GlobalVariable.f.line2"]),
             ReferenceTestNode("a.line3", "FunctionDef.f", ["Parameter.a.line2"]),
             ReferenceTestNode("x.line6", "Module.", ["GlobalVariable.x.line5"])]
        ),
        (  # language=Python "recursive function call",
            """
def f(a):
    print(a)
    if a > 0:
        f(a - 1)

x = 10
f(x)
            """,  # language=none
            [ReferenceTestNode("print.line3", "FunctionDef.f", ["Builtin.print"]),
             ReferenceTestNode("f.line5", "FunctionDef.f", ["GlobalVariable.f.line2"]),
             ReferenceTestNode("f.line8", "Module.", ["GlobalVariable.f.line2"]),
             ReferenceTestNode("a.line3", "FunctionDef.f", ["Parameter.a.line2"]),
             ReferenceTestNode("a.line4", "FunctionDef.f", ["Parameter.a.line2"]),
             ReferenceTestNode("a.line5", "FunctionDef.f", ["Parameter.a.line2"]),
             ReferenceTestNode("x.line8", "Module.", ["GlobalVariable.x.line7"])]
        ),
        (  # language=Python "class instantiation"
            """
class F:
    pass

F()
            """,  # language=none
            [ReferenceTestNode("F.line5", "Module.", ["GlobalVariable.F.line2"])]
        ),
        (  # language=Python "lambda function"
            """
lambda x, y: x + y
            """,  # language=none
            [ReferenceTestNode("x.line2", "Lambda", ["LocalVariable.x.line2"]),
             ReferenceTestNode("y.line2", "Lambda", ["LocalVariable.y.line2"])]
        ),
        (  # language=Python "lambda function call"
            """
(lambda x, y: x + y)(10, 20)
            """,  # language=none
            [ReferenceTestNode("x.line2", "Lambda", ["LocalVariable.x.line2"]),
             ReferenceTestNode("y.line2", "Lambda", ["LocalVariable.y.line2"])]
        ),
        (  # language=Python "lambda function used as normal function"
            """
double = lambda x: 2 * x

double(10)
            """,  # language=none
            [ReferenceTestNode("double.line4", "Module.", ["GlobalVariable.double.line2"]),
             ReferenceTestNode("x.line2", "Lambda", ["LocalVariable.x.line2"])]
        ),
        (  # language=Python "lambda function as key"
            """
names = ["a", "abc", "ab", "abcd"]

sort = sorted(names, key=lambda x: len(x))
sort
            """,  # language=none
            [ReferenceTestNode("sorted.line4", "Module.", ["Builtin.sorted"]),
             ReferenceTestNode("len.line4", "Lambda", ["Builtin.len"]),
             ReferenceTestNode("names.line4", "Module.", ["GlobalVariable.names.line2"]),
             ReferenceTestNode("x.line4", "Lambda", ["LocalVariable.x.line4"]),
             ReferenceTestNode("sort.line5", "Module.", ["GlobalVariable.sort.line4"])]
        ),
        (  # language=Python "generator function"
            """
def square_generator(limit):
    for i in range(limit):
        yield i**2

gen = square_generator(5)
for value in gen:
    value
            """,  # language=none
            [ReferenceTestNode("range.line3", "FunctionDef.square_generator", ["Builtin.range"]),
             ReferenceTestNode("square_generator.line6", "Module.", ["GlobalVariable.square_generator.line2"]),
             ReferenceTestNode("limit.line3", "FunctionDef.square_generator", ["Parameter.limit.line2"]),
             ReferenceTestNode("i.line4", "FunctionDef.square_generator", ["LocalVariable.i.line3"]),
             ReferenceTestNode("gen.line7", "Module.", ["GlobalVariable.gen.line6"]),
             ReferenceTestNode("value.line8", "Module.", ["GlobalVariable.value.line7"])]
        ),
        (  # language=Python "import"
            """
import math

math
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python "import with use"
            """
import math

math.pi
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python "import multiple"
            """
import math, sys

math.pi
sys.version
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python "import as"
            """
import math as m

m.pi
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python "import from"
            """
from math import sqrt

sqrt(4)
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python "import from multiple"
            """
from math import pi, sqrt

pi
sqrt(4)
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python "import from as"
            """
from math import sqrt as s

s(4)
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python "import from as multiple"
            """
from math import pi as p, sqrt as s

p
s(4)
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python "dataclass"
            """
from dataclasses import dataclass

@dataclass
class State:
    pass

State()
            """,  # language=none
            [ReferenceTestNode("State.line8", "Module.", ["GlobalVariable.State.line5"])]
        ),
        (  # language=Python "dataclass with default attribute"
            """
from dataclasses import dataclass

@dataclass
class State:
    state: int = 0

State().state
            """,  # language=none
            [ReferenceTestNode("State.line8", "Module.", ["GlobalVariable.State.line5"]),
             ReferenceTestNode("State.state.line8", "Module.", ["ClassVariable.State.state.line6"])]
        ),
        (  # language=Python "dataclass with attribute"
            """
from dataclasses import dataclass

@dataclass
class State:
    state: int

State(0).state
            """,  # language=none
            [ReferenceTestNode("State.line8", "Module.", ["GlobalVariable.State.line5"]),
             ReferenceTestNode("State.state.line8", "Module.", ["ClassVariable.State.state.line6"])]
        ),
        (  # language=Python "dataclass with @property and @setter"
            """
from dataclasses import dataclass

@dataclass
class State:
    _state: int

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value # TODO: what do we do with self._state?

State(10).state
            """,  # language=none
            [ReferenceTestNode("State.line16", "Module.", ["GlobalVariable.State.line5"]),
             ReferenceTestNode("self._state.line10", "FunctionDef.state", ["ClassVariable.State._state.line6"]),
             ReferenceTestNode("value.line14", "FunctionDef.state", ["Parameter.value.line13"]),
             ReferenceTestNode("State.state.line16", "Module.", ["ClassVariable.State._state.line6"])]
        ),
#         (  # language=Python "regex global scope"
#             """
# import re
#
# regex = re.compile(r"^\s*#")
# string = "    # comment"
#
# if regex.match(string) is None:
#     print(string, end="")
#             """,  # language=none
#             []
#         ),
    ],
    ids=[
        "local variable in function scope",
        "parameter in function scope",
        "parameter in function scope with keyword only",
        "parameter in function scope with positional only",
        "parameter in function scope with default value",
        "parameter in function scope with type annotation",
        "parameter in function scope with *args",
        "parameter in function scope with **kwargs",
        "parameter in function scope with *args and **kwargs",
        "two parameters in function scope",
        "global variable in module scope",
        "global variable in class scope",
        "global variable in function scope",
        "global variable in function scope but after definition",
        "global variable in class scope and function scope",
        "access of global variable without global keyword",
        "local variable in function scope shadowing global variable without global keyword",
        "two globals in class scope",
        "class attribute value",
        "class attribute target",
        "chained class attribute",
        "instance attribute value",
        "instance attribute target",
        "instance attribute with parameter",
        "instance attribute with parameter and class attribute",
        "chained class attribute and instance attribute",
        "chained instance attributes",
        "two classes with same signature",
        "getter function with self",
        "getter function with classname",
        "setter function with self",
        "setter function with self different name",
        "setter function with classname different name",
        "if statement global scope",
        "if else statement global scope",
        "if elif else statement global scope",
        "if in statement global scope",
        "for loop with global runtime variable global scope",
        "for loop wih local runtime variable local scope",
        "for loop with local runtime variable global scope",
        "for loop in list comprehension global scope",
        "while loop global scope",
        "match statement global scope",
        "try except statement global scope",
        "array and indexed array global scope",
        "dictionary global scope",
        "map function global scope",
        "two variables",
        "double return",
        "reassignment",
        "vars with comma",
        "f-string",
        "multiple references in one line",
        "walrus operator",
        "variable swap",
        "aliases",
        "builtin function call",
        "function call shadowing builtin function",
        "function call",
        "function call with parameter",
        "function call with keyword parameter",
        "function call as value",
        "nested function call",
        "nested function call with parameter",
        "recursive function call",
        "class instantiation",
        "lambda function",
        "lambda function call",
        "lambda function used as normal function",
        "lambda function as key",
        "generator function",
        "import",
        "import with use",
        "import multiple",
        "import as",
        "import from",
        "import from multiple",
        "import from as",
        "import from as multiple",
        "dataclass",
        "dataclass with default attribute",
        "dataclass with attribute",
        "dataclass with @property and @setter",
    ]
)
# TODO: it is problematic, that the order of references is relevant, since it does not matter in the later usage
#       of these results. Therefore, we should return a set of references instead of a list.
#       For now convert the result to a set for testing purposes
def test_resolve_references(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code)
    transformed_references: list[ReferenceTestNode] = []

    for node in references:
        transformed_references.append(transform_reference_node(node))

    # assert references == expected
    assert transformed_references == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python
            """
class A:
    global glob1
    glob1 = 10
    glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line5", "ClassDef.A", ["ClassVariable.glob1.line4"])]
        ),
        (  # language=Python
            """
def local_global():
    global glob1

    return glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line5", "FunctionDef.local_global", [])]
        ),
        (  # language=Python
            """
class A:
    global glob1
    value = glob1

a = A().value
glob1 = 10
b = A().value
a, b
            """,  # language= None
            [ReferenceTestNode("glob1.line4", "ClassDef.A", [""]),
             ReferenceTestNode("a.line9", "Module.", ["GlobalVariable.a.line6"]),
             ReferenceTestNode("b.line9", "Module.", ["GlobalVariable.b.line8"])]
        ),
        (  # language=Python
            """
def local_global():
    global glob1

    return glob1

lg = local_global()
glob1 = 10
glob1
            """,  # language= None
            ValueError  # TODO: error message
        )  # Problem: we can not check weather a function is called before the global variable is declared since
        # this would need a context-sensitive approach
        # I would suggest to just check if the global variable is declared in the module scope at the cost of loosing precision
        # for now we check if the global variable is declared in the module scope, if it isn't we simply ignore it
    ],
    ids=[
        "new global variable in class scope",
        "new global variable in function scope",
        "new global variable in class scope with outer scope usage",
        "new global variable in function scope with outer scope usage",
    ]
)
def test_resolve_references_error(code: str, expected: list[ReferenceTestNode]) -> None:
    # with pytest.raises(ValueError):
    #     resolve_references(code)

    references = resolve_references(code)
    transformed_references: list[ReferenceTestNode] = []

    for node in references:
        transformed_references.append(transform_reference_node(node))

    # assert references == expected
    assert transformed_references == expected


def transform_reference_node(node: ReferenceNode) -> ReferenceTestNode:
    if isinstance(node.name, MemberAccess | MemberAccessValue | MemberAccessTarget):
        expression = get_base_expression(node.name)
        return ReferenceTestNode(name=f"{node.name.name}.line{expression.lineno}",
                                 scope=f"{node.scope.node.__class__.__name__}.{node.scope.node.name}",
                                 referenced_symbols=[str(ref) for ref in node.referenced_symbols])
    if isinstance(node.scope.node, astroid.Lambda) and not isinstance(node.scope.node, astroid.FunctionDef):
        # TODO: potential astroid bug: isinstance(node.scope.node, astroid.Lambda) is True for astroid.FunctionDef instances
        if isinstance(node.name, astroid.Call):
            return ReferenceTestNode(name=f"{node.name.func.name}.line{node.name.func.lineno}",
                                     scope=f"{node.scope.node.__class__.__name__}",
                                     referenced_symbols=[str(ref) for ref in node.referenced_symbols])
        return ReferenceTestNode(name=f"{node.name.name}.line{node.name.lineno}",
                                 scope=f"{node.scope.node.__class__.__name__}",
                                 referenced_symbols=[str(ref) for ref in node.referenced_symbols])
    if isinstance(node.name, astroid.Call):
        return ReferenceTestNode(name=f"{node.name.func.name}.line{node.name.func.lineno}",
                                 scope=f"{node.scope.node.__class__.__name__}.{node.scope.node.name}",
                                 referenced_symbols=[str(ref) for ref in node.referenced_symbols])
    return ReferenceTestNode(name=f"{node.name.name}.line{node.name.lineno}",
                             scope=f"{node.scope.node.__class__.__name__}.{node.scope.node.name}",
                             referenced_symbols=[str(ref) for ref in node.referenced_symbols])


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (
            """
                glob = 1
                class A:
                    def __init__(self):
                        self.value = 10
                        self.test = 20
                    def f():
                        var1 = 1
                def g():
                    var2 = 2
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope("AssignName.glob", []),
                        SimpleClassScope(
                            "ClassDef.A",
                            [
                                SimpleScope(
                                    "FunctionDef.__init__",
                                    [
                                        SimpleScope("MemberAccess.self.value", []),
                                        SimpleScope("MemberAccess.self.test", []),
                                    ],
                                ),
                                SimpleScope(
                                    "FunctionDef.f",
                                    [SimpleScope("AssignName.var1", [])],
                                ),
                            ],
                            [],
                            ["value", "test"],
                        ),
                        SimpleScope("FunctionDef.g", [SimpleScope("AssignName.var2", [])]),
                    ],
                ),
            ],
        ),
        (
            """
                def function_scope():
                    res = 23
                    return res
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope(
                            "FunctionDef.function_scope",
                            [SimpleScope("AssignName.res", [])],
                        ),
                    ],
                ),
            ],
        ),
        (
            """
                var1 = 10
                def function_scope():
                    res = var1
                    return res
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope("AssignName.var1", []),
                        SimpleScope(
                            "FunctionDef.function_scope",
                            [SimpleScope("AssignName.res", [])],
                        ),
                    ],
                ),
            ],
        ),
        (
            """
                var1 = 10
                def function_scope():
                    global var1
                    res = var1
                    return res
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope("AssignName.var1", []),
                        SimpleScope(
                            "FunctionDef.function_scope",
                            [SimpleScope("AssignName.res", [])],
                        ),
                    ],
                ),
            ],
        ),
        (
            """
                def function_scope(parameter):
                    res = parameter
                    return res
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope(
                            "FunctionDef.function_scope",
                            [
                                SimpleScope("AssignName.parameter", []),
                                SimpleScope("AssignName.res", []),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        (
            """
                class A:
                    class_attr1 = 20

                    def local_class_attr():
                        var1 = A.class_attr1
                        return var1
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleClassScope(
                            "ClassDef.A",
                            [
                                SimpleScope("AssignName.class_attr1", []),
                                SimpleScope(
                                    "FunctionDef.local_class_attr",
                                    [SimpleScope("AssignName.var1", [])],
                                ),
                            ],
                            ["class_attr1"],
                            [],
                        ),
                    ],
                ),
            ],
        ),
        (
            """
                class B:
                    local_class_attr1 = 20
                    local_class_attr2 = 30

                    def __init__(self):
                        self.instance_attr1 = 10

                    def local_instance_attr():
                        var1 = self.instance_attr1
                        return var1
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleClassScope(
                            "ClassDef.B",
                            [
                                SimpleScope("AssignName.local_class_attr1", []),
                                SimpleScope("AssignName.local_class_attr2", []),
                                SimpleScope(
                                    "FunctionDef.__init__",
                                    [SimpleScope("MemberAccess.self.instance_attr1", [])],
                                ),
                                SimpleScope(
                                    "FunctionDef.local_instance_attr",
                                    [SimpleScope("AssignName.var1", [])],
                                ),
                            ],
                            ["local_class_attr1", "local_class_attr2"],
                            ["instance_attr1"],
                        ),
                    ],
                ),
            ],
        ),
        (
            """
                class B:
                    def __init__(self):
                        self.instance_attr1 = 10

                def local_instance_attr():
                    var1 = B().instance_attr1
                    return var1
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleClassScope(
                            "ClassDef.B",
                            [
                                SimpleScope(
                                    "FunctionDef.__init__",
                                    [SimpleScope("MemberAccess.self.instance_attr1", [])],
                                ),
                            ],
                            [],
                            ["instance_attr1"],
                        ),
                        SimpleScope(
                            "FunctionDef.local_instance_attr",
                            [SimpleScope("AssignName.var1", [])],
                        ),
                    ],
                ),
            ],
        ),
        (
            """
                class A:
                    var1 = 10

                    class B:
                        var2 = 20
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleClassScope(
                            "ClassDef.A",
                            [
                                SimpleScope("AssignName.var1", []),
                                SimpleClassScope(
                                    "ClassDef.B",
                                    [SimpleScope("AssignName.var2", [])],
                                    ["var2"],
                                    [],
                                ),
                            ],
                            ["var1"],
                            [],
                        ),
                    ],
                ),
            ],
        ),
        (
            """
                class A:
                    var1 = 10

                class X:
                    var3 = 30

                class B(A, X):
                    var2 = 20
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleClassScope(
                            "ClassDef.A",
                            [SimpleScope("AssignName.var1", [])],
                            ["var1"],
                            []
                        ),
                        SimpleClassScope(
                            "ClassDef.X",
                            [SimpleScope("AssignName.var3", [])],
                            ["var3"],
                            []
                        ),
                        SimpleClassScope(
                            "ClassDef.B",
                            [SimpleScope("AssignName.var2", [])],
                            ["var2"],
                            [],
                            ["ClassDef.A", "ClassDef.X"]
                        ),
                    ],
                ),
            ],
        ),
        (
            """
                def function_scope():
                    var1 = 10

                    class B:
                        var2 = 20
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope(
                            "FunctionDef.function_scope",
                            [
                                SimpleScope("AssignName.var1", []),
                                SimpleClassScope(
                                    "ClassDef.B",
                                    [SimpleScope("AssignName.var2", [])],
                                    ["var2"],
                                    [],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        (
            """
                def function_scope():
                    var1 = 10

                    def local_function_scope():
                        var2 = 20
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope(
                            "FunctionDef.function_scope",
                            [
                                SimpleScope("AssignName.var1", []),
                                SimpleScope(
                                    "FunctionDef.local_function_scope",
                                    [SimpleScope("AssignName.var2", [])],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        (
            """
                import math

                class A:
                    value = math.pi
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope("Import.math", []),
                        SimpleClassScope(
                            "ClassDef.A",
                            [SimpleScope("AssignName.value", [])],
                            ["value"],
                            [],
                        ),
                    ],
                ),
            ],
        ),
        (
            """
                import math, datetime

                a = math.pi + datetime.today()
            """,
            []
        ),
        (
            """
                import math as m

                a = m.pi
            """,
            []
        ),
        (
            """
                from math import pi

                class B:
                    value = pi
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope("ImportFrom.math.pi", []),
                        SimpleClassScope("ClassDef.B", [SimpleScope("AssignName.value", [])], ["value"], []),
                    ],
                ),
            ],
        ),
        (
            """
                from math import pi, e

                a = pi + e
            """,
            []
        ),
        (
            """
                from math import pi as pi_value

                a = pi_value
            """,
            []
        ),
        (
            """
                def function_scope():
                    var1 = 10

                    def local_function_scope():
                        var2 = 20

                        class local_class_scope:
                            var3 = 30

                            def local_class_function_scope():
                                var4 = 40
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope(
                            "FunctionDef.function_scope",
                            [
                                SimpleScope("AssignName.var1", []),
                                SimpleScope(
                                    "FunctionDef.local_function_scope",
                                    [
                                        SimpleScope("AssignName.var2", []),
                                        SimpleClassScope(
                                            "ClassDef.local_class_scope",
                                            [
                                                SimpleScope("AssignName.var3", []),
                                                SimpleScope(
                                                    "FunctionDef.local_class_function_scope",
                                                    [
                                                        SimpleScope(
                                                            "AssignName.var4",
                                                            [],
                                                        ),
                                                    ],
                                                ),
                                            ],
                                            ["var3"],
                                            [],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        (
            """
                from collections.abc import Callable
                from typing import Any

                import astroid

                _EnterAndLeaveFunctions = tuple[
                    Callable[[astroid.NodeNG], None] | None,
                    Callable[[astroid.NodeNG], None] | None,
                ]


                class ASTWalker:
                    additional_locals = []

                    def __init__(self, handler: Any) -> None:
                        self._handler = handler
                        self._cache: dict[type, _EnterAndLeaveFunctions] = {}

                    def walk(self, node: astroid.NodeNG) -> None:
                        self.__walk(node, set())

                    def __walk(self, node: astroid.NodeNG, visited_nodes: set[astroid.NodeNG]) -> None:
                        if node in visited_nodes:
                            raise AssertionError("Node visited twice")
                        visited_nodes.add(node)

                        self.__enter(node)
                        for child_node in node.get_children():
                            self.__walk(child_node, visited_nodes)
                        self.__leave(node)

                    def __enter(self, node: astroid.NodeNG) -> None:
                        method = self.__get_callbacks(node)[0]
                        if method is not None:
                            method(node)

                    def __leave(self, node: astroid.NodeNG) -> None:
                        method = self.__get_callbacks(node)[1]
                        if method is not None:
                            method(node)

                    def __get_callbacks(self, node: astroid.NodeNG) -> _EnterAndLeaveFunctions:
                        klass = node.__class__
                        methods = self._cache.get(klass)

                        if methods is None:
                            handler = self._handler
                            class_name = klass.__name__.lower()
                            enter_method = getattr(handler, f"enter_{class_name}", getattr(handler, "enter_default", None))
                            leave_method = getattr(handler, f"leave_{class_name}", getattr(handler, "leave_default", None))
                            self._cache[klass] = (enter_method, leave_method)
                        else:
                            enter_method, leave_method = methods

                        return enter_method, leave_method

            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope("ImportFrom.collections.abc.Callable", []),
                        SimpleScope("ImportFrom.typing.Any", []),
                        SimpleScope("Import.astroid", []),
                        SimpleScope("AssignName._EnterAndLeaveFunctions", []),
                        SimpleClassScope(
                            "ClassDef.ASTWalker",
                            [
                                SimpleScope("AssignName.additional_locals", []),
                                SimpleScope(
                                    "FunctionDef.__init__",
                                    [
                                        SimpleScope("AssignName.handler", []),
                                        SimpleScope("MemberAccess.self._handler", []),
                                        SimpleScope("MemberAccess.self._cache", []),
                                    ],
                                ),
                                SimpleScope(
                                    "FunctionDef.walk",
                                    [
                                        SimpleScope("AssignName.node", []),
                                    ],
                                ),
                                SimpleScope(
                                    "FunctionDef.__walk",
                                    [
                                        SimpleScope("AssignName.node", []),
                                        SimpleScope("AssignName.visited_nodes", []),
                                        SimpleScope("AssignName.child_node", []),
                                    ],
                                ),
                                SimpleScope(
                                    "FunctionDef.__enter",
                                    [
                                        SimpleScope("AssignName.node", []),
                                        SimpleScope("AssignName.method", []),
                                    ],
                                ),
                                SimpleScope(
                                    "FunctionDef.__leave",
                                    [
                                        SimpleScope("AssignName.node", []),
                                        SimpleScope("AssignName.method", []),
                                    ],
                                ),
                                SimpleScope(
                                    "FunctionDef.__get_callbacks",
                                    [
                                        SimpleScope("AssignName.node", []),
                                        SimpleScope("AssignName.klass", []),
                                        SimpleScope("AssignName.methods", []),
                                        SimpleScope("AssignName.handler", []),
                                        SimpleScope("AssignName.class_name", []),
                                        SimpleScope("AssignName.enter_method", []),
                                        SimpleScope("AssignName.leave_method", []),
                                        SimpleScope("AssignName.enter_method", []),
                                        SimpleScope("AssignName.leave_method", []),
                                    ],
                                ),
                            ],
                            ["additional_locals"],
                            ["_handler", "_cache"],
                        ),
                    ],
                ),
            ],
        ),
        (
            """
                a = b
            """,
            [SimpleScope("Module", [SimpleScope("AssignName.a", [])])],
        )
    ],
    ids=[
        "Seminar Example",
        "Function Scope",
        "Function Scope with variable",
        "Function Scope with global variable",
        "Function Scope with Parameter",
        "Class Scope with class attribute and Class function",
        "Class Scope with instance attribute and Class function",
        "Class Scope with instance attribute and Modul function",
        "Class Scope within Class Scope",
        "Class Scope with subclass",
        "Class Scope within Function Scope",
        "Function Scope within Function Scope",
        "Import Scope",
        "Import Scope with multiple imports",
        "Import Scope with alias",
        "Import From Scope",
        "Import From Scope with multiple imports",
        "Import From Scope with alias",
        "Complex Scope",
        "ASTWalker",
        "AssignName",
    ],  # TODO: add tests for lambda and generator expressions
)
def test_get_scope(code: str, expected: list[SimpleScope | SimpleClassScope]) -> None:
    result = _get_module_data(code).scope
    # assert result == expected
    assert_test_get_scope(result, expected)


def assert_test_get_scope(result: Scope, expected: list[SimpleScope | SimpleClassScope]) -> None:
    transformed_result = [
        transform_result(node) for node in result
    ]  # The result and the expected data is simplified to make the comparison easier
    assert transformed_result == expected


def transform_result(node: Scope | ClassScope) -> SimpleScope | SimpleClassScope:
    if node.children is not None:
        if isinstance(node, ClassScope):
            return SimpleClassScope(
                to_string(node.node),
                [transform_result(child) for child in node.children],
                [to_string_class(child) for child in node.class_variables],
                [to_string_class(child) for child in node.instance_variables],
                [to_string_class(child) for child in node.super_classes],
            )
        return SimpleScope(to_string(node.node), [transform_result(child) for child in node.children])
    else:
        return SimpleScope(to_string(node.node), [])


def to_string(node: astroid.NodeNG) -> str:
    if isinstance(node, astroid.Module):
        return "Module"
    elif isinstance(node, astroid.ClassDef | astroid.FunctionDef | astroid.AssignName):
        return f"{node.__class__.__name__}.{node.name}"
    elif isinstance(node, astroid.AssignAttr):
        return f"{node.__class__.__name__}.{node.attrname}"
    elif isinstance(node, MemberAccess):
        result = transform_member_access(node)
        return f"MemberAccess.{result}"
    elif isinstance(node, astroid.Import):
        return f"{node.__class__.__name__}.{node.names[0][0]}"  # TODO: handle multiple imports and aliases
    elif isinstance(node, astroid.ImportFrom):
        return f"{node.__class__.__name__}.{node.modname}.{node.names[0][0]}"  # TODO: handle multiple imports and aliases
    elif isinstance(node, astroid.Name):
        return f"{node.__class__.__name__}.{node.name}"
    raise NotImplementedError(f"Unknown node type: {node.__class__.__name__}")


def to_string_class(node: astroid.NodeNG) -> str:
    if isinstance(node, astroid.AssignAttr):
        return f"{node.attrname}"
    elif isinstance(node, astroid.AssignName):
        return f"{node.name}"
    elif isinstance(node, ClassScope):
        return f"{node.node.__class__.__name__}.{node.node.name}"
    raise NotImplementedError(f"Unknown node type: {node.__class__.__name__}")
