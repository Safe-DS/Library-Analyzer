from __future__ import annotations

from dataclasses import dataclass

import astroid
import pytest
from library_analyzer.processing.api import (
    ClassScope,
    MemberAccess,
    Scope,
    NodeID,
    _calc_node_id,
    _get_name_nodes,
    _get_scope,
    ReferenceNode,
    _create_references,
    _find_references,
)


@dataclass
class SimpleScope:
    node_name: str
    children: list[SimpleScope]


@dataclass
class SimpleClassScope(SimpleScope):
    class_variables: list[str]
    instance_variables: list[str]


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
                def aug_assign():
                    var1 += 1
            """,
            ["AssignName.var1"],
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
        "Assign Chain",
        "Assign Chain Reversed",
        "AugAssign",
        "AssignAttr",
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
    ],
    ids=[
        "Module",
        "ClassDef (parent Module)",
        "FunctionDef (parent ClassDef)",
        "FunctionDef (parent ClassDef, parent Module)",
        "AssignName (parent FunctionDef)",
        "Name (parent FunctionDef)",
        "Name (parent FunctionDef, parent ClassDef, parent Module)",
        # "Name incorrect (wrong parent)",
        # "Name incorrect (wrong name)",
        # "Name incorrect (wrong lineno)",
        # "Name incorrect (wrong col_offset)",
        # TODO: see above
    ],
)
def test_calc_function_id_new(
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
                           Scope(astroid.Name("var1", lineno=1, col_offset=4), NodeID(astroid.Module(""), "var1", 1, 4), []))]
        ),
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
             astroid.Name("var2", lineno=2, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
             astroid.Name("var3", lineno=30, col_offset=4,
                          parent=astroid.FunctionDef("func2", lineno=1, col_offset=0))],
            [ReferenceNode(astroid.Name("var1", lineno=1, col_offset=4),
                           Scope(astroid.Name("var1", lineno=1, col_offset=4), NodeID(astroid.Module(""), "var1", 1, 4), [])),
             ReferenceNode(astroid.Name("var2", lineno=2, col_offset=4),
                           Scope(astroid.Name("var2", lineno=2, col_offset=4), NodeID(astroid.Module(""), "var2", 2, 4), [])),
             ReferenceNode(astroid.Name("var3", lineno=30, col_offset=4),
                           Scope(astroid.Name("var3", lineno=30, col_offset=4), NodeID(astroid.Module(""), "var3", 30, 4), []))]
        ),
        (
            [astroid.AssignName("var1", lineno=12, col_offset=42,
                                parent=astroid.FunctionDef("func1", lineno=1, col_offset=0))],
            [ReferenceNode(astroid.AssignName("var1", lineno=12, col_offset=42),
                           Scope(astroid.AssignName("var1", lineno=12, col_offset=42), NodeID(astroid.Module(""), "var1", 12, 42), []))]
        ),
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
             astroid.AssignName("var2", lineno=1, col_offset=8,
                                parent=astroid.FunctionDef("func1", lineno=1, col_offset=0))],
            [ReferenceNode(astroid.Name("var1", lineno=1, col_offset=4),
                           Scope(astroid.Name("var1", lineno=1, col_offset=4), NodeID(astroid.Module(""), "var1", 1, 4), [])),
             ReferenceNode(astroid.AssignName("var2", lineno=1, col_offset=8),
                           Scope(astroid.AssignName("var2", lineno=1, col_offset=8), NodeID(astroid.Module(""), "var2", 1, 8), []))]
        ),
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.ClassDef("MyClass", lineno=1, col_offset=0))],
            [ReferenceNode(astroid.Name("var1", lineno=1, col_offset=4),
                           Scope(astroid.Name("var1", lineno=1, col_offset=4), NodeID(astroid.Module(""), "var1", 1, 4), []))]
        ),
        (
            [astroid.Name("glob", lineno=1, col_offset=4, parent=astroid.Module("mod"))],
            [ReferenceNode(astroid.Name("glob", lineno=1, col_offset=4),
                           Scope(astroid.Name("glob", lineno=1, col_offset=4), NodeID(astroid.Module("mod"), "glob", 1, 4), []))]
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
        ReferenceNode(name.name.name, name.scope.children.__class__.__name__, name.referenced_symbols) for name in result]
    expected = [
        ReferenceNode(name.name.name, name.scope.children.__class__.__name__, name.referenced_symbols) for name in expected]
    assert result == expected

# TODO: test this when resolve reference is implemented (disabled for now due to test failures)
# def test_add_potential_value_reference() -> None:
#     raise NotImplementedError("Test not implemented")

# TODO: test this when resolve reference is implemented (disabled for now due to test failures)
# def test_add_potential_target_reference() -> None:
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

local_var()
            """,  # language= None
            [ReferenceTestNode("var1", "FunctionDef.local_var", ["LocalVariable.var1.line3"])]
        ),
        (  # language=Python
            """
def local_parameter(pos_arg):
    return 2 * pos_arg

local_parameter(10)
            """,  # language= None
            [ReferenceTestNode("pos_arg", "FunctionDef.local_parameter", ["Parameter.pos_arg.line2"])]
        ),
        (  # language=Python
            """
def local_parameter(def_arg=10):
    return def_arg

local_parameter()
            """,  # language= None
            [ReferenceTestNode("def_arg", "FunctionDef.local_parameter", ["Parameter.def_arg.line2"])]
        ),
        (  # language=Python
            """
def local_parameter(*args):
    return args

local_parameter()
            """,  # language= None
            []  # TODO: how to deal with *args?
        ),
        (  # language=Python
            """
def local_parameter(**kwargs):
    return kwargs

local_parameter()
            """,  # language= None
            []  # TODO: how to deal with **kwargs?
        ),
        (  # language=Python
            """
glob1 = 10
print(glob1)
            """,  # language= None
            [ReferenceTestNode("glob1", "Module.", ["GlobalVariable.glob1.line2"])]
        ),
        (  # language=Python
            """
glob1 = 10
class A:
    global glob1
    a_value = glob1

A()
            """,  # language= None
            [ReferenceTestNode("glob1", "ClassDef.A", ["GlobalVariable.glob1.line2"])]
        ),
        # this test is no duplicate of the previous one, since the global value is used in a different way
        # this case leads to a problem since no reference is created for the global value since it is never assigned
        (  # language=Python
            """
glob1 = 10
class A:
    global glob1
    print(glob1)

A()
            """,  # language= None
            [ReferenceTestNode("glob1", "ClassDef.A", ["GlobalVariable.glob1.line2"])]
        ),
        (  # language=Python
            """
glob1 = 10
def local_global():
    global glob1

    return glob1

local_global()
            """,  # language= None
            [ReferenceTestNode("glob1", "FunctionDef.local_global", ["GlobalVariable.glob1.line2"])]
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

A()
local_global()
            """,  # language= None
            [ReferenceTestNode("glob1", "ClassDef.A", ["GlobalVariable.glob1.line2"]),
                ReferenceTestNode("glob1", "FunctionDef.local_global", ["GlobalVariable.glob1.line2"])]
        ),
        (  # language=Python
            """
class A:
    global glob1
    glob1 = 10
    print(glob1)
            """,  # language= None
            []  # TODO: is this allowed?
        ),
        (  # language=Python
            """
def local_global():
    global glob1

    return glob1

local_global()
            """,  # language= None
            []  # TODO: is this allowed?
        ),
        (  # language=Python
            """
class A:
    global glob1
    value = glob1

a = A().value
glob1 = 10
print(glob1)
            """,  # language= None
            []  # TODO
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
            []  # TODO
        ),
        (  # language=Python
            """
glob1 = 10
def local_global_access():
    return glob1

local_global_access() # returns 10
            """,  # language= None
            [ReferenceTestNode("glob1", "FunctionDef.local_global_access", ["GlobalVariable.glob1.line2"])]
        ),  # TODO: is this ["GlobalVariable.glob1.line2"] correct?
        (  # language=Python
            """
glob1 = 10
def local_global_shadow():
    glob1 = 20

    return glob1

local_global_shadow() # returns 20
            """,  # language= None
            [ReferenceTestNode("glob1", "FunctionDef.local_global_shadow", ["GlobalVariable.glob1.line2", "LocalVariable.glob1.line4"])]
        ),
        (  # language=Python
            """
glob1 = 10
glob2 = 20
class A:
    global glob1, glob2
    print(glob1, glob2)

A()
            """,  # language= None
            [ReferenceTestNode("glob1", "ClassDef.A", ["GlobalVariable.glob1.line2"]),
             ReferenceTestNode("glob2", "ClassDef.A", ["GlobalVariable.glob2.line3"])]
        ),
        (  # language=Python
            """
x =1

def f():
    x = 2
    global x
    x = 3

f()
print(x)
            """,  # language=none
            []  # TODO: some error should be raised here
        ),
#         (  # language=Python
#             """
# class A:
#     class_attr1 = 20
#
# def local_class_attr():
#     var1 = A.class_attr1
#     return var1
#             """,
#             []
#         ),
        (  # language=Python
            """
class A:
    class_attr1 = 20

print(A.class_attr1)  # TODO: right now this is not detected as a reference, since MemberAccess is not supported yet
            """,  # language=none
            [ReferenceTestNode("class_attr1", "ClassDef.A", ["ClassAttribute.class_attr1.line2"])]
        ),
        (  # language=Python
            """
class A:
    class_attr1 = 20

A.class_attr1 = 30 # TODO: right now this is not detected as a reference, since MemberAccess is not supported yet
print(A.class_attr1)
            """,  # language=none
            [""]
        ),
        (  # language=Python
            """
class B:
    def __init__(self):
        self.instance_attr1 = 10

b = B()
var1 = b.instance_attr1
print(var1)
            """,  # language=none
            []
        ),
        (  # language=Python
            """
var1 = 10
if var1 > 0:
    print(var1)
else:
    print(-var1)
        """,  # language=none
            []
        ),
        (  # language=Python
            """
arr = [1, 2, 3]
arr[0] = 10
print(arr)
            """,  # language=none
            []
        ),
        (  # language=Python
            """
x = 10
y = 20
print(x + y)
            """,  # language=none
            [ReferenceTestNode("x", "Module.", ["GlobalVariable.x.line2"]), ReferenceTestNode("y", "Module.", ["GlobalVariable.y.line3"])]
        ),
        (  # language=Python
            """
def local_double_return(a, b):
    return a, b

x, y = local_double_return(10, 20)

print(x)
print(y)
            """,  # language=none
            []
        ),
        (  # language=Python
            """
x = 10
x = 20
print(x)
            """,  # language=none
            [ReferenceTestNode("x", "Module.", ["GlobalVariable.x.line2", "GlobalVariable.x.line3"])]
        ),
        (  # language=Python
            """
x = 10

class A:
    x = 30

    def f(self):
        print(x)

    x = 50
a = A()
a.f()
print(x)
            """,  # language=none
            []
        ),
    ],
    ids=[
        "local variable in function scope",
        "parameter in function scope",
        "parameter in function scope with default value",
        "parameter in function scope with *args",
        "parameter in function scope with **kwargs",
        "global variable in module scope",
        "global variable in class scope assignment",
        "global variable in class scope print",
        "global variable in function scope",
        "global variable in class scope and function scope",
        "new global variable in class scope",
        "new global variable in function scope",
        "new global variable in class scope with outer scope usage",
        "new global variable in function scope with outer scope usage",
        "access of global variable without global keyword",
        "local variable in function scope shadowing global variable without global keyword",
        "two globals in class scope",
        "global with wrong usage",  # TODO: all below are not supported yet
        "class attribute",
        "class attribute with overwriting",
        "instance attribute as global variable",
        "global path",
        "global array",
        "two variables",
        "double return",
        "reassignment",
        "different scopes",
    ]  # TODO: Right now there are no testcases where a variable is only declared outside of its scope
)
def test_find_references(code, expected):
    scope = _get_scope(code)
    all_names_list = _get_name_nodes(code)

    references: list[list[ReferenceNode]] = []
    transformed_references: list[list[ReferenceTestNode]] = []

    for name_node in all_names_list:
        references.append(_find_references(name_node, all_names_list, scope[0], scope[1], scope[2], scope[3]))

    for node in references[0]:
        transformed_references.append(transform_reference_node(node))

    # assert references == expected
    assert transformed_references == expected


def transform_reference_node(node: ReferenceNode) -> ReferenceTestNode:
    return ReferenceTestNode(node.name.name, f"{node.scope.node.__class__.__name__}.{node.scope.node.name}", [str(ref) for ref in node.referenced_symbols])


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
                                        SimpleScope("AssignAttr.value", []),
                                        SimpleScope("AssignAttr.test", []),
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
                                    [SimpleScope("AssignAttr.instance_attr1", [])],
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
                                    [SimpleScope("AssignAttr.instance_attr1", [])],
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
                                        SimpleScope("AssignAttr._handler", []),
                                        SimpleScope("AssignAttr._cache", []),
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
    ],
)
def test_get_scope(code: str, expected: list[SimpleScope | SimpleClassScope]) -> None:
    result = _get_scope(code)[0]
    # assert result == expected
    assert_test_get_scope(result, expected)


def assert_test_get_scope(result: list[Scope], expected: list[SimpleScope | SimpleClassScope]) -> None:
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
