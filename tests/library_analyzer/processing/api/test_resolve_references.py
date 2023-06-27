from __future__ import annotations

from dataclasses import dataclass

import astroid
import pytest
from library_analyzer.processing.api import (
    MemberAccess,
    ScopeNode,
    calc_node_id,
    get_name_nodes,
    get_scope,
    Variables,
    NodeReference,
    create_references,
    find_references,
)


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
    module = astroid.parse(code)
    # print(module.repr_tree(), "\n")
    names_list = get_name_nodes(module)

    assert_names_list(names_list, expected)


def assert_names_list(names_list: list[astroid.Name], expected: str) -> None:
    names_list = transform_names_list(names_list)
    # for name in names_list:
    #     print(name)
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
    result = calc_node_id(node)
    assert result.__str__() == expected


@pytest.mark.parametrize(
    ("node", "expected"),
    [
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0))],
            [NodeReference(astroid.Name("var1", lineno=1, col_offset=4), "func1.var1.1.4",
                           ScopeNode(astroid.Name("var1", lineno=1, col_offset=4),
                                     None, None))]
        ),
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
             astroid.Name("var2", lineno=2, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
             astroid.Name("var3", lineno=30, col_offset=4,
                          parent=astroid.FunctionDef("func2", lineno=1, col_offset=0))],
            [NodeReference(astroid.Name("var1", lineno=1, col_offset=4), "func1.var1.1.4",
                           ScopeNode(astroid.Name("var1", lineno=1, col_offset=4),
                                     None, None)),
             NodeReference(astroid.Name("var2", lineno=2, col_offset=4), "func1.var2.2.4",
                           ScopeNode(astroid.Name("var2", lineno=2, col_offset=4),
                                     None, None)),
             NodeReference(astroid.Name("var3", lineno=30, col_offset=4), "func2.var3.30.4",
                           ScopeNode(astroid.Name("var3", lineno=30, col_offset=4),
                                     None, None))]
        ),
        (
            [astroid.AssignName("var1", lineno=12, col_offset=42,
                                parent=astroid.FunctionDef("func1", lineno=1, col_offset=0))],
            [NodeReference(astroid.AssignName("var1", lineno=12, col_offset=42), "func1.var1.12.42",
                           ScopeNode(astroid.AssignName("var1", lineno=12, col_offset=42),
                                     None, None))]
        ),
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
             astroid.AssignName("var2", lineno=1, col_offset=8,
                                parent=astroid.FunctionDef("func1", lineno=1, col_offset=0))],
            [NodeReference(astroid.Name("var1", lineno=1, col_offset=4), "func1.var1.1.4",
                           ScopeNode(astroid.Name("var1", lineno=1, col_offset=4),
                                     None, None)),
             NodeReference(astroid.AssignName("var2", lineno=1, col_offset=8), "func1.var2.1.8",
                           ScopeNode(astroid.AssignName("var2", lineno=1, col_offset=8),
                                     None, None))]
        ),
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.ClassDef("MyClass", lineno=1, col_offset=0))],
            [NodeReference(astroid.Name("var1", lineno=1, col_offset=4), "MyClass.var1.1.4",
                           ScopeNode(astroid.Name("var1", lineno=1, col_offset=4),
                                     None, None))]
        ),
        (
            [astroid.Name("glob", lineno=1, col_offset=4, parent=astroid.Module("mod"))],
            [NodeReference(astroid.Name("glob", lineno=1, col_offset=4), "mod.glob.1.4",
                           ScopeNode(astroid.Name("glob", lineno=1, col_offset=4), None, None))]
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
def test_construct_reference_list(node: list[astroid.Name | astroid.AssignName], expected) -> None:
    result = create_references(node)
    assert_reference_list_equal(result, expected)


def assert_reference_list_equal(result: list[NodeReference], expected: list[NodeReference]) -> None:
    """ The result data as well as the expected data in this test is simplified, so it is easier to compare the results.
    The real results name and scope are objects and not strings"""
    result = [
        NodeReference(name.name.name, name.node_id, name.scope.children.__class__.__name__, name.referenced_declarations) for name in result]
    expected = [
        NodeReference(name.name.name, name.node_id, name.scope.children.__class__.__name__, name.referenced_declarations) for name in expected]
    assert result == expected

# TODO: test this when resolve reference is implemented (disabled for now due to test failures)
# def test_add_potential_value_reference() -> None:
#     raise NotImplementedError("Test not implemented")

# TODO: test this when resolve reference is implemented (disabled for now due to test failures)
# def test_add_potential_target_reference() -> None:
#     raise NotImplementedError("Test not implemented")


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (
            """
                def local_const():
                    var1 = 20
                    var2 = 40
                    res = var1 + var2
                    if res > 0:
                        res = var1 - var2
                    return res
            """,
            []
        ),
        (
            """
                def local_parameter(a):
                    var1 = 2 * a
                    return var1

                local_parameter(10)
            """,
            []
        ),
        (
            """
                glob1 = 10
                def local_global():

                    res = glob1
                    if res > 0:
                        global glob1
                        glob1 = 20
                    else:
                        glob1 = 30

                    return glob1
            """,
            ["glob1"]
        ),
        (
            """
                class A:
                    class_attr1 = 20

                def local_class_attr():
                    var1 = A.class_attr1
                    return var1
            """,
            []
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
            []
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

            """, []
        )
    ],
    ids=[
        "constant as local variable",
        "parameter as local variable",
        "global as local variable",
        "class attribute as local variable",
        "instance attribute as local variable",
        "ASTWalker"
    ]
)
def test_find_references(code, expected):
    module = astroid.parse(code)
    all_names_list = get_name_nodes(module)
    # print(all_names_list)
    references = [find_references(all_names_list)]

    for reference in references:
        print(reference, "\n")
        # print(resolved[0].node_id.module, "\n")
        assert reference == expected


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
            SimpleVariables(["A.class_variable"], []),
        ),
        (
            """
            class B:
                class_variable1 = 1
                class_variable2 = 2
            """,
            SimpleVariables(["B.class_variable1", "B.class_variable2"], []),
        ),
        (
            """
            class C:
                def __init__(self):
                    self.instance_variable = 1
            """,
            SimpleVariables([], ["C.instance_variable"]),
        ),
        (
            """
            class D:
                def __init__(self):
                    self.instance_variable1 = 1
                    self.instance_variable2 = 2
            """,
            SimpleVariables([], ["D.instance_variable1", "D.instance_variable2"]),
        ),
        (
            """
            class E:
                class_variable = 1

                def __init__(self):
                    self.instance_variable = 1
            """,
            SimpleVariables(["E.class_variable"], ["E.instance_variable"]),
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
            SimpleVariables(["ASTWalker.additional_locals"], ["ASTWalker._handler", "ASTWalker._cache"]),
        ),
        (
            """
            class F:
                var = 1

                def __init__(self):
                    self.var = 1
            """,
            SimpleVariables(["F.var"], ["F.var"]),
        ),
        (
            """
            class G:
                var: int = 1
            """,
            SimpleVariables(["G.var"], []),
        )
    ],
    ids=[
        "Class Variable",
        "Multiple Class Variables",
        "Instance Variable",
        "Multiple Instance Variables",
        "Class and Instance Variable",
        "ASTWalker",
        "Class and Instance Variable with same name",  # is this something we want to support?
        "Type Annotation"
    ]
)
def test_distinguish_class_variables(code: str, expected: SimpleVariables) -> None:
    module = astroid.parse(code)
    result = get_scope(module)
    result = transform_variables(result[1])
    assert result == expected


def transform_variables(variables: Variables) -> SimpleVariables:
    class_var = [to_string_var(variable) for variable in variables.class_variables]
    instance_var = [to_string_var(variable) for variable in variables.instance_variables]
    return SimpleVariables(class_var, instance_var)


def to_string_var(node: astroid.AssignName | astroid.AssignAttr) -> str | None:
    if isinstance(node, astroid.AssignName):
        return f"{node.parent.parent.name}.{node.name}"
    elif isinstance(node, astroid.AssignAttr):
        return f"{node.parent.parent.parent.name}.{node.attrname}"
    return None
