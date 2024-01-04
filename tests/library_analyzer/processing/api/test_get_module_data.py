from __future__ import annotations

from dataclasses import dataclass, field

import astroid
import pytest
from library_analyzer.processing.api.purity_analysis import (
    calc_node_id,
    get_module_data,
)
from library_analyzer.processing.api.purity_analysis.model import (
    ClassScope,
    MemberAccess,
    MemberAccessTarget,
    MemberAccessValue,
    Reasons,
    Scope,
    Symbol, NodeID,
)


# TODO: refactor: move functions to top of file
@dataclass
class SimpleScope:
    """Class for simple scopes.

    A simplified class of the Scope class for testing purposes.

    Attributes
    ----------
    node_name : str | None
        The name of the node.
    children : list[SimpleScope] | None
        The children of the node.
        None if the node has no children.
    """

    node_name: str | None
    children: list[SimpleScope] | None


@dataclass
class SimpleClassScope(SimpleScope):
    """Class for simple class scopes.

    A simplified class of the ClassScope class for testing purposes.

    Attributes
    ----------
    node_name : str | None
        The name of the node.
    children : list[SimpleScope] | None
        The children of the node.
        None if the node has no children.
    class_variables : list[str]
        The list of class variables.
    instance_variables : list[str]
        The list of instance variables.
    super_class : list[str]
        The list of super classes.
    """

    class_variables: list[str]
    instance_variables: list[str]
    super_class: list[str] = field(default_factory=list)


@dataclass
class SimpleFunctionScope(SimpleScope):
    pass  # TODO: add function scope


@dataclass
class SimpleReasons:
    """Class for simple reasons.

    A simplified class of the Reasons class for testing purposes.

    Attributes
    ----------
    function_name : str
        The name of the function.
    writes : set[SimpleFunctionReference]
        The set of the functions writes.
    reads : set[SimpleFunctionReference]
        The set of the function reads.
    calls : set[SimpleFunctionReference]
        The set of the function calls.
    """

    function_name: str
    writes: set[SimpleFunctionReference] = field(default_factory=set)
    reads: set[SimpleFunctionReference] = field(default_factory=set)
    calls: set[SimpleFunctionReference] = field(default_factory=set)

    def __hash__(self) -> int:
        return hash(self.function_name)


