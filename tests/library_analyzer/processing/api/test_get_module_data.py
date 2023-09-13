from __future__ import annotations

from dataclasses import dataclass, field

import astroid
import pytest

from library_analyzer.processing.api.purity_analysis.model import (
    Scope,
    ClassScope,
    MemberAccess,
    Symbol,
    MemberAccessValue,
    MemberAccessTarget,
)

from library_analyzer.processing.api.purity_analysis import (
    get_module_data,
    calc_node_id,
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
            astroid.ImportFrom(fromname="math", names=[("sqrt", None)], level=0, lineno=1, col_offset=0,
                               parent=astroid.Module("my_module")),
            "my_module.sqrt.1.0",
        ),
        (
            astroid.ImportFrom(fromname="math", names=[("sqrt", "s")], level=0, lineno=1, col_offset=0,
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
    result = calc_node_id(node)
    assert result.__str__() == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # Seminar Example
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
                                    "ClassVariable.FunctionDef.__init__",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("InstanceVariable.MemberAccess.self.value", []),
                                        SimpleScope("InstanceVariable.MemberAccess.self.test", []),
                                    ],
                                ),
                                SimpleScope(
                                    "ClassVariable.FunctionDef.f",
                                    [SimpleScope("LocalVariable.AssignName.var1", [])],
                                ),
                            ],
                            ["FunctionDef.__init__", "FunctionDef.f"],
                            ["AssignAttr.value", "AssignAttr.test"],
                        ),
                        SimpleScope("GlobalVariable.FunctionDef.g", [SimpleScope("LocalVariable.AssignName.var2", [])]),
                    ],
                ),
            ],
        ),
        (  # Function Scope
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
        (  # Function Scope with variable
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
        (  # Function Scope with global variable
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
        (  # Function Scope with Parameter
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
        (  # Class Scope with class attribute and class function
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
                                    "ClassVariable.FunctionDef.local_class_attr",
                                    [SimpleScope("LocalVariable.AssignName.var1", [])],
                                ),
                            ],
                            ["AssignName.class_attr1", "FunctionDef.local_class_attr"],
                            [],
                        ),
                    ],
                ),
            ],
        ),
        (  # Class Scope with instance attribute and class function
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
                                    "ClassVariable.FunctionDef.__init__",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("InstanceVariable.MemberAccess.self.instance_attr1", [])
                                    ],
                                ),
                                SimpleScope(
                                    "ClassVariable.FunctionDef.local_instance_attr",
                                    [SimpleScope("LocalVariable.AssignName.var1", [])],
                                ),
                            ],
                            ["AssignName.local_class_attr1", "AssignName.local_class_attr2", "FunctionDef.__init__",
                             "FunctionDef.local_instance_attr"],
                            ["AssignAttr.instance_attr1"],
                        ),
                    ],
                ),
            ],
        ),
        (  # Class Scope with instance attribute and module function
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
                                    "ClassVariable.FunctionDef.__init__",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("InstanceVariable.MemberAccess.self.instance_attr1", [])
                                    ],
                                ),
                            ],
                            ["FunctionDef.__init__"],
                            ["AssignAttr.instance_attr1"],
                        ),
                        SimpleScope(
                            "GlobalVariable.FunctionDef.local_instance_attr",
                            [SimpleScope("LocalVariable.AssignName.var1", [])],
                        ),
                    ],
                ),
            ],
        ),
        (  # Class Scope within Class Scope
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
                                    "ClassVariable.ClassDef.B",
                                    [SimpleScope("ClassVariable.AssignName.var2", [])],
                                    ["AssignName.var2"],
                                    [],
                                ),
                            ],
                            ["AssignName.var1", "ClassDef.B"],
                            [],
                        ),
                    ],
                ),
            ],
        ),
        (  # Class Scope with subclass
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
                            ["AssignName.var1"],
                            []
                        ),
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.X",
                            [SimpleScope("ClassVariable.AssignName.var3", [])],
                            ["AssignName.var3"],
                            []
                        ),
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.B",
                            [SimpleScope("ClassVariable.AssignName.var2", [])],
                            ["AssignName.var2"],
                            [],
                            ["ClassDef.A", "ClassDef.X"]
                        ),
                    ],
                ),
            ],
        ),
        (  # Class Scope within Function Scope
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
                                    ["AssignName.var2"],
                                    [],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        (  # Function Scope within Function Scope
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
                        SimpleScope("GlobalVariable.Import.math", []),
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.A",
                            [SimpleScope("ClassVariable.AssignName.value", [])],
                            ["AssignName.value"],
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
            [SimpleScope("Module",
                         [SimpleScope("GlobalVariable.Import.math", []),
                          SimpleScope("GlobalVariable.Import.datetime", []),
                          SimpleScope("GlobalVariable.AssignName.a", [])])],
        ),
        (
            """
                import math as m

                a = m.pi
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope("GlobalVariable.Import.m", []),
                        SimpleScope("GlobalVariable.AssignName.a", []),
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
                        SimpleScope("GlobalVariable.ImportFrom.math.pi", []),
                        SimpleClassScope("GlobalVariable.ClassDef.B",
                                         [SimpleScope("ClassVariable.AssignName.value", [])],
                                         ["AssignName.value"],
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
            [
                SimpleScope("Module",
                            [SimpleScope("GlobalVariable.ImportFrom.math.pi", []),
                             SimpleScope("GlobalVariable.ImportFrom.math.e", []),
                             SimpleScope("GlobalVariable.AssignName.a", [])])
            ]
        ),
        (
            """
                from math import pi as pi_value

                a = pi_value
            """,
            [
                SimpleScope(
                    "Module",
                    [SimpleScope("GlobalVariable.ImportFrom.math.pi_value", []),
                     SimpleScope("GlobalVariable.AssignName.a", [])]
                )
            ]
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
                                                    "ClassVariable.FunctionDef.local_class_function_scope",
                                                    [
                                                        SimpleScope(
                                                            "LocalVariable.AssignName.var4",
                                                            [],
                                                        ),
                                                    ],
                                                ),
                                            ],
                                            ["AssignName.var3", "FunctionDef.local_class_function_scope"],
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
        (  # ASTWalker
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
                                    "ClassVariable.FunctionDef.__init__",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("Parameter.AssignName.handler", []),
                                        SimpleScope("InstanceVariable.MemberAccess.self._handler", []),
                                        SimpleScope("InstanceVariable.MemberAccess.self._cache", []),
                                    ],
                                ),
                                SimpleScope(
                                    "ClassVariable.FunctionDef.walk",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("Parameter.AssignName.node", []),
                                    ],
                                ),
                                SimpleScope(
                                    "ClassVariable.FunctionDef.__walk",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("Parameter.AssignName.node", []),
                                        SimpleScope("Parameter.AssignName.visited_nodes", []),
                                        SimpleScope("LocalVariable.AssignName.child_node", []),
                                    ],
                                ),
                                SimpleScope(
                                    "ClassVariable.FunctionDef.__enter",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("Parameter.AssignName.node", []),
                                        SimpleScope("LocalVariable.AssignName.method", []),
                                    ],
                                ),
                                SimpleScope(
                                    "ClassVariable.FunctionDef.__leave",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("Parameter.AssignName.node", []),
                                        SimpleScope("LocalVariable.AssignName.method", []),
                                    ],
                                ),
                                SimpleScope(
                                    "ClassVariable.FunctionDef.__get_callbacks",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
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
                            ["AssignName.additional_locals", "FunctionDef.__init__", "FunctionDef.walk",
                             "FunctionDef.__walk", "FunctionDef.__enter", "FunctionDef.__leave",
                             "FunctionDef.__get_callbacks"],
                            ["AssignAttr._handler", "AssignAttr._cache"],
                        ),
                    ],
                ),
            ],
        ),
        (  # AssignName
            """
                a = "a"
            """,
            [SimpleScope("Module", [SimpleScope("GlobalVariable.AssignName.a", [])])],
        ),
        (  # List Comprehension in Module
            """
                [len(num) for num in nums]
            """,
            [SimpleScope("Module", [SimpleScope("ListComp", [SimpleScope("LocalVariable.AssignName.num", [])])])],
        ),
        (  # List Comprehension in Class
            """
                class A:
                    x = [len(num) for num in nums]
            """,
            [SimpleScope("Module",
                         [SimpleClassScope("GlobalVariable.ClassDef.A", [SimpleScope("ClassVariable.AssignName.x", []),
                                                                         SimpleScope("ListComp", [
                                                                             SimpleScope("LocalVariable.AssignName.num",
                                                                                         [])])], ["AssignName.x"], [],
                                           [])])],
        ),
        (  # List Comprehension in Function
            """
                def fun():
                    x = [len(num) for num in nums]
            """,
            [SimpleScope("Module",
                         [SimpleScope("GlobalVariable.FunctionDef.fun", [SimpleScope("LocalVariable.AssignName.x", []),
                                                                         SimpleScope("ListComp", [
                                                                             SimpleScope("LocalVariable.AssignName.num",
                                                                                         [])])])])],
        ),
        (  # Try Except in Module
            """
                try:
                    result = num1 / num2
                except ZeroDivisionError as zde:
                    zde
            """,
            [SimpleScope("Module", [SimpleScope("TryExcept", [SimpleScope("GlobalVariable.AssignName.result", []),
                                                              SimpleScope("LocalVariable.AssignName.zde", [])])])],
            # TODO: do we want zde to be Global? -> no it should be local to the except block
        ),
        (  # Try Except Finally in Module
            """
                try:
                    result = num1 / num2
                except ZeroDivisionError as zde:
                    error = 1
                finally:
                    final = 1
            """,
            [SimpleScope("Module", [SimpleScope("TryExcept", [SimpleScope("GlobalVariable.AssignName.result", []),
                                                              SimpleScope("GlobalVariable.AssignName.error", []),
                                                              SimpleScope("GlobalVariable.AssignName.final", [])])])],
            # TODO: do we want finally to be its own scope? -> No. we want its content to be part of the parent scope
            #  just zde is local to the except block which should get its own scope
        ),
        (  # Try Except in Class
            """
                class A:
                    try:
                        result = num1 / num2
                    except ZeroDivisionError as zde:
                        error = 1
            """,
            [SimpleScope("Module", [SimpleClassScope("GlobalVariable.ClassDef.A", [
                SimpleScope("TryExcept", [SimpleScope("ClassVariable.AssignName.result", []),
                                          SimpleScope("GlobalVariable.AssignName.error", [])])],
                                                     [], [], [])])],
            # TODO: do we want any of these to be class variables? -> Yes all of them, just zde is local
        ),
        (  # Try Except in Function
            """
                def fun():
                    try:
                        result = num1 / num2
                    except ZeroDivisionError as zde:
                        error = 1
            """,
            [SimpleScope("Module", [SimpleScope("GlobalVariable.FunctionDef.fun", [
                SimpleScope("TryExcept", [SimpleScope("LocalVariable.AssignName.result", []),
                                          SimpleScope("LocalVariable.AssignName.zde", [])])])])],
            # TODO: what about this case? -> see above: zde should be local the rest is in parent scope
        ),
        (  # With Statement
            """
                with file:
                    a = 1
            """,
            [SimpleScope("Module", [SimpleScope("GlobalVariable.AssignName.a", []),
                                    SimpleScope("With", [])])]
        ),
        (  # With Statement File
            """
                file = "file.txt"
                with open(file, "r") as f:
                    a = 1
                    f.read()
            """,
            [SimpleScope("Module", [SimpleScope("GlobalVariable.AssignName.file", []),
                                    SimpleScope("GlobalVariable.AssignName.a", []),
                                    SimpleScope("With", [SimpleScope("LocalVariable.AssignName.f", [])])])]
        ),
        (  # With Statement Class
            """
                class MyContext:
                    def __enter__(self):
                        print("Entering the context")
                        return self

                    def __exit__(self):
                        print("Exiting the context")

                with MyContext() as context:
                    print("Inside the context")
            """,
            [SimpleScope("Module", [SimpleClassScope("GlobalVariable.ClassDef.MyContext", [
                SimpleScope("ClassVariable.FunctionDef.__enter__", [SimpleScope("Parameter.AssignName.self", [])]),
                SimpleScope("ClassVariable.FunctionDef.__exit__", [SimpleScope("Parameter.AssignName.self", [])])],
                                                     ["FunctionDef.__enter__", "FunctionDef.__exit__"], [], []),
                                    SimpleScope("With", [SimpleScope("LocalVariable.AssignName.context", [])])])]
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
        "List Comprehension in Module",
        "List Comprehension in Class",
        "List Comprehension in Function",
        "Try Except in Module",
        "Try Except Finally in Module",
        "Try Except in Class",
        "Try Except in Function",
        "With Statement",
        "With Statement File",
        "With Statement Class",
    ],  # TODO: add tests for lambda and generator expressions
)
def test_get_module_data_scope(code: str, expected: list[SimpleScope | SimpleClassScope]) -> None:
    scope = get_module_data(code).scope
    # assert result == expected
    assert_test_get_scope(scope, expected)


def assert_test_get_scope(result: Scope, expected: list[SimpleScope | SimpleClassScope]) -> None:
    transformed_result = [
        transform_result(node) for node in result
    ]  # The result and the expected data is simplified to make the comparison easier
    assert transformed_result == expected


def transform_result(node: Scope | ClassScope) -> SimpleScope | SimpleClassScope:
    if node.children is not None:
        if isinstance(node, ClassScope):
            instance_vars_transformed = []
            class_vars_transformed = []
            for child in node.instance_variables.values():
                for c in child:
                    instance_vars_transformed.append(to_string_class(c.node.member))
            for child in node.class_variables.values():
                for c in child:
                    c_str = to_string_class(c.node)
                    if c_str is not None:
                        class_vars_transformed.append(c_str)

            return SimpleClassScope(
                to_string(node.symbol),
                [transform_result(child) for child in node.children],
                class_vars_transformed,
                instance_vars_transformed,
                [to_string_class(child) for child in node.super_classes],
            )
        return SimpleScope(to_string(node.symbol), [transform_result(child) for child in node.children])
    else:
        return SimpleScope(to_string(node.symbol), [])


def to_string(symbol: Symbol) -> str:
    if isinstance(symbol.node, astroid.Module):
        return f"{symbol.node.__class__.__name__}"
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
    elif isinstance(symbol.node, astroid.ListComp | astroid.TryExcept | astroid.TryFinally | astroid.With):
        return f"{symbol.node.__class__.__name__}"
    raise NotImplementedError(f"Unknown node type: {symbol.node.__class__.__name__}")


def to_string_class(node: astroid.NodeNG | ClassScope) -> str | None:
    if isinstance(node, astroid.AssignAttr):
        return f"{node.__class__.__name__}.{node.attrname}"
    elif isinstance(node, astroid.AssignName | astroid.FunctionDef | astroid.ClassDef):
        return f"{node.__class__.__name__}.{node.name}"
    elif isinstance(node, astroid.Lambda | astroid.TryExcept | astroid.TryFinally | astroid.ListComp):
        return None
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


@pytest.mark.parametrize(
    ("code", "expected"),
    # expected is a tuple of (ClassDefName, set of class variables, set of instance variables, list of super classes)
    [
        (  # ClassDef
            """
                class A:
                    pass
            """,
            {"A": SimpleClassScope("GlobalVariable.ClassDef.A", [], [], [], [])},
        ),
        (  # ClassDef with class attribute
            """
                class A:
                    var1 = 1
            """,
            {"A": SimpleClassScope("GlobalVariable.ClassDef.A", [SimpleScope("ClassVariable.AssignName.var1", [])],
                                   ["AssignName.var1"], [], [])},
        ),
        (  # ClassDef with multiple class attribute
            """
                class A:
                    var1 = 1
                    var2 = 2
            """,
            {"A": SimpleClassScope("GlobalVariable.ClassDef.A", [SimpleScope("ClassVariable.AssignName.var1", []),
                                                                 SimpleScope("ClassVariable.AssignName.var2", [])],
                                   ["AssignName.var1", "AssignName.var2"], [], [])},
        ),
        (  # ClassDef with multiple class attribute (same name)
            """
                class A:
                    if True:
                        var1 = 1
                    else:
                        var1 = 2
            """,
            {"A": SimpleClassScope("GlobalVariable.ClassDef.A", [SimpleScope("ClassVariable.AssignName.var1", []),
                                                                 SimpleScope("ClassVariable.AssignName.var1", [])],
                                   ["AssignName.var1", "AssignName.var1"], [], [])},
        ),
        (  # ClassDef with instance attribute
            """
                class A:
                    def __init__(self):
                        self.var1 = 1
            """,
            {"A": SimpleClassScope("GlobalVariable.ClassDef.A", [SimpleScope("ClassVariable.FunctionDef.__init__", [
                SimpleScope("Parameter.AssignName.self", []),
                SimpleScope("InstanceVariable.MemberAccess.self.var1", [])])],
                                   ["FunctionDef.__init__"], ["AssignAttr.var1"], [])},
        ),
        (  # ClassDef with multiple instance attributes (and type annotations)
            """
                class A:
                    def __init__(self):
                        self.var1: int = 1
                        self.name: str = "name"
                        self.state: bool = True
            """,
            {"A": SimpleClassScope("GlobalVariable.ClassDef.A", [
                SimpleScope("ClassVariable.FunctionDef.__init__", [SimpleScope("Parameter.AssignName.self", []),
                                                                   SimpleScope(
                                                                       "InstanceVariable.MemberAccess.self.var1", []),
                                                                   SimpleScope(
                                                                       "InstanceVariable.MemberAccess.self.name", []),
                                                                   SimpleScope(
                                                                       "InstanceVariable.MemberAccess.self.state",
                                                                       [])])],
                                   ["FunctionDef.__init__"], ["AssignAttr.var1", "AssignAttr.name", "AssignAttr.state"],
                                   [])},
        ),
        (  # ClassDef with conditional instance attributes (instance attributes with same name)
            """
                class A:
                    def __init__(self):
                        if True:
                            self.var1 = 1
                        else:
                            self.var1 = 0
            """,
            {"A": SimpleClassScope("GlobalVariable.ClassDef.A", [SimpleScope("ClassVariable.FunctionDef.__init__", [
                SimpleScope("Parameter.AssignName.self", []),
                SimpleScope("InstanceVariable.MemberAccess.self.var1", []),
                SimpleScope("InstanceVariable.MemberAccess.self.var1", [])])],
                                   ["FunctionDef.__init__"], ["AssignAttr.var1", "AssignAttr.var1"],
                                   [])},
        ),
        (  # ClassDef with class and instance attribute
            """
                class A:
                    var1 = 1

                    def __init__(self):
                        self.var1 = 1
            """,
            {"A": SimpleClassScope("GlobalVariable.ClassDef.A", [SimpleScope("ClassVariable.AssignName.var1", []),
                                                                 SimpleScope("ClassVariable.FunctionDef.__init__", [
                                                                     SimpleScope("Parameter.AssignName.self", []),
                                                                     SimpleScope(
                                                                         "InstanceVariable.MemberAccess.self.var1",
                                                                         [])])],
                                   ["AssignName.var1", "FunctionDef.__init__"], ["AssignAttr.var1"], [])},
        ),
        (  # ClassDef with nested class
            """
                class A:
                    class B:
                        pass
            """,
            {"A": SimpleClassScope("GlobalVariable.ClassDef.A", [SimpleClassScope("ClassVariable.ClassDef.B",
                                                                                  [], [], [], [])],
                                   ["ClassDef.B"], [], []),
             "B": SimpleClassScope("ClassVariable.ClassDef.B", [], [], [], [])},
        ),
        (  # Multiple ClassDef
            """
                class A:
                    pass

                class B:
                    pass
            """,
            {"A": SimpleClassScope("GlobalVariable.ClassDef.A", [], [], [], []),
             "B": SimpleClassScope("GlobalVariable.ClassDef.B", [], [], [], [])},
        ),
        (  # ClassDef with super class
            """
                class A:
                    pass

                class B(A):
                    pass
            """,
            {"A": SimpleClassScope("GlobalVariable.ClassDef.A", [], [], [], []),
             "B": SimpleClassScope("GlobalVariable.ClassDef.B", [], [], [], ["ClassDef.A"])},
        ),
    ],
    ids=[
        "ClassDef",
        "ClassDef with class attribute",
        "ClassDef with multiple class attribute",
        "ClassDef with conditional class attribute (same name)",
        "ClassDef with instance attribute",
        "ClassDef with multiple instance attributes",
        "ClassDef with conditional instance attributes (instance attributes with same name)",
        "ClassDef with class and instance attribute",
        "ClassDef with nested class",
        "Multiple ClassDef",
        "ClassDef with super class",
    ]
)
def test_get_module_data_classes(code: str, expected: dict[str, SimpleClassScope]) -> None:
    classes = get_module_data(code).classes

    assert_get_module_data_classes(classes, expected)


def assert_get_module_data_classes(classes: dict[str, ClassScope],
                                   expected: dict[str, SimpleClassScope]) -> None:
    transformed_classes = {
        klassname: transform_result(klass) for klassname, klass in classes.items()
    }  # The result and the expected data is simplified to make the comparison easier
    assert transformed_classes == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    []
)
def test_get_module_data_functions(code: str, expected: str) -> None:
    functions = get_module_data(code).classes
    raise NotImplementedError("TODO: implement test")
    assert functions == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    []
)
def test_get_module_data_globals(code: str, expected: str) -> None:
    globs = get_module_data(code).classes
    raise NotImplementedError("TODO: implement test")
    assert globs == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
    ]
)
def test_get_module_data_parameters(code: str, expected: str) -> None:
    parameters = get_module_data(code).classes
    raise NotImplementedError("TODO: implement test")
    assert parameters == expected


@pytest.mark.parametrize(
    ("code", "expected"),  # expected is a tuple of (value_nodes, target_nodes)
    [
        (  # Assign
            """
                def variable():
                    var1 = 20
            """,
            ({},
             {"var1": "AssignName.var1"}),
        ),
        (  # Assign Parameter
            """
                def parameter(a):
                    var1 = a
            """,
            ({"a": "Name.a"},
             {"var1": "AssignName.var1",
              "a": "AssignName.a"}),
        ),
        (  # Global unused
            """
                def glob():
                    global glob1
            """,
            ({}, {}),
        ),
        (  # Global and Assign
            """
                def glob():
                    global glob1
                    var1 = glob1
            """,
            ({"glob1": "Name.glob1"},
             {"var1": "AssignName.var1"}),
        ),
        (  # Assign Class Attribute
            """
                def class_attr():
                    var1 = A.class_attr
            """,
            ({"A": "Name.A",
              "A.class_attr": "MemberAccessValue.A.class_attr"},
             {"var1": "AssignName.var1"}),
        ),
        (  # Assign Instance Attribute
            """
                def instance_attr():
                    b = B()
                    var1 = b.instance_attr
            """,
            ({"b": "Name.b",
              "b.instance_attr": "MemberAccessValue.b.instance_attr"},
             {"b": "AssignName.b",
              "var1": "AssignName.var1"}),
        ),
        (  # Assign MemberAccessValue
            """
                def chain():
                    var1 = test.instance_attr.field.next_field
            """,
            ({"test": "Name.test",
              "test.instance_attr": "MemberAccessValue.test.instance_attr",
              "test.instance_attr.field": "MemberAccessValue.test.instance_attr.field",
              "test.instance_attr.field.next_field": "MemberAccessValue.test.instance_attr.field.next_field"},
             {"var1": "AssignName.var1"}),
        ),
        (  # Assign MemberAccessTarget
            """
                def chain_reversed():
                    test.instance_attr.field.next_field = var1
            """,
            ({"var1": "Name.var1"},
             {"test": "Name.test",
              "test.instance_attr": "MemberAccessTarget.test.instance_attr",
              "test.instance_attr.field": "MemberAccessTarget.test.instance_attr.field",
              "test.instance_attr.field.next_field": "MemberAccessTarget.test.instance_attr.field.next_field"})
        ),
        (  # AssignAttr
            """
                def assign_attr():
                    a.res = 1
            """,
            ({},
             {"a": "Name.a",
              "a.res": "MemberAccessTarget.a.res"}),
        ),
        (  # AugAssign
            """
                def aug_assign():
                    var1 += 1
            """,
            ({},
             {"var1": "AssignName.var1"}),
        ),
        (  # Return
            """
                def assign_return():
                    return var1
            """,
            ({"var1": "Name.var1"},
             {})
        ),
        (  # While
            """
                def while_loop():
                    while var1 > 0:
                        do_something()
            """,
            ({"var1": "Name.var1"},
             {})
        ),
        (  # For
            """
                def for_loop():
                    for var1 in range(10):
                        do_something()
            """,
            ({},
             {"var1": "AssignName.var1"})
        ),
        (  # If
            """
                def if_state():
                    if var1 > 0:
                        do_something()
            """,
            ({"var1": "Name.var1"},
             {})
        ),
        (  # If Else
            """
                def if_else_state():
                    if var1 > 0:
                        do_something()
                    else:
                        do_something_else()
            """,
            ({"var1": "Name.var1"},
             {})
        ),
        (  # If Elif
            """
                def if_elif_state():
                    if var1 & True:
                        do_something()
                    elif var1 | var2:
                        do_something_else()
            """,
            ({"var1": "Name.var1",
              "var1": "Name.var1",
              "var2": "Name.var2"},
             {})
        ),
        (  # Try Except Finally
            """
                try:
                    result = num1 / num2
                except ZeroDivisionError as error:
                    error
                finally:
                    final = num3
            """,
            ({"error": "Name.error",
              "num1": "Name.num1",
              "num2": "Name.num2",
              "num3": "Name.num3"},
             {"error": "AssignName.error",
              "final": "AssignName.final",
              "result": "AssignName.result"})
        ),
        (  # AnnAssign
            """
                def ann_assign():
                    var1: int = 10
            """,
            ({},
             {"var1": "AssignName.var1"})
        ),
        (  # FuncCall
            """
                def func_call():
                    var1 = func(var2)
            """,
            ({"var2": "Name.var2"},
             {"var1": "AssignName.var1"})
        ),
        (  # FuncCall Parameter
            """
                def func_call_par(param):
                    var1 = param + func(param)
            """,
            ({"param": "Name.param",
              "param": "Name.param"},
             {"param": "AssignName.param",
              "var1": "AssignName.var1"})
        ),
        (  # BinOp
            """
                def bin_op():
                    var1 = 20 + var2
            """,
            ({"var2": "Name.var2"},
             {"var1": "AssignName.var1"})
        ),
        (  # BoolOp
            """
                def bool_op():
                    var1 = True and var2
            """,
            ({"var2": "Name.var2"},
             {"var1": "AssignName.var1"})
        ),
        (  # Import
            """
                import math

                def local_import():
                    var1 = math.pi
                    return var1
            """,
            ("Import.math", "AssignName.var1", "MemberAccess.math.pi", "Name.var1")
        # TODO: adapt test when import is implemented
        ),
        (  # Import From
            """
                from math import pi

                def local_import():
                    var1 = pi
                    return var1
            """,
            ("ImportFrom.math.pi", "AssignName.var1", "Name.test", "Name.var1")
        # TODO: adapt test when import is implemented
        ),
        (  # Import From As
            """
                from math import pi as test

                def local_import():
                    var1 = test
                    return var1
            """,
            ("ImportFrom.math.pi.test", "AssignName.var1", "Name.test", "Name.var1")
        # TODO: adapt test when import is implemented
        ),
        (  # ASTWalker
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

            """, ("")
        ),
    ],
    ids=[
        "Assign",
        "Assign Parameter",
        "Global unused",
        "Global and Assign",
        "Assign Class Attribute",
        "Assign Instance Attribute",
        "Assign MemberAccessValue",
        "Assign MemberAccessTarget",
        "AssignAttr",
        "AugAssign",
        "Return",
        "While",
        "For",
        "If",
        "If Else",
        "If Elif",
        "Try Except Finally",
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
def test_get_module_data_value_and_target_nodes(code: str, expected: str) -> None:
    module_data = get_module_data(code)
    value_nodes = module_data.value_nodes
    target_nodes = module_data.target_nodes

    # assert (value_nodes, target_nodes) == expected
    assert_names_list(value_nodes, target_nodes, expected)


def assert_names_list(value_nodes: dict[astroid.Name | MemberAccessValue, Scope | ClassScope],
                      target_nodes: dict[astroid.AssignName | MemberAccessTarget, Scope | ClassScope],
                      expected: str) -> None:
    value_nodes_transformed = transform_value_nodes(value_nodes)
    target_nodes_transformed = transform_target_nodes(target_nodes)
    assert (value_nodes_transformed, target_nodes_transformed) == expected


def transform_value_nodes(value_nodes: dict[astroid.Name | MemberAccessValue, Scope | ClassScope]) -> dict[str, str]:
    value_nodes_transformed = {}
    for node in value_nodes:
        if isinstance(node, astroid.Name):
            value_nodes_transformed.update({node.name: f"{node.__class__.__name__}.{node.name}"})
        elif isinstance(node, MemberAccessValue):
            result = transform_member_access(node)
            value_nodes_transformed.update({result: f"{node.__class__.__name__}.{result}"})

    return value_nodes_transformed


def transform_target_nodes(
    target_nodes: dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope | ClassScope]) -> dict[str, str]:
    target_nodes_transformed = {}
    for node in target_nodes:
        if isinstance(node, astroid.AssignName | astroid.Name):
            target_nodes_transformed.update({node.name: f"{node.__class__.__name__}.{node.name}"})
        elif isinstance(node, MemberAccessTarget):
            result = transform_member_access(node)
            target_nodes_transformed.update({result: f"{node.__class__.__name__}.{result}"})

    return target_nodes_transformed


# def get_symbol(node, scope: Scope | ClassScope) -> str:
#     for child in scope.children:
#         if child.symbol.node == node:
#             return child.symbol.__class__.__name__


def transform_member_access(member_access: MemberAccess) -> str:
    attribute_names = []

    while isinstance(member_access, MemberAccess):
        if isinstance(member_access.member, astroid.AssignAttr | astroid.Attribute):
            attribute_names.append(member_access.member.attrname)
        else:
            attribute_names.append(member_access.member.name)
        member_access = member_access.receiver
    if isinstance(member_access, astroid.Name):
        attribute_names.append(member_access.name)

    return ".".join(reversed(attribute_names))


@pytest.mark.parametrize(
    ("code", "expected"),
    [
    ]
)
def test_get_module_data_function_calls(code: str, expected: str) -> None:
    function_calls = get_module_data(code).classes
    raise NotImplementedError("TODO: implement test")
    assert function_calls == expected
