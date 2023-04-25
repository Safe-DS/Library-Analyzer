from dataclasses import dataclass, field

import pytest
import astroid

from library_analyzer.processing.api import (
    find_references,
    get_name_nodes, create_references, NodeReference, calc_node_id, NodeScope, get_nodes_for_scope, MemberAccess,
)
from library_analyzer.processing.api._resolve_references import Scopes, get_scope


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (
            """
                def variable():
                    var1 = 20
            """,
            ["AssignName.var1"]
        ),
        (
            """
                def parameter(a):
                    var1 = a
            """,
            ['AssignName.a', 'AssignName.var1', 'Name.a']
        ),
        (
            """
                def glob():
                    global glob1
            """,
            []
        ),
        (
            """
                def glob():
                    global glob1
                    var1 = glob1
            """,
            ['AssignName.var1', 'Name.glob1']
        ),
        (
            """
                def class_attr():
                    var1 = A.class_attr
            """,
            ['AssignName.var1', 'MemberAccess.A.class_attr']
        ),
        (
            """
                def instance_attr():
                    b = B()
                    var1 = b.instance_attr
            """,
            ['AssignName.b', 'AssignName.var1', 'MemberAccess.b.instance_attr']
        ),
        (
            """
                def chain():
                    var1 = test.instance_attr.field.next_field
            """,
            ['AssignName.var1',
             'MemberAccess.test.instance_attr.field.next_field',
             'MemberAccess.test.instance_attr.field',
             'MemberAccess.test.instance_attr']
        ),
        (
            """
                def chain_reversed():
                    test.instance_attr.field.next_field = var1
            """,
            ['MemberAccess.test.instance_attr.field.next_field',
             'MemberAccess.test.instance_attr.field',
             'MemberAccess.test.instance_attr',
             'Name.var1']
        ),
        (
            """
                def aug_assign():
                    var1 += 1
            """, ['AssignName.var1']
        ),
        (
            """
                def assign_attr():
                    a.res = 1
            """, ["MemberAccess.a.res"]
        ),
        (
            """
                def assign_return():
                    return var1
            """, ['Name.var1']
        ),
        (
            """
                def while_loop():
                    while var1 > 0:
                        do_something()
            """, ['Name.var1']
        ),
        (
            """
                def for_loop():
                    for var1 in range(10):
                        do_something()
            """, ['AssignName.var1']
        ),
        (
            """
                def if_state():
                    if var1 > 0:
                        do_something()
            """, ['Name.var1']
        ),
        (
            """
                def if_else_state():
                    if var1 > 0:
                        do_something()
                    else:
                        do_something_else()
            """, ['Name.var1']
        ),
        (
            """
                def if_elif_state():
                    if var1 & True:
                        do_something()
                    elif var1 | var2:
                        do_something_else()
            """, ['Name.var1', 'Name.var1', 'Name.var2']
        ),
        (
            """
                def ann_assign():
                    var1: int = 10
            """, ['AssignName.var1']
        ),
        (
            """
                def func_call():
                    var1 = func(var2)
            """, ['AssignName.var1', 'Name.var2']
        ),
        (
            """
                def func_call_par(param):
                    var1 = param + func(param)
            """, ['AssignName.param', 'AssignName.var1', 'Name.param', 'Name.param']
        ),
        (
            """
                def bin_op():
                    var1 = 20 + var2
            """, ['AssignName.var1', 'Name.var2']
        ),
        (
            """
                def bool_op():
                    var1 = True and var2
            """, ['AssignName.var1', 'Name.var2']
        ),
        (
            """
                import math

                def local_import():
                    var1 = math.pi
                    return var1
            """,
            ["ImportName.math", "AssignName.var1", "MemberAccess.math.pi", "Name.var1"]
        ),
        (
            """
                from math import pi

                def local_import():
                    var1 = pi
                    return var1
            """,
            ["ImportName.math.pi", "AssignName.var1", "Name.test", "Name.var1"]
        ),
        (
            """
                from math import pi as test

                def local_import():
                    var1 = test
                    return var1
            """,
            ["ImportName.math.pi.test", "AssignName.var1", "Name.test", "Name.var1"]
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
        )
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
    ]
)
def test_get_name_nodes(code: str, expected: str) -> None:
    module = astroid.parse(code)
    print(module.repr_tree(), "\n")
    names_list = get_name_nodes(module)
    names_list_joined = [element for name in names_list for element in name]

    assert_names_list(names_list_joined, expected)


