from __future__ import annotations

from dataclasses import dataclass, field

import astroid
import pytest

from library_analyzer.processing.api.model import (
    Scope,
    ClassScope,
    MemberAccess,
    Symbol,
)

from library_analyzer.processing.api import (
    _get_module_data,
    _construct_member_access,
)

from tests.library_analyzer.processing.api import (
    transform_member_access,
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
                        SimpleScope("GlobalVariable.AssignName.glob", []),
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.A",
                            [
                                SimpleScope(
                                    "LocalVariable.FunctionDef.__init__",
                                    [
                                        SimpleScope("InstanceVariable.MemberAccess.self.value", []),
                                        SimpleScope("InstanceVariable.MemberAccess.self.test", []),
                                    ],
                                ),
                                SimpleScope(
                                    "LocalVariable.FunctionDef.f",
                                    [SimpleScope("LocalVariable.AssignName.var1", [])],
                                ),
                            ],
                            [],
                            ["value", "test"],
                        ),
                        SimpleScope("GlobalVariable.FunctionDef.g", [SimpleScope("LocalVariable.AssignName.var2", [])]),
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
                            "GlobalVariable.FunctionDef.function_scope",
                            [SimpleScope("LocalVariable.AssignName.res", [])],
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
                        SimpleScope("GlobalVariable.AssignName.var1", []),
                        SimpleScope(
                            "GlobalVariable.FunctionDef.function_scope",
                            [SimpleScope("LocalVariable.AssignName.res", [])],
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
                        SimpleScope("GlobalVariable.AssignName.var1", []),
                        SimpleScope(
                            "GlobalVariable.FunctionDef.function_scope",
                            [SimpleScope("LocalVariable.AssignName.res", [])],
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
                            "GlobalVariable.FunctionDef.function_scope",
                            [
                                SimpleScope("Parameter.AssignName.parameter", []),
                                SimpleScope("LocalVariable.AssignName.res", []),
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
                            "GlobalVariable.ClassDef.A",
                            [
                                SimpleScope("ClassVariable.AssignName.class_attr1", []),
                                SimpleScope(
                                    "LocalVariable.FunctionDef.local_class_attr",
                                    [SimpleScope("LocalVariable.AssignName.var1", [])],
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
                            "GlobalVariable.ClassDef.B",
                            [
                                SimpleScope("ClassVariable.AssignName.local_class_attr1", []),
                                SimpleScope("ClassVariable.AssignName.local_class_attr2", []),
                                SimpleScope(
                                    "LocalVariable.FunctionDef.__init__",
                                    [SimpleScope("InstanceVariable.MemberAccess.self.instance_attr1", [])],
                                ),
                                SimpleScope(
                                    "LocalVariable.FunctionDef.local_instance_attr",
                                    [SimpleScope("LocalVariable.AssignName.var1", [])],
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
                            "GlobalVariable.ClassDef.B",
                            [
                                SimpleScope(
                                    "LocalVariable.FunctionDef.__init__",
                                    [SimpleScope("InstanceVariable.MemberAccess.self.instance_attr1", [])],
                                ),
                            ],
                            [],
                            ["instance_attr1"],
                        ),
                        SimpleScope(
                            "GlobalVariable.FunctionDef.local_instance_attr",
                            [SimpleScope("LocalVariable.AssignName.var1", [])],
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
                            "GlobalVariable.ClassDef.A",
                            [
                                SimpleScope("ClassVariable.AssignName.var1", []),
                                SimpleClassScope(
                                    "LocalVariable.ClassDef.B",
                                    [SimpleScope("ClassVariable.AssignName.var2", [])],
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
                            "GlobalVariable.ClassDef.A",
                            [SimpleScope("ClassVariable.AssignName.var1", [])],
                            ["var1"],
                            []
                        ),
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.X",
                            [SimpleScope("ClassVariable.AssignName.var3", [])],
                            ["var3"],
                            []
                        ),
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.B",
                            [SimpleScope("ClassVariable.AssignName.var2", [])],
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
                            "GlobalVariable.FunctionDef.function_scope",
                            [
                                SimpleScope("LocalVariable.AssignName.var1", []),
                                SimpleClassScope(
                                    "LocalVariable.ClassDef.B",
                                    [SimpleScope("ClassVariable.AssignName.var2", [])],
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
                            "GlobalVariable.FunctionDef.function_scope",
                            [
                                SimpleScope("LocalVariable.AssignName.var1", []),
                                SimpleScope(
                                    "LocalVariable.FunctionDef.local_function_scope",
                                    [SimpleScope("LocalVariable.AssignName.var2", [])],
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
                        SimpleScope("Import.Import.math", []),
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.A",
                            [SimpleScope("ClassVariable.AssignName.value", [])],
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
                        SimpleScope("Import.ImportFrom.math.pi", []),
                        SimpleClassScope("GlobalVariable.ClassDef.B",
                                         [SimpleScope("ClassVariable.AssignName.value", [])],
                                         ["value"],
                                         []),
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
                            "GlobalVariable.FunctionDef.function_scope",
                            [
                                SimpleScope("LocalVariable.AssignName.var1", []),
                                SimpleScope(
                                    "LocalVariable.FunctionDef.local_function_scope",
                                    [
                                        SimpleScope("LocalVariable.AssignName.var2", []),
                                        SimpleClassScope(
                                            "LocalVariable.ClassDef.local_class_scope",
                                            [
                                                SimpleScope("ClassVariable.AssignName.var3", []),
                                                SimpleScope(
                                                    "LocalVariable.FunctionDef.local_class_function_scope",
                                                    [
                                                        SimpleScope(
                                                            "LocalVariable.AssignName.var4",
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
                        SimpleScope("Import.ImportFrom.collections.abc.Callable", []),
                        SimpleScope("Import.ImportFrom.typing.Any", []),
                        SimpleScope("Import.Import.astroid", []),
                        SimpleScope("GlobalVariable.AssignName._EnterAndLeaveFunctions", []),
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.ASTWalker",
                            [
                                SimpleScope("ClassVariable.AssignName.additional_locals", []),
                                SimpleScope(
                                    "LocalVariable.FunctionDef.__init__",
                                    [
                                        SimpleScope("Parameter.AssignName.handler", []),
                                        SimpleScope("InstanceVariable.MemberAccess.self._handler", []),
                                        SimpleScope("InstanceVariable.MemberAccess.self._cache", []),
                                    ],
                                ),
                                SimpleScope(
                                    "LocalVariable.FunctionDef.walk",
                                    [
                                        SimpleScope("Parameter.AssignName.node", []),
                                    ],
                                ),
                                SimpleScope(
                                    "LocalVariable.FunctionDef.__walk",
                                    [
                                        SimpleScope("Parameter.AssignName.node", []),
                                        SimpleScope("Parameter.AssignName.visited_nodes", []),
                                        SimpleScope("LocalVariable.AssignName.child_node", []),
                                    ],
                                ),
                                SimpleScope(
                                    "LocalVariable.FunctionDef.__enter",
                                    [
                                        SimpleScope("Parameter.AssignName.node", []),
                                        SimpleScope("LocalVariable.AssignName.method", []),
                                    ],
                                ),
                                SimpleScope(
                                    "LocalVariable.FunctionDef.__leave",
                                    [
                                        SimpleScope("Parameter.AssignName.node", []),
                                        SimpleScope("LocalVariable.AssignName.method", []),
                                    ],
                                ),
                                SimpleScope(
                                    "LocalVariable.FunctionDef.__get_callbacks",
                                    [
                                        SimpleScope("Parameter.AssignName.node", []),
                                        SimpleScope("LocalVariable.AssignName.klass", []),
                                        SimpleScope("LocalVariable.AssignName.methods", []),
                                        SimpleScope("LocalVariable.AssignName.handler", []),
                                        SimpleScope("LocalVariable.AssignName.class_name", []),
                                        SimpleScope("LocalVariable.AssignName.enter_method", []),
                                        SimpleScope("LocalVariable.AssignName.leave_method", []),
                                        SimpleScope("LocalVariable.AssignName.enter_method", []),
                                        SimpleScope("LocalVariable.AssignName.leave_method", []),
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
                a = "a"
            """,
            [SimpleScope("Module", [SimpleScope("GlobalVariable.AssignName.a", [])])],
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
                to_string(node.symbol),
                [transform_result(child) for child in node.children],
                [to_string_class(child) for child in node.class_variables],
                [to_string_class(child) for child in node.instance_variables],
                [to_string_class(child) for child in node.super_classes],
            )
        return SimpleScope(to_string(node.symbol), [transform_result(child) for child in node.children])
    else:
        return SimpleScope(to_string(node.symbol), [])


def to_string(symbol: Symbol) -> str:
    if isinstance(symbol.node, astroid.Module):
        return "Module"
    elif isinstance(symbol.node, astroid.ClassDef | astroid.FunctionDef | astroid.AssignName):
        return f"{symbol.__class__.__name__}.{symbol.node.__class__.__name__}.{symbol.node.name}"
    elif isinstance(symbol.node, astroid.AssignAttr):
        return f"{symbol.__class__.__name__}.{symbol.node.__class__.__name__}.{symbol.node.attrname}"
    elif isinstance(symbol.node, MemberAccess):
        result = transform_member_access(symbol.node)
        return f"{symbol.__class__.__name__}.MemberAccess.{result}"
    elif isinstance(symbol.node, astroid.Import):
        return f"{symbol.__class__.__name__}.{symbol.node.__class__.__name__}.{symbol.node.names[0][0]}"  # TODO: handle multiple imports and aliases
    elif isinstance(symbol.node, astroid.ImportFrom):
        return f"{symbol.__class__.__name__}.{symbol.node.__class__.__name__}.{symbol.node.modname}.{symbol.node.names[0][0]}"  # TODO: handle multiple imports and aliases
    elif isinstance(symbol.node, astroid.Name):
        return f"{symbol.__class__.__name__}.{symbol.node.__class__.__name__}.{symbol.node.name}"
    raise NotImplementedError(f"Unknown node type: {symbol.node.__class__.__name__}")


def to_string_class(node: astroid.NodeNG) -> str:
    if isinstance(node, astroid.AssignAttr):
        return f"{node.attrname}"
    elif isinstance(node, astroid.AssignName):
        return f"{node.name}"
    elif isinstance(node, ClassScope):
        return f"{node.symbol.node.__class__.__name__}.{node.symbol.node.name}"
    raise NotImplementedError(f"Unknown node type: {node.__class__.__name__}")
#
#
# @pytest.mark.parametrize(
#     ("node", "expected"),
#     [
#         (
#             astroid.AssignAttr(attrname="member", expr=astroid.Name(name="self")),
#             "self.member"
#         )
#     ]
# )
# def test_construct_member_access(node: astroid.AssignAttr | astroid.Attribute, expected: str) -> None:
#     result = _construct_member_access(node)
#     assert result == expected
