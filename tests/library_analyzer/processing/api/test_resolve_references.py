from __future__ import annotations

from dataclasses import dataclass

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
    _get_name_nodes,
    _get_module_data,
    ReferenceNode,
    _create_references,
    _find_references,
    resolve_references,
)


@dataclass
class SimpleScope:
    node_name: str
    children: list[SimpleScope]


@dataclass
class SimpleClassScope(SimpleScope):
    class_variables: list[str]
    instance_variables: list[str]
    super_class: list[str] | None = None


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
    names_list = _get_name_nodes(code)

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
            astroid.Import(names=[("numpy", None), ("sys", None)], lineno=1, col_offset=0, parent=astroid.Module("my_module")),
            "my_module.numpy.1.0",  # TODO: this is a problem since one node can contain multiple imports and therefore each one needs its own id
        ),
        (
            astroid.Import(names=[("numpy", "np")], lineno=1, col_offset=0, parent=astroid.Module("my_module")),
            "my_module.np.1.0",
        ),
        (
            astroid.ImportFrom(fromname='math', names=[('sqrt', None)], level=0, lineno=1, col_offset=0, parent=astroid.Module("my_module")),
            "my_module.sqrt.1.0",
        ),
        (
            astroid.ImportFrom(fromname='math', names=[('sqrt', 's')], level=0, lineno=1, col_offset=0, parent=astroid.Module("my_module")),
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
def test_create_references(node: list[astroid.Name | astroid.AssignName], expected) -> None:
    result = _create_references(node)[0]
    assert result == expected
    assert_reference_list_equal(result, expected)


# TODO: rewrite this test since the results are no longer just prototypes


def assert_reference_list_equal(result: list[ReferenceNode], expected: list[ReferenceNode]) -> None:
    """ The result data as well as the expected data in this test is simplified, so it is easier to compare the results.
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
    """ A simple dataclass to store the data for the reference tests"""
    name: str
    scope: str
    referenced_symbols: list[str]


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python
            """
def local_var():
    var1 = 1
    return var1
            """,  # language= None
            [ReferenceTestNode("var1.line4", "FunctionDef.local_var", ["LocalVariable.var1.line3"])]
        ),
        (  # language=Python
            """
def local_parameter(pos_arg):
    return 2 * pos_arg
            """,  # language= None
            [ReferenceTestNode("pos_arg.line3", "FunctionDef.local_parameter", ["Parameter.pos_arg.line2"])]
        ),
        (  # language=Python
            """
def local_parameter(*, key_arg_only):
    return 2 * key_arg_only
            """,  # language= None
            [ReferenceTestNode("key_arg_only.line3", "FunctionDef.local_parameter", ["Parameter.key_arg_only.line2"])]
        ),        (  # language=Python
            """
def local_parameter(pos_arg_only, /):
    return 2 * pos_arg_only
            """,  # language= None
            [ReferenceTestNode("pos_arg_only.line3", "FunctionDef.local_parameter", ["Parameter.pos_arg_only.line2"])]
        ),
        (  # language=Python
            """
def local_parameter(def_arg=10):
    return def_arg
            """,  # language= None
            [ReferenceTestNode("def_arg.line3", "FunctionDef.local_parameter", ["Parameter.def_arg.line2"])]
        ),
        (  # language=Python
            """
def local_parameter(*args):
    return args
            """,  # language= None
            [ReferenceTestNode("args.line3", "FunctionDef.local_parameter", ["Parameter.args.line2"])]
        ),
        (  # language=Python
            """
def local_parameter(**kwargs):
    return kwargs
            """,  # language= None
            [ReferenceTestNode("kwargs.line3", "FunctionDef.local_parameter", ["Parameter.kwargs.line2"])]
        ),
        (  # language=Python
            """
def local_double_parameter(a, b):
    return a, b
            """,  # language= None
            [ReferenceTestNode("a.line3", "FunctionDef.local_double_parameter", ["Parameter.a.line2"]),
             ReferenceTestNode("b.line3", "FunctionDef.local_double_parameter", ["Parameter.b.line2"])]
        ),
        (  # language=Python
            """
glob1 = 10
print(glob1)
            """,  # language= None
            [ReferenceTestNode("glob1.line3", "Module.", ["GlobalVariable.glob1.line2"])]
        ),
        (  # language=Python
            """
glob1 = 10
class A:
    global glob1
    print(glob1)
            """,  # language= None
            [ReferenceTestNode("glob1.line5", "ClassDef.A", ["GlobalVariable.glob1.line2"])]
        ),
        (  # language=Python
            """
glob1 = 10
def local_global():
    global glob1

    return glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line6", "FunctionDef.local_global", ["GlobalVariable.glob1.line2"])]
        ),
        (  # language=Python
            """
def local_global():
    global glob1

    return glob1  # TODO: this is not detected as a global variable, because the node is not added to the module.globals when looking at this functiondef

glob1 = 10  # TODO: this can be fixed by removing [:reference_list.index(reference)] in line 580
            """,  # language= None
            [ReferenceTestNode("glob1.line5", "FunctionDef.local_global", ["GlobalVariable.glob1.line7"])]
        ),
        (  # language=Python
            """
glob1 = 10
class A:
    global glob1
    print(glob1)

def local_global():
    global glob1

    return glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line5", "ClassDef.A", ["GlobalVariable.glob1.line2"]),
             ReferenceTestNode("glob1.line10", "FunctionDef.local_global", ["GlobalVariable.glob1.line2"])]
        ),
        (  # language=Python
            """
glob1 = 10
def local_global_access():
    return glob1  # TODO: this is not detected as a node inside the function scope, which is correct
            """,  # language= None
            [ReferenceTestNode("glob1.line4", "FunctionDef.local_global_access", ["GlobalVariable.glob1.line2"])]
        ),
        (  # language=Python
            """
glob1 = 10
def local_global_shadow():
    glob1 = 20

    return glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line6", "FunctionDef.local_global_shadow",
                               ["GlobalVariable.glob1.line2", "LocalVariable.glob1.line4"])]
        ),
        (  # language=Python
            """
glob1 = 10
glob2 = 20
class A:
    global glob1, glob2
    print(glob1, glob2)
            """,  # language= None
            [ReferenceTestNode("glob1.line6", "ClassDef.A", ["GlobalVariable.glob1.line2"]),
             ReferenceTestNode("glob2.line6", "ClassDef.A", ["GlobalVariable.glob2.line3"])]
        ),
        (  # language=Python
            """
class A:
    class_attr1 = 20

print(A.class_attr1)
            """,  # language=none
            [ReferenceTestNode("A.class_attr1.line5", "Module.", ["ClassVariable.A.class_attr1.line3"])]
        ),
        (  # language=Python
            """
class A:
    class_attr1 = 20

A.class_attr1 = 30
print(A.class_attr1)
            """,  # language=none
            [ReferenceTestNode("A.class_attr1.line6", "Module.", ["ClassVariable.A.class_attr1.line5",
                                                                  "ClassVariable.A.class_attr1.line3"])]
        ),
        (  # language=Python
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
        (  # language=Python
            """
class B:
    def __init__(self):
        self.instance_attr1 = 10

b = B()
b.instance_attr1 = 1
print(b.instance_attr1)
            """,  # language=none
            [ReferenceTestNode("B.line6", "Module.", ["GlobalVariable.B.line2"]),
             ReferenceTestNode("b.line7", "Module.", ["GlobalVariable.b.line6"]),
             ReferenceTestNode("b.instance_attr1.line8", "Module.", ["GlobalVariable.b.instance_attr1.line7",
                                                                     "InstanceVariable.b.instance_attr1.line4"])
             ]
        ),
        (  # language=Python
            """
class B:
    def __init__(self, name):
        self.name = name

b = B("test")
print(b.name)
            """,  # language=none
            [ReferenceTestNode("B.line6", "Module.", ["GlobalVariable.B.line2"]),
             ReferenceTestNode("b.line7", "Module.", ["GlobalVariable.b.line6"]),
             ReferenceTestNode("b.name.line7", "Module.", ["InstanceVariable.b.name.line4"])]
        ),
        (  # language=Python
            """
class C:
    state: int = 0

    def get_state(self):
        return self.state
            """,  # language= None
            [ReferenceTestNode("self.state.line6", "FunctionDef.get_state", ["ClassVariable.C.state.line3"])]
        ),
        (  # language=Python
            """
class C:
    state: int = 0

    def get_state(self):
        return C.state
            """,  # language= None
            [ReferenceTestNode("C.state.line6", "FunctionDef.get_state", ["ClassVariable.C.state.line3"])]
        ),
        (  # language=Python
            """
class C:
    state: int = 0

    def set_state(self, state):
        self.state = state
            """,  # language= None
            []  # TODO
        ),
        (  # language=Python
            """
class C:
    state: int = 0

    def set_state(self, state):
        C.state = state
            """,  # language= None
            []  # TODO
        ),
        (  # language=Python
            """
var1 = 10
if var1 > 0:
    print(var1)
        """,  # language=none
            [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line4", "Module.", ["GlobalVariable.var1.line2"])]
        ),
        (  # language=Python
            """
var1 = 10
if var1 > 0:
    print(var1)
else:
    print(2 * var1)
        """,  # language=none
            [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line4", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line6", "Module.", ["GlobalVariable.var1.line2"])]
        ),
        (  # language=Python
            """
var1 = 10
if var1 > 0:
    print(var1)
elif var1 < 0:
    print(-var1)
else:
    print(var1)
        """,  # language=none
            [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line4", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line5", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line6", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line8", "Module.", ["GlobalVariable.var1.line2"])]
        ),
        (  # language=Python
            """
var1 = 10
for i in range(var1):
    print(i)
        """,  # language=none
            [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("i.line4", "Module.", ["GlobalVariable.i.line3"])]  # TODO: do we really tread i as a global variable? -yes implement it
        ),
        (  # language=Python
            """
var1 = 10
def func1():
    for i in range(var1):
        print(i)
        """,  # language=none
            [ReferenceTestNode("var1.line4", "FunctionDef.func1", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("i.line5", "FunctionDef.func1", ["LocalVariable.i.line4"])]
        ),
        (  # language=Python
            """
nums = ["one", "two", "three"]
for num in nums:
    print(num)
        """,  # language=none
            [ReferenceTestNode("nums.line3", "Module.", ["GlobalVariable.nums.line2"]),
             ReferenceTestNode("num.line4", "Module.", ["GlobalVariable.num.line3"])]
        ),
        (  # language=Python
            """
nums = ["one", "two", "three"]
lengths = [len(num) for num in nums]  # TODO: list comprehension should get its own scope (LATER: for further improvement)
print(lengths)
        """,  # language=none
            [ReferenceTestNode("nums.line3", "Module.", ["GlobalVariable.nums.line2"]),
             ReferenceTestNode("num.line3", "List.", ["LocalVariable.num.line3"]),
             ReferenceTestNode("lengths.line4", "Module.", ["GlobalVariable.lengths.line3"])]
        ),
        (  # language=Python
            """
var1 = 10
while var1 > 0:
    print(var1)
        """,  # language=none
            [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line4", "Module.", ["GlobalVariable.var1.line2"])]
        ),
        (  # language=Python
            """
var1 = 10
match var1:
    case 1: print(1)
    case 2: print(2)
    case (a, b): print(var1, a, b)  # TODO: Match should get its own scope (LATER: for further improvement)  maybe add its parent
        """,  # language=none
            [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line6", "Module.", ["GlobalVariable.var1.line2"])]
        ),
        (  # language=Python
            """
try:
    num1 = int(input("Enter a number: "))
    num2 = int(input("Enter another number: "))
    result = num1 / num2
    print("Result:", result)
except ValueError:
    print("Invalid input. Please enter valid numbers.")
except ZeroDivisionError as zde:   # TODO: zde is not detected as a global variable # TODO: Except should get its own scope (LATER: for further improvement)
    print("Error: Cannot divide by zero.")
    print(zde)
        """,  # language=none
            []
        ),
        (  # language=Python
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
        (  # language=Python
            """
dictionary = {"key1": 1, "key2": 2}
dictionary["key1"] = 0
            """,  # language=none
            [ReferenceTestNode("dictionary.line3", "Module.", ["GlobalVariable.dictionary.line2"])]
        ),
        (  # language=Python
            """
x = 10
y = 20
print(x + y)
            """,  # language=none
            [ReferenceTestNode("x.line4", "Module.", ["GlobalVariable.x.line2"]),
             ReferenceTestNode("y.line4", "Module.", ["GlobalVariable.y.line3"])]
        ),
        (  # language=Python
            """
def double_return(a, b):
    return a, b

x, y = double_return(10, 20)

print(x)
print(y)
            """,  # language=none
            [ReferenceTestNode("a.line3", "FunctionDef.double_return", ["Parameter.a.line2"]),
             ReferenceTestNode("b.line3", "FunctionDef.double_return", ["Parameter.b.line2"]),
             ReferenceTestNode("x.line7", "Module.", ["GlobalVariable.x.line5"]),
             ReferenceTestNode("y.line8", "Module.", ["GlobalVariable.y.line5"])]
        ),
        (  # language=Python
            """
x = 10
x = 20
print(x)
            """,  # language=none
            [ReferenceTestNode("x.line4", "Module.", ["GlobalVariable.x.line2", "GlobalVariable.x.line3"])]
        ),
        (  # language=Python
            """
x = 10
y = 20
print(x, y)
            """,  # language=none
            [ReferenceTestNode("x.line4", "Module.", ["GlobalVariable.x.line2"]),
             ReferenceTestNode("y.line4", "Module.", ["GlobalVariable.y.line3"])]
        ),
        (  # language=Python
            """
x = 10
y = 20
print(f"{x} + {y} = {x + y}")
            """,  # language=none
            [ReferenceTestNode("x.line4", "Module.", ["GlobalVariable.x.line2"]),
             ReferenceTestNode("y.line4", "Module.", ["GlobalVariable.y.line3"]),
             ReferenceTestNode("x.line4", "Module.", ["GlobalVariable.x.line2"]),
             ReferenceTestNode("y.line4", "Module.", ["GlobalVariable.y.line3"])]
        ),
        (  # language=Python
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
        (  # language=Python
            """
x = 10

class A:
    x = 30

    def f(self):
        print(x)

a = A()
a.f()
print(x)
            """,  # language=none
            []
        ),
        (  # language=Python
            """
a = 10
b = a
c = b
print(c)
            """,  # language=none
            [ReferenceTestNode("a.line3", "Module.", ["GlobalVariable.a.line2"]),
             ReferenceTestNode("b.line4", "Module.", ["GlobalVariable.b.line3"]),
             ReferenceTestNode("c.line5", "Module.", ["GlobalVariable.c.line4"])]
        ),
        (  # language=Python
            """
def f():
    pass

f()
            """,  # language=none
            [ReferenceTestNode("f.line5", "Module.", ["GlobalVariable.f.line2"])]
        ),
        (  # language=Python
            """
class F:
    pass

F()
            """,  # language=none
            [ReferenceTestNode("F.line5", "Module.", ["GlobalVariable.F.line2"])]
        ),
        (  # language=Python
            """
import math

print(math.pi)
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python
            """
import math, sys

print(math.pi)
print(sys.version)
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python
            """
import math as m

print(m.pi)
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python
            """
from math import sqrt

print(sqrt(4))
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python
            """
from math import pi, sqrt

print(pi)
print(sqrt(4))
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python
            """
from math import sqrt as s

print(s(4))
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python
            """
from math import pi as p, sqrt as s

print(p)
print(s(4))
            """,  # language=none
            [""]  # TODO
        ),

    ],
    ids=[
        "local variable in function scope",
        "parameter in function scope",
        "parameter in function scope with keyword only",
        "parameter in function scope with positional only",
        "parameter in function scope with default value",
        "parameter in function scope with *args",
        "parameter in function scope with **kwargs",
        "two parameters in function scope",
        "global variable in module scope",
        "global variable in class scope",
        "global variable in function scope",
        "global variable in function scope but after definition",
        "global variable in class scope and function scope",
        "access of global variable without global keyword",
        "local variable in function scope shadowing global variable without global keyword",
        "two globals in class scope",  # TODO: all below are not supported yet
        "class attribute value",
        "class attribute target",
        "instance attribute value",
        "instance attribute target",
        "instance attribute with parameter",
        "getter function with self",
        "getter function with classname",
        "setter function with self",
        "setter function with classname",
        "if statement global scope",
        "if else statement global scope",
        "if elif else statement global scope",
        "for loop with global runtime variable global scope",
        "for loop wih local runtime variable local scope",
        "for loop with local runtime variable global scope",
        "for loop in list comprehension global scope",
        "while loop global scope",
        "match statement global scope",
        "try except statement global scope",
        "array and indexed array global scope",
        "dictionary global scope",
        "two variables",
        "double return",
        "reassignment",
        "double print",
        "f-string",
        "multiple references in one line",
        "different scopes",
        "aliases",
        "function call",
        "class instantiation",
        "import",
        "import multiple",
        "import as",
        "import from",
        "import from multiple",
        "import from as",
        "import from as multiple",
    ]  # TODO: testcases for calls and imports
)
def test_resolve_references(code, expected):
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
    print(glob1)
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
print(a, b)
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
print(glob1)
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
def test_resolve_references_error(code, expected):
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
        return ReferenceTestNode(name=f"{node.name.name}.line{node.name.expression.lineno}",
                                 scope=f"{node.scope.node.__class__.__name__}.{node.scope.node.name}",
                                 referenced_symbols=[str(ref) for ref in node.referenced_symbols])
    return ReferenceTestNode(name=f"{node.name.name}.line{node.name.lineno}",
                             scope=f"{node.scope.node.__class__.__name__}.{node.scope.node.name}",
                             referenced_symbols=[str(ref) for ref in node.referenced_symbols])


@dataclass
class SimpleScope:
    node_name: str | None
    children: list[SimpleScope] | None


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
        ), (
            """
                class A:
                    var1 = 10

                class B(A):
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
                                    "ClassDef.B",
                                    [SimpleScope("AssignName.var2", [])],
                                    ["var2"],
                                    [],
                                    ["ClassDef.A"],
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
        "a"
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
    raise NotImplementedError(f"Unknown node type: {node.__class__.__name__}")
