from __future__ import annotations

from dataclasses import dataclass

import astroid
import pytest
from library_analyzer.processing.api import (
    MemberAccess,
    NodeScope,
    get_scope,
)


@dataclass
class SimpleScope:
    node_name: str | None
    children: list[SimpleScope] | None
    parent_scope: str | None


def transform_member_access(member_access: MemberAccess) -> str:
    attribute_names = []

    while isinstance(member_access, MemberAccess):
        attribute_names.append(member_access.value.name)
        member_access = member_access.expression
    if isinstance(member_access, astroid.Name):
        attribute_names.append(member_access.name)

    return ".".join(reversed(attribute_names))


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
                        SimpleScope("AssignName.glob", None, "Module"),
                        SimpleScope(
                            "ClassDef.A",
                            [
                                SimpleScope(
                                    "FunctionDef.__init__",
                                    [
                                        SimpleScope("AssignAttr.value", None, "FunctionDef.__init__"),
                                        SimpleScope("AssignAttr.test", None, "FunctionDef.__init__"),
                                    ],
                                    "ClassDef.A",
                                ),
                                SimpleScope(
                                    "FunctionDef.f",
                                    [SimpleScope("AssignName.var1", None, "FunctionDef.f")],
                                    "ClassDef.A",
                                ),
                            ],
                            "Module",
                        ),
                        SimpleScope("FunctionDef.g", [SimpleScope("AssignName.var2", None, "FunctionDef.g")], "Module"),
                    ],
                    None,
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
                            [SimpleScope("AssignName.res", None, "FunctionDef.function_scope")],
                            "Module",
                        ),
                    ],
                    None,
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
                        SimpleScope("AssignName.var1", None, "Module"),
                        SimpleScope(
                            "FunctionDef.function_scope",
                            [SimpleScope("AssignName.res", None, "FunctionDef.function_scope")],
                            "Module",
                        ),
                    ],
                    None,
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
                        SimpleScope("AssignName.var1", None, "Module"),
                        SimpleScope(
                            "FunctionDef.function_scope",
                            [SimpleScope("AssignName.res", None, "FunctionDef.function_scope")],
                            "Module",
                        ),
                    ],
                    None,
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
                                SimpleScope("AssignName.parameter", None, "FunctionDef.function_scope"),
                                SimpleScope("AssignName.res", None, "FunctionDef.function_scope"),
                            ],
                            "Module",
                        ),
                    ],
                    None,
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
                        SimpleScope(
                            "ClassDef.A",
                            [
                                SimpleScope("AssignName.class_attr1", None, "ClassDef.A"),
                                SimpleScope(
                                    "FunctionDef.local_class_attr",
                                    [SimpleScope("AssignName.var1", None, "FunctionDef.local_class_attr")],
                                    "ClassDef.A",
                                ),
                            ],
                            "Module",
                        ),
                    ],
                    None,
                ),
            ],
        ),
        (
            """
                class B:
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
                        SimpleScope(
                            "ClassDef.B",
                            [
                                SimpleScope(
                                    "FunctionDef.__init__",
                                    [SimpleScope("AssignAttr.instance_attr1", None, "FunctionDef.__init__")],
                                    "ClassDef.B",
                                ),
                                SimpleScope(
                                    "FunctionDef.local_instance_attr",
                                    [SimpleScope("AssignName.var1", None, "FunctionDef.local_instance_attr")],
                                    "ClassDef.B",
                                ),
                            ],
                            "Module",
                        ),
                    ],
                    None,
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
                        SimpleScope(
                            "ClassDef.B",
                            [
                                SimpleScope(
                                    "FunctionDef.__init__",
                                    [SimpleScope("AssignAttr.instance_attr1", None, "FunctionDef.__init__")],
                                    "ClassDef.B",
                                ),
                            ],
                            "Module",
                        ),
                        SimpleScope(
                            "FunctionDef.local_instance_attr",
                            [SimpleScope("AssignName.var1", None, "FunctionDef.local_instance_attr")],
                            "Module",
                        ),
                    ],
                    None,
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
                        SimpleScope(
                            "ClassDef.A",
                            [
                                SimpleScope("AssignName.var1", None, "ClassDef.A"),
                                SimpleScope(
                                    "ClassDef.B",
                                    [SimpleScope("AssignName.var2", None, "ClassDef.B")],
                                    "ClassDef.A",
                                ),
                            ],
                            "Module",
                        ),
                    ],
                    None,
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
                                SimpleScope("AssignName.var1", None, "FunctionDef.function_scope"),
                                SimpleScope(
                                    "ClassDef.B",
                                    [SimpleScope("AssignName.var2", None, "ClassDef.B")],
                                    "FunctionDef.function_scope",
                                ),
                            ],
                            "Module",
                        ),
                    ],
                    None,
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
                                SimpleScope("AssignName.var1", None, "FunctionDef.function_scope"),
                                SimpleScope(
                                    "FunctionDef.local_function_scope",
                                    [SimpleScope("AssignName.var2", None, "FunctionDef.local_function_scope")],
                                    "FunctionDef.function_scope",
                                ),
                            ],
                            "Module",
                        ),
                    ],
                    None,
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
                        SimpleScope("Import.math", None, "Module"),
                        SimpleScope("ClassDef.A", [SimpleScope("AssignName.value", None, "ClassDef.A")], "Module"),
                    ],
                    None,
                ),
            ],
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
                        SimpleScope("ImportFrom.math.pi", None, "Module"),
                        SimpleScope("ClassDef.B", [SimpleScope("AssignName.value", None, "ClassDef.B")], "Module"),
                    ],
                    None,
                ),
            ],
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
                                SimpleScope("AssignName.var1", None, "FunctionDef.function_scope"),
                                SimpleScope(
                                    "FunctionDef.local_function_scope",
                                    [
                                        SimpleScope("AssignName.var2", None, "FunctionDef.local_function_scope"),
                                        SimpleScope(
                                            "ClassDef.local_class_scope",
                                            [
                                                SimpleScope("AssignName.var3", None, "ClassDef.local_class_scope"),
                                                SimpleScope(
                                                    "FunctionDef.local_class_function_scope",
                                                    [
                                                        SimpleScope(
                                                            "AssignName.var4",
                                                            None,
                                                            "FunctionDef.local_class_function_scope",
                                                        ),
                                                    ],
                                                    "ClassDef.local_class_scope",
                                                ),
                                            ],
                                            "FunctionDef.local_function_scope",
                                        ),
                                    ],
                                    "FunctionDef.function_scope",
                                ),
                            ],
                            "Module",
                        ),
                    ],
                    None,
                ),
            ],
        ),
        (
            """
                def function_scope():
                    var1 = 10

                function_scope()
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope(
                            "FunctionDef.function_scope",
                            [SimpleScope("AssignName.var1", None, "FunctionDef.function_scope")],
                            "Module",
                        ),
                        SimpleScope("Call.function_scope", None, "Module"),
                    ],
                    None,
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
                        SimpleScope("ImportFrom.collections.abc.Callable", None, "Module"),
                        SimpleScope("ImportFrom.typing.Any", None, "Module"),
                        SimpleScope("Import.astroid", None, "Module"),
                        SimpleScope("AssignName._EnterAndLeaveFunctions", None, "Module"),
                        SimpleScope(
                            "ClassDef.ASTWalker",
                            [
                                SimpleScope("AssignName.additional_locals", None, "ClassDef.ASTWalker"),
                                SimpleScope(
                                    "FunctionDef.__init__",
                                    [
                                        SimpleScope("AssignName.handler", None, "FunctionDef.__init__"),
                                        SimpleScope("AssignAttr._handler", None, "FunctionDef.__init__"),
                                        SimpleScope("AssignAttr._cache", None, "FunctionDef.__init__"),
                                    ],
                                    "ClassDef.ASTWalker",
                                ),
                                SimpleScope(
                                    "FunctionDef.walk",
                                    [
                                        SimpleScope("AssignName.node", None, "FunctionDef.walk"),
                                        SimpleScope("Call.self.__walk", None, "FunctionDef.walk"),
                                    ],
                                    "ClassDef.ASTWalker",
                                ),
                                SimpleScope(
                                    "FunctionDef.__walk",
                                    [
                                        SimpleScope("AssignName.node", None, "FunctionDef.__walk"),
                                        SimpleScope("AssignName.visited_nodes", None, "FunctionDef.__walk"),
                                        SimpleScope("Call.visited_nodes.add", None, "FunctionDef.__walk"),
                                        SimpleScope("Call.self.__enter", None, "FunctionDef.__walk"),
                                        SimpleScope("Call.self.__walk", None, "FunctionDef.__walk"),
                                        SimpleScope("Call.self.__leave", None, "FunctionDef.__walk"),
                                    ],
                                    "ClassDef.ASTWalker",
                                ),
                                SimpleScope(
                                    "FunctionDef.__enter",
                                    [
                                        SimpleScope("AssignName.node", None, "FunctionDef.__enter"),
                                        SimpleScope("AssignName.method", None, "FunctionDef.__enter"),
                                        SimpleScope("Call.method", None, "FunctionDef.__enter"),
                                    ],
                                    "ClassDef.ASTWalker",
                                ),
                                SimpleScope(
                                    "FunctionDef.__leave",
                                    [
                                        SimpleScope("AssignName.node", None, "FunctionDef.__leave"),
                                        SimpleScope("AssignName.method", None, "FunctionDef.__leave"),
                                        SimpleScope("Call.method", None, "FunctionDef.__leave"),
                                    ],
                                    "ClassDef.ASTWalker",
                                ),
                                SimpleScope(
                                    "FunctionDef.__get_callbacks",
                                    [
                                        SimpleScope("AssignName.node", None, "FunctionDef.__get_callbacks"),
                                        SimpleScope("AssignName.klass", None, "FunctionDef.__get_callbacks"),
                                        SimpleScope("AssignName.methods", None, "FunctionDef.__get_callbacks"),
                                        SimpleScope("AssignName.handler", None, "FunctionDef.__get_callbacks"),
                                        SimpleScope("AssignName.class_name", None, "FunctionDef.__get_callbacks"),
                                        SimpleScope("AssignName.enter_method", None, "FunctionDef.__get_callbacks"),
                                        SimpleScope("AssignName.leave_method", None, "FunctionDef.__get_callbacks"),
                                    ],
                                    "ClassDef.ASTWalker",
                                ),
                            ],
                            "Module",
                        ),
                    ],
                    None,
                ),
            ],
        ),
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
        "Import From Scope",
        "Complex Scope",
        "Call",
        "ASTWalker",
    ],
)
def test_get_scope(code: str, expected: list[SimpleScope]) -> None:
    result = get_scope(code)
    assert_test_get_scope(result, expected)