@dataclass
class SimpleFunctionReference:
    """Class for simple function references.

    A simplified class of the FunctionReference class for testing purposes.

    Attributes
    ----------
    node : str
        The name of the node.
    kind : str
        The kind of the Reason as string.
    """

    node: str
    kind: str

    def __hash__(self) -> int:
        return hash((self.node, self.kind))


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
    ],  # TODO: add Import and ImportFrom
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
                    def f(self):
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
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("LocalVariable.AssignName.var1", []),
                                    ],
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

                    def local_class_attr(self):
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
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("LocalVariable.AssignName.var1", []),
                                    ],
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

                    def local_instance_attr(self):
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
                                        SimpleScope("InstanceVariable.MemberAccess.self.instance_attr1", []),
                                    ],
                                ),
                                SimpleScope(
                                    "ClassVariable.FunctionDef.local_instance_attr",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("LocalVariable.AssignName.var1", []),
                                    ],
                                ),
                            ],
                            [
                                "AssignName.local_class_attr1",
                                "AssignName.local_class_attr2",
                                "FunctionDef.__init__",
                                "FunctionDef.local_instance_attr",
                            ],
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
                                        SimpleScope("InstanceVariable.MemberAccess.self.instance_attr1", []),
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
                            [],
                        ),
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.X",
                            [SimpleScope("ClassVariable.AssignName.var3", [])],
                            ["AssignName.var3"],
                            [],
                        ),
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.B",
                            [SimpleScope("ClassVariable.AssignName.var2", [])],
                            ["AssignName.var2"],
                            [],
                            ["ClassDef.A", "ClassDef.X"],
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
        (  # Complex Scope
            """
                def function_scope():
                    var1 = 10

                    def local_function_scope():
                        var2 = 20

                        class local_class_scope:
                            var3 = 30

                            def local_class_function_scope(self):
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
                                                        SimpleScope("Parameter.AssignName.self", []),
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
                            [
                                "AssignName.additional_locals",
                                "FunctionDef.__init__",
                                "FunctionDef.walk",
                                "FunctionDef.__walk",
                                "FunctionDef.__enter",
                                "FunctionDef.__leave",
                                "FunctionDef.__get_callbacks",
                            ],
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
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.A",
                            [
                                SimpleScope("ClassVariable.AssignName.x", []),
                                SimpleScope("ListComp", [SimpleScope("LocalVariable.AssignName.num", [])]),
                            ],
                            ["AssignName.x"],
                            [],
                            [],
                        ),
                    ],
                ),
            ],
        ),
        (  # List Comprehension in Function
            """
                def fun():
                    x = [len(num) for num in nums]
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope(
                            "GlobalVariable.FunctionDef.fun",
                            [
                                SimpleScope("LocalVariable.AssignName.x", []),
                                SimpleScope("ListComp", [SimpleScope("LocalVariable.AssignName.num", [])]),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        (  # With Statement
            """
                with file:
                    a = 1
            """,
            [SimpleScope("Module", [SimpleScope("GlobalVariable.AssignName.a", [])])],
        ),
        (  # With Statement File
            """
                file = "file.txt"
                with open(file, "r") as f:
                    a = 1
                    f.read()
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope("GlobalVariable.AssignName.file", []),
                        SimpleScope("GlobalVariable.AssignName.f", []),
                        SimpleScope("GlobalVariable.AssignName.a", []),
                    ],
                ),
            ],
        ),
        (  # With Statement Function
            """
                def fun():
                    with open("text.txt") as f:
                        text = f.read()
                        print(text)
                        f.close()
            """,
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope(
                            "GlobalVariable.FunctionDef.fun",
                            [
                                SimpleScope("LocalVariable.AssignName.f", []),
                                SimpleScope("LocalVariable.AssignName.text", []),
                            ],
                        ),
                    ],
                ),
            ],
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
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.MyContext",
                            [
                                SimpleScope(
                                    "ClassVariable.FunctionDef.__enter__",
                                    [SimpleScope("Parameter.AssignName.self", [])],
                                ),
                                SimpleScope(
                                    "ClassVariable.FunctionDef.__exit__",
                                    [SimpleScope("Parameter.AssignName.self", [])],
                                ),
                            ],
                            ["FunctionDef.__enter__", "FunctionDef.__exit__"],
                            [],
                            [],
                        ),
                        SimpleScope("GlobalVariable.AssignName.context", []),
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
        "Class Scope with subclass",
        "Class Scope within Function Scope",
        "Function Scope within Function Scope",
        "Complex Scope",
        "ASTWalker",
        "AssignName",
        "List Comprehension in Module",
        "List Comprehension in Class",
        "List Comprehension in Function",
        "With Statement",
        "With Statement File",
        "With Statement Function",
        "With Statement Class",
    ],  # TODO: add tests for lambda, match, try except and generator expressions
    # TODO: add SimpleFunctionScope and adapt the tests
)
def test_get_module_data_scope(code: str, expected: list[SimpleScope | SimpleClassScope]) -> None:
    scope = get_module_data(code).scope
    # assert result == expected
    transformed_result = [
        transform_result(node) for node in scope
    ]  # The result and the expected data are simplified to make the comparison easier
    assert transformed_result == expected


def transform_result(node: Scope | ClassScope) -> SimpleScope | SimpleClassScope:
    """Transform a Scope or ClassScope instance.

    Parameters
    ----------
    node : Scope | ClassScope
        The node to transform.

    Returns
    -------
    SimpleScope | SimpleClassScope
        The transformed node.
    """
    if node.children is not None:
        if isinstance(node, ClassScope):
            instance_vars_transformed = []
            class_vars_transformed = []
            super_classes_transformed = []
            for child in node.instance_variables.values():
                for c in child:
                    c_str = to_string_class(c.node.member)
                    if c_str is not None:
                        instance_vars_transformed.append(c_str)  # type: ignore[misc] # it is not possible that c_str is None
            for child in node.class_variables.values():
                for c in child:
                    c_str = to_string_class(c.node)
                    if c_str is not None:
                        class_vars_transformed.append(c_str)  # type: ignore[misc] # it is not possible that c_str is None

            for klass in node.super_classes:
                c_str = to_string_class(klass)
                if c_str is not None:
                    super_classes_transformed.append(c_str)  # type: ignore[misc] # it is not possible that c_str is None

            return SimpleClassScope(
                to_string(node.symbol),
                [transform_result(child) for child in node.children],
                class_vars_transformed,
                instance_vars_transformed,
                super_classes_transformed,
            )
        return SimpleScope(to_string(node.symbol), [transform_result(child) for child in node.children])
    else:
        return SimpleScope(to_string(node.symbol), [])


def to_string(symbol: Symbol) -> str:
    """Transform a Symbol instance to a string.

    Parameters
    ----------
    symbol : Symbol
        The Symbol instance to transform.

    Returns
    -------
    str
        The transformed Symbol instance as string.
    """
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
        return (  # TODO: handle multiple imports and aliases
            f"{symbol.__class__.__name__}.{symbol.node.__class__.__name__}.{symbol.node.names[0][0]}"
        )
    elif isinstance(symbol.node, astroid.ImportFrom):
        return f"{symbol.__class__.__name__}.{symbol.node.__class__.__name__}.{symbol.node.modname}.{symbol.node.names[0][0]}"  # TODO: handle multiple imports and aliases
    elif isinstance(symbol.node, astroid.Name):
        return f"{symbol.__class__.__name__}.{symbol.node.__class__.__name__}.{symbol.node.name}"
    elif isinstance(symbol.node, astroid.ListComp | astroid.TryExcept | astroid.TryFinally | astroid.With):
        return f"{symbol.node.__class__.__name__}"
    raise NotImplementedError(f"Unknown node type: {symbol.node.__class__.__name__}")


def to_string_class(node: astroid.NodeNG | ClassScope) -> str | None:
    """Transform a NodeNG or ClassScope instance to a string.

    Parameters
    ----------
    node : astroid.NodeNG | ClassScope
        The NodeNG or ClassScope instance to transform.

    Returns
    -------
    str | None
        The transformed NodeNG or ClassScope instance as string.
        None if the node is a Lambda, TryExcept, TryFinally or ListComp instance.
    """
    if isinstance(node, astroid.AssignAttr):
        return f"{node.__class__.__name__}.{node.attrname}"
    elif isinstance(node, astroid.AssignName | astroid.FunctionDef | astroid.ClassDef):
        return f"{node.__class__.__name__}.{node.name}"
    elif isinstance(node, astroid.Lambda | astroid.TryExcept | astroid.TryFinally | astroid.ListComp):
        return None
    elif isinstance(node, ClassScope):
        return f"{node.symbol.node.__class__.__name__}.{node.symbol.node.name}"
    raise NotImplementedError(f"Unknown node type: {node.__class__.__name__}")


@pytest.mark.parametrize(
    ("code", "expected"),
    # expected is a tuple of (ClassDefName, set of class variables, set of instance variables, list of superclasses)
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
            {
                "A": SimpleClassScope(
                    "GlobalVariable.ClassDef.A",
                    [SimpleScope("ClassVariable.AssignName.var1", [])],
                    ["AssignName.var1"],
                    [],
                    [],
                ),
            },
        ),
        (  # ClassDef with multiple class attribute
            """
                class A:
                    var1 = 1
                    var2 = 2
            """,
            {
                "A": SimpleClassScope(
                    "GlobalVariable.ClassDef.A",
                    [
                        SimpleScope("ClassVariable.AssignName.var1", []),
                        SimpleScope("ClassVariable.AssignName.var2", []),
                    ],
                    ["AssignName.var1", "AssignName.var2"],
                    [],
                    [],
                ),
            },
        ),
        (  # ClassDef with multiple class attribute (same name)
            """
                class A:
                    if True:
                        var1 = 1
                    else:
                        var1 = 2
            """,
            {
                "A": SimpleClassScope(
                    "GlobalVariable.ClassDef.A",
                    [
                        SimpleScope("ClassVariable.AssignName.var1", []),
                        SimpleScope("ClassVariable.AssignName.var1", []),
                    ],
                    ["AssignName.var1", "AssignName.var1"],
                    [],
                    [],
                ),
            },
        ),
        (  # ClassDef with instance attribute
            """
                class A:
                    def __init__(self):
                        self.var1 = 1
            """,
            {
                "A": SimpleClassScope(
                    "GlobalVariable.ClassDef.A",
                    [
                        SimpleScope(
                            "ClassVariable.FunctionDef.__init__",
                            [
                                SimpleScope("Parameter.AssignName.self", []),
                                SimpleScope("InstanceVariable.MemberAccess.self.var1", []),
                            ],
                        ),
                    ],
                    ["FunctionDef.__init__"],
                    ["AssignAttr.var1"],
                    [],
                ),
            },
        ),
        (  # ClassDef with multiple instance attributes (and type annotations)
            """
                class A:
                    def __init__(self):
                        self.var1: int = 1
                        self.name: str = "name"
                        self.state: bool = True
            """,
            {
                "A": SimpleClassScope(
                    "GlobalVariable.ClassDef.A",
                    [
                        SimpleScope(
                            "ClassVariable.FunctionDef.__init__",
                            [
                                SimpleScope("Parameter.AssignName.self", []),
                                SimpleScope("InstanceVariable.MemberAccess.self.var1", []),
                                SimpleScope("InstanceVariable.MemberAccess.self.name", []),
                                SimpleScope("InstanceVariable.MemberAccess.self.state", []),
                            ],
                        ),
                    ],
                    ["FunctionDef.__init__"],
                    ["AssignAttr.var1", "AssignAttr.name", "AssignAttr.state"],
                    [],
                ),
            },
        ),
        (  # ClassDef with conditional instance attributes (instance attributes with the same name)
            """
                class A:
                    def __init__(self):
                        if True:
                            self.var1 = 1
                        else:
                            self.var1 = 0
            """,
            {
                "A": SimpleClassScope(
                    "GlobalVariable.ClassDef.A",
                    [
                        SimpleScope(
                            "ClassVariable.FunctionDef.__init__",
                            [
                                SimpleScope("Parameter.AssignName.self", []),
                                SimpleScope("InstanceVariable.MemberAccess.self.var1", []),
                                SimpleScope("InstanceVariable.MemberAccess.self.var1", []),
                            ],
                        ),
                    ],
                    ["FunctionDef.__init__"],
                    ["AssignAttr.var1", "AssignAttr.var1"],
                    [],
                ),
            },
        ),
        (  # ClassDef with class and instance attribute
            """
                class A:
                    var1 = 1

                    def __init__(self):
                        self.var1 = 1
            """,
            {
                "A": SimpleClassScope(
                    "GlobalVariable.ClassDef.A",
                    [
                        SimpleScope("ClassVariable.AssignName.var1", []),
                        SimpleScope(
                            "ClassVariable.FunctionDef.__init__",
                            [
                                SimpleScope("Parameter.AssignName.self", []),
                                SimpleScope("InstanceVariable.MemberAccess.self.var1", []),
                            ],
                        ),
                    ],
                    ["AssignName.var1", "FunctionDef.__init__"],
                    ["AssignAttr.var1"],
                    [],
                ),
            },
        ),
        (  # ClassDef with nested class
            """
                class A:
                    class B:
                        pass
            """,
            {
                "A": SimpleClassScope(
                    "GlobalVariable.ClassDef.A",
                    [SimpleClassScope("ClassVariable.ClassDef.B", [], [], [], [])],
                    ["ClassDef.B"],
                    [],
                    [],
                ),
                "B": SimpleClassScope("ClassVariable.ClassDef.B", [], [], [], []),
            },
        ),
        (  # Multiple ClassDef
            """
                class A:
                    pass

                class B:
                    pass
            """,
            {
                "A": SimpleClassScope("GlobalVariable.ClassDef.A", [], [], [], []),
                "B": SimpleClassScope("GlobalVariable.ClassDef.B", [], [], [], []),
            },
        ),
        (  # ClassDef with superclass
            """
                class A:
                    pass

                class B(A):
                    pass
            """,
            {
                "A": SimpleClassScope("GlobalVariable.ClassDef.A", [], [], [], []),
                "B": SimpleClassScope("GlobalVariable.ClassDef.B", [], [], [], ["ClassDef.A"]),
            },
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
    ],
)
def test_get_module_data_classes(code: str, expected: dict[str, SimpleClassScope]) -> None:
    classes = get_module_data(code).classes

    transformed_classes = {
        klassname: transform_result(klass) for klassname, klass in classes.items()
    }  # The result and the expected data are simplified to make the comparison easier
    assert transformed_classes == expected


@pytest.mark.parametrize(("code", "expected"), [])
def test_get_module_data_functions(code: str, expected: str) -> None:
    functions = get_module_data(code).classes
    raise NotImplementedError("TODO: implement test")
    assert functions == expected


@pytest.mark.parametrize(("code", "expected"), [])
def test_get_module_data_globals(code: str, expected: str) -> None:
    globs = get_module_data(code).classes
    raise NotImplementedError("TODO: implement test")
    assert globs == expected


@pytest.mark.parametrize(("code", "expected"), [])
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
            ({}, {"var1": "AssignName.var1"}),
        ),
        (  # Assign Parameter
            """
                def parameter(a):
                    var1 = a
            """,
            ({"a": "Name.a"}, {"var1": "AssignName.var1", "a": "AssignName.a"}),
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
            ({"glob1": "Name.glob1"}, {"var1": "AssignName.var1"}),
        ),
        (  # Assign Class Attribute
            """
                def class_attr():
                    var1 = A.class_attr
            """,
            ({"A": "Name.A", "A.class_attr": "MemberAccessValue.A.class_attr"}, {"var1": "AssignName.var1"}),
        ),
        (  # Assign Instance Attribute
            """
                def instance_attr():
                    b = B()
                    var1 = b.instance_attr
            """,
            (
                {"b": "Name.b", "b.instance_attr": "MemberAccessValue.b.instance_attr"},
                {"b": "AssignName.b", "var1": "AssignName.var1"},
            ),
        ),
        (  # Assign MemberAccessValue
            """
                def chain():
                    var1 = test.instance_attr.field.next_field
            """,
            (
                {
                    "test": "Name.test",
                    "test.instance_attr": "MemberAccessValue.test.instance_attr",
                    "test.instance_attr.field": "MemberAccessValue.test.instance_attr.field",
                    "test.instance_attr.field.next_field": "MemberAccessValue.test.instance_attr.field.next_field",
                },
                {"var1": "AssignName.var1"},
            ),
        ),
        (  # Assign MemberAccessTarget
            """
                def chain_reversed():
                    test.instance_attr.field.next_field = var1
            """,
            (
                {"var1": "Name.var1"},
                {
                    "test": "Name.test",
                    "test.instance_attr": "MemberAccessTarget.test.instance_attr",
                    "test.instance_attr.field": "MemberAccessTarget.test.instance_attr.field",
                    "test.instance_attr.field.next_field": "MemberAccessTarget.test.instance_attr.field.next_field",
                },
            ),
        ),
        (  # AssignAttr
            """
                def assign_attr():
                    a.res = 1
            """,
            ({}, {"a": "Name.a", "a.res": "MemberAccessTarget.a.res"}),
        ),
        (  # AugAssign
            """
                def aug_assign():
                    var1 += 1
            """,
            ({}, {"var1": "AssignName.var1"}),
        ),
        (  # Return
            """
                def assign_return():
                    return var1
            """,
            ({"var1": "Name.var1"}, {}),
        ),
        (  # While
            """
                def while_loop():
                    while var1 > 0:
                        do_something()
            """,
            ({"var1": "Name.var1"}, {}),
        ),
        (  # For
            """
                def for_loop():
                    for var1 in range(10):
                        do_something()
            """,
            ({}, {"var1": "AssignName.var1"}),
        ),
        (  # If
            """
                def if_state():
                    if var1 > 0:
                        do_something()
            """,
            ({"var1": "Name.var1"}, {}),
        ),
        (  # If Else
            """
                def if_else_state():
                    if var1 > 0:
                        do_something()
                    else:
                        do_something_else()
            """,
            ({"var1": "Name.var1"}, {}),
        ),
        (  # If Elif
            """
                def if_elif_state():
                    if var1 & True:
                        do_something()
                    elif var1 | var2:
                        do_something_else()
            """,
            ({"var1": "Name.var1", "var2": "Name.var2"}, {}),
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
            (
                {"error": "Name.error", "num1": "Name.num1", "num2": "Name.num2", "num3": "Name.num3"},
                {"error": "AssignName.error", "final": "AssignName.final", "result": "AssignName.result"},
            ),
        ),
        (  # AnnAssign
            """
                def ann_assign():
                    var1: int = 10
            """,
            ({}, {"var1": "AssignName.var1"}),
        ),
        (  # FuncCall
            """
                def func_call():
                    var1 = func(var2)
            """,
            ({"var2": "Name.var2"}, {"var1": "AssignName.var1"}),
        ),
        (  # FuncCall Parameter
            """
                def func_call_par(param):
                    var1 = param + func(param)
            """,
            ({"param": "Name.param"}, {"param": "AssignName.param", "var1": "AssignName.var1"}),
        ),
        (  # BinOp
            """
                def bin_op():
                    var1 = 20 + var2
            """,
            ({"var2": "Name.var2"}, {"var1": "AssignName.var1"}),
        ),
        (  # BoolOp
            """
                def bool_op():
                    var1 = True and var2
            """,
            ({"var2": "Name.var2"}, {"var1": "AssignName.var1"}),
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
    ],
)
def test_get_module_data_value_and_target_nodes(code: str, expected: str) -> None:
    module_data = get_module_data(code)
    value_nodes = module_data.value_nodes
    target_nodes = module_data.target_nodes

    # assert (value_nodes, target_nodes) == expected
    value_nodes_transformed = transform_value_nodes(value_nodes)
    target_nodes_transformed = transform_target_nodes(target_nodes)
    assert (value_nodes_transformed, target_nodes_transformed) == expected


def transform_value_nodes(value_nodes: dict[astroid.Name | MemberAccessValue, Scope | ClassScope]) -> dict[str, str]:
    """Transform the value nodes.

    The value nodes are transformed to a dictionary with the name of the node as key and the transformed node as value.

    Parameters
    ----------
    value_nodes : dict[astroid.Name | MemberAccessValue, Scope | ClassScope]
        The value nodes to transform.

    Returns
    -------
    dict[str, str]
        The transformed value nodes.
    """
    value_nodes_transformed = {}
    for node in value_nodes:
        if isinstance(node, astroid.Name):
            value_nodes_transformed.update({node.name: f"{node.__class__.__name__}.{node.name}"})
        elif isinstance(node, MemberAccessValue):
            result = transform_member_access(node)
            value_nodes_transformed.update({result: f"{node.__class__.__name__}.{result}"})

    return value_nodes_transformed


def transform_target_nodes(
    target_nodes: dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope | ClassScope],
) -> dict[str, str]:
    """Transform the target nodes.

    The target nodes are transformed to a dictionary with the name of the node as key and the transformed node as value.

    Parameters
    ----------
    target_nodes : dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope | ClassScope]

    Returns
    -------
    dict[str, str]
        The transformed target nodes.
    """
    target_nodes_transformed = {}
    for node in target_nodes:
        if isinstance(node, astroid.AssignName | astroid.Name):
            target_nodes_transformed.update({node.name: f"{node.__class__.__name__}.{node.name}"})
        elif isinstance(node, MemberAccessTarget):
            result = transform_member_access(node)
            target_nodes_transformed.update({result: f"{node.__class__.__name__}.{result}"})

    return target_nodes_transformed


def transform_member_access(member_access: MemberAccess) -> str:
    """Transform a MemberAccess instance to a string.

    Parameters
    ----------
    member_access : MemberAccess
        The MemberAccess instance to transform.

    Returns
    -------
    str
        The transformed MemberAccess instance as string.
    """
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


@pytest.mark.parametrize(("code", "expected"), [])
def test_get_module_data_function_calls(code: str, expected: str) -> None:
    function_calls = get_module_data(code).function_calls
    raise NotImplementedError("TODO: implement test")
    assert function_calls == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "internal stuff"
            """
b = 1
c = 2
d = 3
def g():
    pass

def f():
    # global b  # TODO: [LATER] to detect this case, we need to collect the global statements on function level
    a = 1  # LocaleWrite
    b = 2  # NonLocalVariableWrite
    a      # LocaleRead
    c      # NonLocalVariableRead
    b = d  # NonLocalVariableWrite, NonLocalVariableRead
    g()    # Call
    x = open("text.txt") # LocalWrite, Call
            """,  # language=none
            {
                ".f.8.0": SimpleReasons(
                    "f",
                    {
                        SimpleFunctionReference("AssignName.b.line11", "NonLocalVariableWrite"),
                        SimpleFunctionReference("AssignName.b.line14", "NonLocalVariableWrite"),
                    },
                    {
                        SimpleFunctionReference("Name.c.line13", "NonLocalVariableRead"),
                        SimpleFunctionReference("Name.d.line14", "NonLocalVariableRead"),
                    },
                    {
                        SimpleFunctionReference("Call.g.line15", "Call"),
                        SimpleFunctionReference("Call.open.line16", "Call"),
                    },
                ),
                ".g.5.0": SimpleReasons("g", set(), set(), set()),
            },
        ),
        (  # language=Python "control flow statements"
            """
b = 1
c = 0

def f():
    global b, c
    if b > 1:  # we ignore all control flow statements
        a = 1  # LocaleWrite
    else:
        c = 2  # NonLocalVariableWrite

    while a < 10:  # we ignore all control flow statements
        b += 1  # NonLocalVariableWrite
            """,  # language=none
            {
                ".f.5.0": SimpleReasons(
                    "f",
                    {
                        SimpleFunctionReference("AssignName.c.line10", "NonLocalVariableWrite"),
                        SimpleFunctionReference("AssignName.b.line13", "NonLocalVariableWrite"),
                    },
                ),
            },
        ),
        (  # language=Python "class attribute"
            """
class A:
    class_attr1 = 20

def f():
    a = A()
    a.class_attr1 = 10  # NonLocalVariableWrite

def g():
    a = A()
    c = a.class_attr1  # NonLocalVariableRead
            """,  # language=none
            {
                ".f.5.0": SimpleReasons(
                    "f",
                    {
                        SimpleFunctionReference("MemberAccessTarget.a.class_attr1.line7", "MemberAccessTarget"),
                    },
                    set(),
                    {
                        SimpleFunctionReference("Call.A.line6", "Call"),
                    }
                ),
                ".g.9.0": SimpleReasons(
                    "g",
                    set(),
                    {
                        SimpleFunctionReference("MemberAccessValue.a.class_attr1.line11", "MemberAccessValue"),
                    },
                    {
                        SimpleFunctionReference("Call.A.line10", "Call"),
                    }
                ),
            },
        ),
        (  # language=Python "instance attribute"
            """
class A:
    def __init__(self):
        self.instance_attr1 = 20

def f1():
    a = A()
    a.instance_attr1 = 10  # NonLocalVariableWrite  # TODO [Later] we should detect that this is a local variable

b = A()
def f2(x):
    x.instance_attr1 = 10  # NonLocalVariableWrite

def f3():
    global b
    b.instance_attr1 = 10  # NonLocalVariableWrite

def g1():
    a = A()
    c = a.instance_attr1  # NonLocalVariableWrite  # TODO [Later] we should detect that this is a local variable

def g2(x):
    c = x.instance_attr1  # NonLocalVariableRead

def g3():
    global b
    c = b.instance_attr1  # NonLocalVariableRead
            """,  # language=none
            {
                ".__init__.3.4": SimpleReasons(
                    "__init__"
                ),
                ".f1.6.0": SimpleReasons(
                    "f1", {
                        SimpleFunctionReference("MemberAccessTarget.a.instance_attr1.line8", "MemberAccessTarget"),
                    },
                    set(),
                    {SimpleFunctionReference("Call.A.line7", "Call")}
                ),
                ".f2.11.0": SimpleReasons(
                    "f2",
                    {
                        SimpleFunctionReference("MemberAccessTarget.x.instance_attr1.line12", "MemberAccessTarget"),
                    },
                ),
                ".f3.14.0": SimpleReasons(
                    "f3",
                    {
                        SimpleFunctionReference("MemberAccessTarget.b.instance_attr1.line16", "MemberAccessTarget"),
                    },
                ),
                ".g1.18.0": SimpleReasons(
                    "g1", set(), {
                        SimpleFunctionReference("MemberAccessValue.a.instance_attr1.line20", "MemberAccessValue"),
                    }, {SimpleFunctionReference("Call.A.line19", "Call")}
                ),
                ".g2.22.0": SimpleReasons(
                    "g2",
                    set(),
                    {
                        SimpleFunctionReference("MemberAccessValue.x.instance_attr1.line23", "MemberAccessValue"),
                    },
                ),
                ".g3.25.0": SimpleReasons(
                    "g3",
                    set(),
                    {
                        SimpleFunctionReference("MemberAccessValue.b.instance_attr1.line27", "MemberAccessValue"),
                    },
                ),
            },
        ),
        (  # language=Python "chained attributes"
            """
class A:
    def __init__(self):
        self.name = 10

    def set_name(self, name):
        self.name = name

class B:
    upper_class: A = A()

def f():
    b = B()
    x = b.upper_class.name
    b.upper_class.set_name("test")
            """,  # language=none
            {
                ".__init__.3.4": SimpleReasons(
                    "__init__"
                ),
                ".set_name.6.4": SimpleReasons(
                    "set_name",
                    {SimpleFunctionReference("MemberAccessTarget.self.name.line7", "MemberAccessTarget")}
                ),
                ".f.12.0": SimpleReasons(
                    "f",
                    set(),
                    {
                        SimpleFunctionReference("MemberAccessValue.b.upper_class.name.line14", "MemberAccessValue"),
                        SimpleFunctionReference("MemberAccessValue.b.upper_class.line14", "MemberAccessValue"),
                        SimpleFunctionReference("MemberAccessValue.b.upper_class.line15", "MemberAccessValue"),
                    },
                    {
                        SimpleFunctionReference("Call.B.line13", "Call"),
                        SimpleFunctionReference("Call.set_name.line15", "Call"),
                    }
                ),
            }
        ),
        (  # language=Python "chained class function call"
            """
class B:
    def __init__(self):
        self.b = 20

    def f(self):
        pass

class A:
    class_attr1 = B()

def g():
    A().class_attr1.f()
            """,  # language=none
            {
                ".__init__.3.4": SimpleReasons(
                    "__init__"
                ),
                ".f.6.4": SimpleReasons(
                    "f", set(), set(), set()
                ),
                ".g.12.0": SimpleReasons(
                    "g",
                    set(),
                    set(),
                    {
                        SimpleFunctionReference("Call.A.line13", "Call"),
                        SimpleFunctionReference("Call.f.line13", "Call"),
                    }
                ),
            }
        ),
        (  # language=Python "two classes with same attribute name"
            """
class A:
    name: str = ""

    def __init__(self, name: str):
        self.name = name

class B:
    name: str = ""

    def __init__(self, name: str):
        self.name = name

def f():
    a = A("value")
    b = B("test")
    a.name
    b.name
            """,  # language=none
            {
                ".__init__.5.4": SimpleReasons(
                    "__init__"
                ),
                ".__init__.11.4": SimpleReasons(
                    "__init__"
                ),
                ".f.14.0": SimpleReasons(
                    "f",
                    set(),
                    {
                        SimpleFunctionReference("MemberAccessValue.a.name.line17", "MemberAccessValue"),
                        SimpleFunctionReference("MemberAccessValue.b.name.line18", "MemberAccessValue"),
                    },
                    {
                        SimpleFunctionReference("Call.A.line15", "Call"),
                        SimpleFunctionReference("Call.B.line16", "Call"),
                    }
                )
            }
        ),
        (  # language=Python "multiple classes with same function name - same signature"
            """
z = 2

class A:
    @staticmethod
    def add(a, b):
        global z
        return a + b + z

class B:
    @staticmethod
    def add(a, b):
        return a + 2 * b

def f():
    x = A.add(1, 2)
    y = B.add(1, 2)
    if x == y:
        pass
            """,  # language=none
            {
                ".add.6.4": SimpleReasons(
                    "add",
                    set(),
                    {
                        SimpleFunctionReference("Name.z.line3", "NonLocalVariableRead")
                    },
                    set()
                ),
                ".add.12.4": SimpleReasons(
                    "add",
                ),
                ".f.15.0": SimpleReasons(
                    "f",
                    set(),
                    set(),
                    {
                        SimpleFunctionReference("Call.add.line16", "Call"),
                        SimpleFunctionReference("Call.add.line17", "Call"),
                    }
                )
            }
        ),  # since we only return a list of all possible references, we can't distinguish between the two functions
        (  # language=Python "multiple classes with same function name - different signature"
            """
class A:
    @staticmethod
    def add(a, b):
        return a + b

class B:
    @staticmethod
    def add(a, b, c):
        return a + b + c

def f():
    A.add(1, 2)
    B.add(1, 2, 3)
            """,  # language=none
            {
                ".add.4.4": SimpleReasons(
                    "add",
                ),
                ".add.9.4": SimpleReasons(
                    "add",
                ),
                ".f.12.0": SimpleReasons(
                    "f",
                    set(),
                    set(),
                    {
                        SimpleFunctionReference("Call.add.line13", "Call"),
                        SimpleFunctionReference("Call.add.line14", "Call"),
                    }
                )
            }
        ),  # TODO: [LATER] we should detect the different signatures
    ],
    ids=[
        "internal stuff",
        "control flow statements",
        "class attribute",
        "instance attribute",
        "chained attributes",
        "chained class function call",
        "two classes with same attribute name",
        "multiple classes with same function name - same signature",  # TODO: Fix the bug where z is not detected as NonLocalVariableRead
        "multiple classes with same function name - different signature",  # TODO: [LATER] we should detect the different signatures
        ],
)
def test_get_module_data_function_references(code: str, expected: dict[str, SimpleReasons]) -> None:
    function_references = get_module_data(code).function_references

    transformed_function_references = transform_function_references(function_references)
    # assert function_references == expected

    assert transformed_function_references == expected


def transform_function_references(function_calls: dict[NodeID, Reasons]) -> dict[str, SimpleReasons]:
    """Transform the function references.

    The function references are transformed to a dictionary with the name of the function as key
    and the transformed Reasons instance as value.

    Parameters
    ----------
    function_calls : dict[str, Reasons]
        The function references to transform.

    Returns
    -------
    dict[str, SimpleReasons]
        The transformed function references.
    """
    transformed_function_references = {}
    for function_id, function_references in function_calls.items():
        transformed_function_references.update({
            function_id.__str__(): SimpleReasons(
                function_references.function.name,
                {
                    SimpleFunctionReference(
                        f"{function_reference.node.__class__.__name__}.{function_reference.node.name}.line{function_reference.node.member.fromlineno}",
                        function_reference.kind,
                    ) if isinstance(function_reference.node, MemberAccessTarget) else
                    SimpleFunctionReference(
                         f"{function_reference.node.__class__.__name__}.{function_reference.node.name}.line{function_reference.node.fromlineno}",
                         function_reference.kind,
                    )
                    for function_reference in function_references.writes
                },
                {
                    SimpleFunctionReference(
                        f"{function_reference.node.__class__.__name__}.{function_reference.node.name}.line{function_reference.node.member.fromlineno}",
                        function_reference.kind,
                    ) if isinstance(function_reference.node, MemberAccessValue) else
                    SimpleFunctionReference(
                         f"{function_reference.node.__class__.__name__}.{function_reference.node.name}.line{function_reference.node.fromlineno}",
                         function_reference.kind,
                    )
                    for function_reference in function_references.reads
                },
                {
                    SimpleFunctionReference(
                        f"{function_reference.node.__class__.__name__}.{function_reference.node.func.attrname}.line{function_reference.node.fromlineno}",
                        function_reference.kind,
                    ) if isinstance(function_reference.node.func, astroid.Attribute) else
                    SimpleFunctionReference(
                        f"{function_reference.node.__class__.__name__}.{function_reference.node.func.name}.line{function_reference.node.fromlineno}",
                        function_reference.kind,
                    )
                    for function_reference in function_references.calls
                },
            ),
        })

    return transformed_function_references


# TODO: testcases for cyclic calls and recursive calls