def assert_names_list(names_list: list[astroid.Name], expected: str) -> None:
    names_list = transform_names_list(names_list)
    # for name in names_list:
    #     print(name)
    assert names_list == expected


def transform_names_list(names_list):
    names_list_transformed = []
    for name in names_list:
        if isinstance(name, astroid.Name | astroid.AssignName):
            names_list_transformed.append(f"{name.__class__.__name__}.{name.name}")
        elif isinstance(name, MemberAccess):
            attribute_names = []

            while isinstance(name, MemberAccess):
                attribute_names.append(name.value.name)
                name = name.expression
            if isinstance(name, astroid.Name):
                attribute_names.append(name.name)

            result = '.'.join(reversed(attribute_names))
            names_list_transformed.append(f"MemberAccess.{result}")

    return names_list_transformed


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
            astroid.FunctionDef("local_func", lineno=1, col_offset=0, parent=astroid.ClassDef("A", lineno=2, col_offset=3)),
            "A.local_func.1.0",
        ),
        (
            astroid.FunctionDef("global_func", lineno=1, col_offset=0, parent=astroid.ClassDef("A", lineno=2, col_offset=3, parent=astroid.Module("numpy"))),
            "numpy.global_func.1.0",
        ),
        (
            astroid.AssignName("var1", lineno=1, col_offset=5, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
            "func1.var1.1.5",
        ),
        (
            astroid.Name("var2", lineno=20, col_offset=0, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
            "func1.var2.20.0",
        ),
        (
            astroid.Name("glob", lineno=20, col_offset=0, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0, parent=astroid.ClassDef("A", lineno=2, col_offset=3, parent=astroid.Module("numpy")))),
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
    ]
)
def test_calc_function_id_new(node: astroid.Module | astroid.ClassDef | astroid.FunctionDef | astroid.AssignName | astroid.Name, expected: str) -> None:
    result = calc_node_id(node)
    assert result.__str__() == expected