def assert_test_get_scope(result: list[NodeScope], expected: list[SimpleScope]) -> None:
    transformed_result = [
        transform_result(node) for node in result
    ]  # The result and the expected data is simplified to make the comparison easier
    assert transformed_result == expected


def transform_result(node: NodeScope) -> SimpleScope:
    if node.children is not None:
        return SimpleScope(
            to_string(node.node),
            [transform_result(child) for child in node.children],
            to_string(node.parent_scope),
        )
    else:
        return SimpleScope(to_string(node.node), None, to_string(node.parent_scope))


def to_string(node: astroid.NodeNG) -> str | None:
    if isinstance(node, astroid.Module):
        return "Module"
    elif isinstance(node, astroid.ClassDef | astroid.FunctionDef | astroid.AssignName):
        return f"{node.__class__.__name__}.{node.name}"
    elif isinstance(node, astroid.AssignAttr):
        return f"{node.__class__.__name__}.{node.attrname}"
    elif isinstance(node, astroid.Call):
        if isinstance(node.func, astroid.Attribute) and isinstance(node.func.expr, astroid.Name):
            return f"{node.__class__.__name__}.{node.func.expr.name}.{node.func.attrname}"
        elif isinstance(node.func, astroid.Name):
            return f"{node.__class__.__name__}.{node.func.name}"
    elif isinstance(node, MemberAccess):
        result = transform_member_access(node)
        return f"MemberAccess.{result}"
    elif isinstance(node, astroid.Import):
        return f"{node.__class__.__name__}.{node.names[0][0]}"
    elif isinstance(node, astroid.ImportFrom):
        return f"{node.__class__.__name__}.{node.modname}.{node.names[0][0]}"
    return None
