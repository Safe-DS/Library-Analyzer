from __future__ import annotations

from dataclasses import dataclass

import astroid
import pytest
from library_analyzer.processing.api import (
    MemberAccess,
    ScopeNode,
    Variables,
    get_scope,
)


@dataclass
class SimpleScope:
    node_name: str | None
    children: list[SimpleScope] | None


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
                        SimpleScope("AssignName.glob", None),
                        SimpleScope(
                            "ClassDef.A",
                            [
                                SimpleScope(
                                    "FunctionDef.__init__",
                                    [
                                        SimpleScope("AssignAttr.value", None),
                                        SimpleScope("AssignAttr.test", None),
                                    ],
                                ),
                                SimpleScope(
                                    "FunctionDef.f",
                                    [SimpleScope("AssignName.var1", None)],
                                ),
                            ],
                        ),
                        SimpleScope("FunctionDef.g", [SimpleScope("AssignName.var2", None)]),
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
                            [SimpleScope("AssignName.res", None)],
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
                        SimpleScope("AssignName.var1", None),
                        SimpleScope(
                            "FunctionDef.function_scope",
                            [SimpleScope("AssignName.res", None)],
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
                        SimpleScope("AssignName.var1", None),
                        SimpleScope(
                            "FunctionDef.function_scope",
                            [SimpleScope("AssignName.res", None)],
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
                                SimpleScope("AssignName.parameter", None),
                                SimpleScope("AssignName.res", None),
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
                        SimpleScope(
                            "ClassDef.A",
                            [
                                SimpleScope("AssignName.class_attr1", None),
                                SimpleScope(
                                    "FunctionDef.local_class_attr",
                                    [SimpleScope("AssignName.var1", None)],
                                ),
                            ],
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
                                    [SimpleScope("AssignAttr.instance_attr1", None)],
                                ),
                                SimpleScope(
                                    "FunctionDef.local_instance_attr",
                                    [SimpleScope("AssignName.var1", None)],
                                ),
                            ],
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
                        SimpleScope(
                            "ClassDef.B",
                            [
                                SimpleScope(
                                    "FunctionDef.__init__",
                                    [SimpleScope("AssignAttr.instance_attr1", None)],
                                ),
                            ],
                        ),
                        SimpleScope(
                            "FunctionDef.local_instance_attr",
                            [SimpleScope("AssignName.var1", None)],
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
                        SimpleScope(
                            "ClassDef.A",
                            [
                                SimpleScope("AssignName.var1", None),
                                SimpleScope(
                                    "ClassDef.B",
                                    [SimpleScope("AssignName.var2", None)],
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
                                SimpleScope("AssignName.var1", None),
                                SimpleScope(
                                    "ClassDef.B",
                                    [SimpleScope("AssignName.var2", None)],
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
                                SimpleScope("AssignName.var1", None),
                                SimpleScope(
                                    "FunctionDef.local_function_scope",
                                    [SimpleScope("AssignName.var2", None)],
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
                        SimpleScope("Import.math", None),
                        SimpleScope("ClassDef.A", [SimpleScope("AssignName.value", None)]),
                    ],
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
                        SimpleScope("ImportFrom.math.pi", None),
                        SimpleScope("ClassDef.B", [SimpleScope("AssignName.value", None)]),
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
                                SimpleScope("AssignName.var1", None),
                                SimpleScope(
                                    "FunctionDef.local_function_scope",
                                    [
                                        SimpleScope("AssignName.var2", None),
                                        SimpleScope(
                                            "ClassDef.local_class_scope",
                                            [
                                                SimpleScope("AssignName.var3", None),
                                                SimpleScope(
                                                    "FunctionDef.local_class_function_scope",
                                                    [
                                                        SimpleScope(
                                                            "AssignName.var4",
                                                            None,
                                                        ),
                                                    ],
                                                ),
                                            ],
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
                        SimpleScope("ImportFrom.collections.abc.Callable", None),
                        SimpleScope("ImportFrom.typing.Any", None),
                        SimpleScope("Import.astroid", None),
                        SimpleScope("AssignName._EnterAndLeaveFunctions", None),
                        SimpleScope(
                            "ClassDef.ASTWalker",
                            [
                                SimpleScope("AssignName.additional_locals", None),
                                SimpleScope(
                                    "FunctionDef.__init__",
                                    [
                                        SimpleScope("AssignName.handler", None),
                                        SimpleScope("AssignAttr._handler", None),
                                        SimpleScope("AssignAttr._cache", None),
                                    ],
                                ),
                                SimpleScope(
                                    "FunctionDef.walk",
                                    [
                                        SimpleScope("AssignName.node", None),
                                    ],
                                ),
                                SimpleScope(
                                    "FunctionDef.__walk",
                                    [
                                        SimpleScope("AssignName.node", None),
                                        SimpleScope("AssignName.visited_nodes", None),
                                    ],
                                ),
                                SimpleScope(
                                    "FunctionDef.__enter",
                                    [
                                        SimpleScope("AssignName.node", None),
                                        SimpleScope("AssignName.method", None),
                                    ],
                                ),
                                SimpleScope(
                                    "FunctionDef.__leave",
                                    [
                                        SimpleScope("AssignName.node", None),
                                        SimpleScope("AssignName.method", None),
                                    ],
                                ),
                                SimpleScope(
                                    "FunctionDef.__get_callbacks",
                                    [
                                        SimpleScope("AssignName.node", None),
                                        SimpleScope("AssignName.klass", None),
                                        SimpleScope("AssignName.methods", None),
                                        SimpleScope("AssignName.handler", None),
                                        SimpleScope("AssignName.class_name", None),
                                        SimpleScope("AssignName.enter_method", None),
                                        SimpleScope("AssignName.leave_method", None),
                                    ],
                                ),
                            ],
                        ),
                    ],
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
        "ASTWalker",
    ],
)
def test_get_scope(code: str, expected: list[SimpleScope]) -> None:
    result = get_scope(code)
    assert_test_get_scope(result[0], expected)


def assert_test_get_scope(result: list[ScopeNode], expected: list[SimpleScope]) -> None:
    transformed_result = [
        transform_result(node) for node in result
    ]  # The result and the expected data is simplified to make the comparison easier
    assert transformed_result == expected


def transform_result(node: ScopeNode) -> SimpleScope:
    if node.children is not None:
        return SimpleScope(to_string(node.node), [transform_result(child) for child in node.children])
    else:
        return SimpleScope(to_string(node.node), None)


def to_string(node: astroid.NodeNG) -> str | None:
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
        return f"{node.__class__.__name__}.{node.names[0][0]}"
    elif isinstance(node, astroid.ImportFrom):
        return f"{node.__class__.__name__}.{node.modname}.{node.names[0][0]}"
    return None


@dataclass
class SimpleVariables:
    """A simplified version of the Variables class."""
    # TODO: class_name: str
    class_variables: list[str]
    instance_variables: list[str]


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (
            """
            class A:
                class_variable = 1
            """,
            [SimpleVariables(["A.class_variable"], [])],
        ),
        (
            """
            class B:
                class_variable1 = 1
                class_variable2 = 2
            """,
            [SimpleVariables(["B.class_variable1", "B.class_variable2"], [])],
        ),
        (
            """
            class C:
                def __init__(self):
                    self.instance_variable = 1
            """,
            [SimpleVariables([], ["self.instance_variable"])],
        ),
        (
            """
            class D:
                def __init__(self):
                    self.instance_variable1 = 1
                    self.instance_variable2 = 2
            """,
            [SimpleVariables([], ["self.instance_variable1", "self.instance_variable2"])],
        ),
        (
            """
            class E:
                class_variable = 1

                def __init__(self):
                    self.instance_variable = 1
            """,
            [SimpleVariables(["E.class_variable"], ["self.instance_variable"])],
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
            [SimpleVariables(["ASTWalker.additional_locals"], ["self._handler", "self._cache"])],
        ),
        (
            """
            class F:
                var = 1

                def __init__(self):
                    self.var = 1
            """,
            [SimpleVariables(["F.var"], ["self.var"])],
        ),
        (
            """
            class G:
                var: int = 1
            """,
            [SimpleVariables(["G.var"], [])],
        ),
        (
            """
            class H:
                var1 = 1
                var2 = 2

            class I:
                test = 1

                def __init__(self):
                    self.var = 1
            """,
            [SimpleVariables(["H.var1", "H.var2"], []), SimpleVariables(["I.test"], ["self.var"])],
        ),
        (
            """
            class J:
                def __init__(self):
                    self.test = 1

                class K:
                    var = 1

                    def __init__(self):
                        self.test = 1
            """,
            [SimpleVariables([], ["self.test"]), SimpleVariables(["K.var"], ["self.test"])],
        ),
        (
            """
            def L():
                class M:
                    var = 1
            """,
            [SimpleVariables(["M.var"], [])],
        ),
        (
            """
                class N:
                    def fun():
                        return 1
            """,
            [SimpleVariables([], [])],
        ),
    ],
    ids=[
        "Class Variable",
        "Multiple Class Variables",
        "Instance Variable",
        "Multiple Instance Variables",
        "Class and Instance Variable",
        "ASTWalker",
        "Class and Instance Variable with same name",
        "Type Annotation",
        "Multiple Classes",
        "Class within Class",
        "Class within Function",
        "Class without variables",
    ],
)
def test_distinguish_class_variables(code: str, expected: list[SimpleVariables]) -> None:
    result = get_scope(code)
    assert result == expected

    transformed_result = transform_variables(result[1])  # The result data is simplified to make the comparison possible
    assert transformed_result == expected


def transform_variables(variables: list[Variables]) -> list[SimpleVariables]:
    result: list[SimpleVariables] = []
    for entry in variables:
        result.append(SimpleVariables([], []))

        class_var = (
            [to_string_var(variable) for variable in entry.class_variables] if entry.class_variables is not None else []
        )
        instance_var = (
            [to_string_var(variable) for variable in entry.instance_variables]
            if entry.instance_variables is not None
            else []
        )

        result[-1].class_variables = class_var
        result[-1].instance_variables = instance_var

    return result


def to_string_var(node: astroid.AssignName | astroid.AssignAttr | astroid.NodeNG) -> str:
    if isinstance(node, astroid.AssignName):
        return f"{node.parent.parent.name}.{node.name}"
    elif isinstance(node, astroid.AssignAttr):
        return f"{node.expr.name}.{node.attrname}"
    elif isinstance(node, astroid.NodeNG):
        pass
    raise AssertionError("Unexpected node type")