@pytest.mark.parametrize(
    ("node", "expected"),
    [
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0))],
            [NodeReference(astroid.Name("var1", lineno=1, col_offset=4), "func1.var1.1.4", NodeScope(astroid.Name("var1", lineno=1, col_offset=4), astroid.FunctionDef("func1", lineno=1, col_offset=0)), [], False)]
        ),
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
             astroid.Name("var2", lineno=2, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
             astroid.Name("var3", lineno=30, col_offset=4, parent=astroid.FunctionDef("func2", lineno=1, col_offset=0))],
            [NodeReference(astroid.Name("var1", lineno=1, col_offset=4), "func1.var1.1.4", NodeScope(astroid.Name("var1", lineno=1, col_offset=4), astroid.FunctionDef("func1", lineno=1, col_offset=0)), [], False),
             NodeReference(astroid.Name("var2", lineno=2, col_offset=4), "func1.var2.2.4", NodeScope(astroid.Name("var2", lineno=2, col_offset=4), astroid.FunctionDef("func1", lineno=1, col_offset=0)), [], False),
             NodeReference(astroid.Name("var3", lineno=30, col_offset=4), "func2.var3.30.4", NodeScope(astroid.Name("var3", lineno=30, col_offset=4), astroid.FunctionDef("func2", lineno=1, col_offset=0)), [], False)]
        ),
        (
            [astroid.AssignName("var1", lineno=12, col_offset=42, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0))],
            [NodeReference(astroid.AssignName("var1", lineno=12, col_offset=42), "func1.var1.12.42", NodeScope(astroid.AssignName("var1", lineno=12, col_offset=42), astroid.FunctionDef("func1", lineno=1, col_offset=0)), [], False)]
        ),
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
             astroid.AssignName("var2", lineno=1, col_offset=8, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0))],
            [NodeReference(astroid.Name("var1", lineno=1, col_offset=4), "func1.var1.1.4", NodeScope(astroid.Name("var1", lineno=1, col_offset=4), astroid.FunctionDef("func1", lineno=1, col_offset=0)), [], False),
             NodeReference(astroid.AssignName("var2", lineno=1, col_offset=8), "func1.var2.1.8", NodeScope(astroid.AssignName("var2", lineno=1, col_offset=8), astroid.FunctionDef("func1", lineno=1, col_offset=0)), [], False)]
        ),
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.ClassDef("MyClass", lineno=1, col_offset=0))],
            [NodeReference(astroid.Name("var1", lineno=1, col_offset=4), "MyClass.var1.1.4",
                           NodeScope(astroid.Name("var1", lineno=1, col_offset=4), astroid.ClassDef("MyClass", lineno=1, col_offset=0)), [], False)]
        ),
        (
            [astroid.Name("glob", lineno=1, col_offset=4, parent=astroid.Module("mod"))],
            [NodeReference(astroid.Name("glob", lineno=1, col_offset=4), "mod.glob.1.4",
                           NodeScope(astroid.Name("glob", lineno=1, col_offset=4), astroid.Module("mod")), [], False)]
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
    result = [NodeReference(name.name.name, name.node_id, name.scope.scope.__class__.__name__, name.potential_references, name.list_is_complete) for name in result]
    expected = [NodeReference(name.name.name, name.node_id, name.scope.scope.__class__.__name__, name.potential_references, name.list_is_complete) for name in expected]
    assert result == expected


def test_add_potential_value_reference() -> None:
    raise NotImplementedError("Test not implemented")


def test_add_potential_target_reference() -> None:
    raise NotImplementedError("Test not implemented")


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
def test_find_references_local(code, expected):
    module = astroid.parse(code)
    # print(module.repr_tree(), "\n")
    all_names_list = get_name_nodes(module)
    print(all_names_list)
    references = []
    for module_name in all_names_list:
        references.append(find_references(module_name))

    for reference in references:
        print(reference, "\n")
        # print(resolved[0].node_id.module, "\n")
        assert reference == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (
            """
                def function_scope():
                    res = 23
                    return res
            """,
            [
                ['FunctionDef.function_scope'],
                [],
                ['AssignName.res']
            ]
        ),
        (
            """
                var1 = 10
                def function_scope():
                    res = var1
                    return res
            """,
            [
                ['AssignName.var1', 'FunctionDef.function_scope'],
                [],
                ['AssignName.res']
            ]
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
                ['AssignName.var1', 'FunctionDef.function_scope'],
                [],
                ['AssignName.res']
            ]
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
                ['ClassDef.A'],
                ['AssignName.class_attr1', 'FunctionDef.local_class_attr'],
                ['AssignName.var1']
            ]
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
                ['ClassDef.B'],
                ['FunctionDef.__init__', 'FunctionDef.local_instance_attr'],
                ['MemberAccess.instance_attr1', 'AssignName.var1']
            ]
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
                ['ClassDef.B', 'FunctionDef.local_instance_attr'],
                ['FunctionDef.__init__'],
                ['MemberAccess.instance_attr1', 'AssignName.var1']
            ]
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

            """, [
                ['ImportName.collections', 'ImportName.typing', 'ImportName.astroid', 'ClassDef.ASTWalker'],
                ['AssignName.additional_locals', 'FunctionDef.__init__', 'FunctionDef.walk', 'FunctionDef.__walk', 'FunctionDef.__enter', 'FunctionDef.__leave', 'FunctionDef.__get_callbacks'],
                ['MemberAccess.self._handler', 'MemberAccess.self._cache', 'Call.self.__walk', ]
            ]
        )
    ],
    ids=[
        "Function Scope",
        "Function Scope with variable",
        "Function Scope with global variable",
        "Class Scope with class attribute and Class function",
        "Class Scope with instance attribute and Class function",
        "Class Scope with instance attribute and Modul function",
        "ASTWalker",
    ]
)
def test_get_nodes_for_scope(code: str, expected) -> None:
    module = astroid.parse(code)
    # print(module.repr_tree(), "\n")
    all_names_list = get_name_nodes(module)
    references = []
    for name in all_names_list:
        references.append(find_references(name))

    module_scope = []
    class_scope = []
    function_scope = []
    for reference in references:
        for ref in reference:
            print(ref, "\n", ref.scope.scope.__class__.__name__, "\n")
        scope_list = get_nodes_for_scope(reference)
        module_scope.append(scope_list.module_scope)
        class_scope.append(scope_list.class_scope)
        function_scope.append(scope_list.function_scope)

    print("Module: ")
    for reference in module_scope:
        for ref in reference:
            print(ref)
    print("ClassDef: ")
    for reference in class_scope:
        for ref in reference:
            print(ref)
    print("FunctionDef: ")
    for reference in function_scope:
        for ref in reference:
            print(ref)

    # assert module_scope == expected[0]
    # assert class_scope == expected[1]
    # assert function_scope == expected[2]


@dataclass
class SimpleScope(Scopes):
    module_scope: list[str]
    class_scope: list[str]
    function_scope: list[str]


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (
            """
                def function_scope():
                    res = 23
                    return res
            """,
            SimpleScope(
                ['FunctionDef.function_scope'],
                [],
                ['AssignName.res']
            )

        ),
        (
            """
                var1 = 10
                def function_scope():
                    res = var1
                    return res
            """,
            SimpleScope(
                ['AssignName.var1', 'FunctionDef.function_scope'],
                [],
                ['AssignName.res']
            )

        ),
        (
            """
                var1 = 10
                def function_scope():
                    global var1
                    res = var1
                    return res
            """,
            SimpleScope(
                ['AssignName.var1', 'FunctionDef.function_scope'],
                [],
                ['AssignName.res']
            )

        ),
        (
            """
                class A:
                    class_attr1 = 20

                    def local_class_attr():
                        var1 = A.class_attr1
                        return var1
            """,
            SimpleScope(
                ['ClassDef.A'],
                ['AssignName.class_attr1', 'FunctionDef.local_class_attr'],
                ['AssignName.var1']
            )

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
                    ['ClassDef.B'],
                    ['FunctionDef.__init__', 'FunctionDef.local_instance_attr'],
                    ['MemberAccess.self.instance_attr1', 'AssignName.var1']
                ),
            ]
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
                    ['ClassDef.B', 'FunctionDef.local_instance_attr'],
                    ['FunctionDef.__init__'],
                    ['MemberAccess.B().instance_attr1', 'AssignName.var1']
                )
            ]
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

            """, [
                SimpleScope(
                    ['ImportName.collections', 'ImportName.typing', 'ImportName.astroid', 'ClassDef.ASTWalker'],
                    ['AssignName.additional_locals', 'FunctionDef.__init__', 'FunctionDef.walk', 'FunctionDef.__walk', 'FunctionDef.__enter', 'FunctionDef.__leave', 'FunctionDef.__get_callbacks'],
                    ['MemberAccess.self._handler', 'MemberAccess.self._cache', 'Call.self.__walk', ]
                )
            ]  # TODO: complete the expected data
        )
    ],
    ids=[
        "Function Scope",
        "Function Scope with variable",
        "Function Scope with global variable",
        "Class Scope with class attribute and Class function",
        "Class Scope with instance attribute and Class function",
        "Class Scope with instance attribute and Modul function",
        "ASTWalker",
    ]
)
def test_get_scope(code, expected):
    result = get_scope(code)
    print(result)
    assert_test_get_scope(result, expected)


def assert_test_get_scope(result, expected):
    """ The result data as well as the expected data in this test is simplified, so it is easier to compare the results.
    The real results name and scope are objects and not strings"""
    result_transformed = SimpleScope([], [], [])
    for scope in result.module_scope:
        result_transformed.module_scope.append(to_string(scope.node))
    for scope in result.class_scope:
        result_transformed.class_scope.append(to_string(scope.node))
    for scope in result.function_scope:
        result_transformed.function_scope.append(to_string(scope.node))
    assert result_transformed == expected
    # assert result == expected


def to_string(node):
    if isinstance(node, astroid.Call):
        return node.func.as_string()
    return f"{node.__class__.__name__}.{node.name}"

# @pytest.mark.parametrize(
#     ("code", "expected"),
#     [
#         (
#             """
#                 def local_const():
#                     var1 = 20
#                     res = var1
#                     return res
#             """,
#             []
#         ),
#         (
#             """
#                 def local_parameter(a):
#                     var1 = a
#                     res = var1
#                     return res
#             """,
#             []
#         ),        (
#             """
#                 glob1 = 10
#                 def local_global():
#                     global glob1
#
#                     var1 = glob1
#                     res = var1
#                     return res
#             """,
#             []
#         ),        (
#             """
#                 class A:
#                     class_attr1 = 10
#
#                 def local_class_attr():
#                     var1 = A.class_attr1
#                     res = var1
#                     return res
#             """,
#             []
#         ),
#         (
#             """
#                 class B:
#                     def __init__(self):
#                         self.instance_attr1 = 10
#
#                 def local_instance_attr():
#                     var1 = B().instance_attr1
#                     res = var1
#                     return res
#             """,
#             []
#         ),
#     ],
#     ids=[
#         "constant as local variable",
#         "parameter as local variable",
#         "global as local variable",
#         "class attribute as local variable",
#         "instance attribute as local variable",
#     ]
# )
# def test_resolve_references_global(code, expected):
#     module = astroid.parse(code)
#     print(module.repr_tree(), "\n")
#     names_list = get_name_nodes(module)
#     for node in names_list:
#         resolve_references(node)
