import pytest
import astroid

from library_analyzer.processing.api import (
    find_references,
    get_name_nodes, create_references, Reference, calc_node_id
)


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
            ['AssignName.var1', 'Name.A.class_attr']  # TODO: how do we need A.class_attr1?
        ),  # TODO: Problem with instance attributes since: A.class_attr1 is not a Name node
        (
            """

                def instance_attr():
                    b = B()
                    var1 = b.instance_attr
            """,
            ['AssignName.b', 'AssignName.var1', 'Name.b.instance_attr']  # TODO: how do we need B().instance_attr1?
        ),  # TODO: Problem with instance attributes since: B().instance_attr1 is not a Name node
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
            """, ["Name.a.res"]
        ),  # TODO: Problem with instance attributes since: a.res is not a Name node
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
            []
        ),
        (
            """
                def unresolved_reference():
                    var1 = x
            """, ['AssignName.var1']
        ),  # TODO: this should better be checked in the resolve_references test?
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
        "Assign",
        "Assign Parameter",
        "Global unused",
        "Global and Assign",
        "Assign Class Attribute",
        "Assign Instance Attribute",
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
        "Unresolved Reference",
        "ASTWalker"
    ]
)
def test_get_name_nodes(code: str, expected: str) -> None:
    module = astroid.parse(code)
    print(module.repr_tree(), "\n")
    names_list = get_name_nodes(module)
    names_list = names_list[0]
    names_list = transform_actual_names(names_list)
    assert names_list == expected


def transform_actual_names(names):
    return [f"{name.__class__.__name__}.{name.name}" for name in names]


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
def test_calc_function_id_new(node: astroid.NodeNG, expected: str) -> None:
    result = calc_node_id(node)
    assert result.__str__() == expected


@pytest.mark.parametrize(
    ("node", "expected"),
    [
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0))],
            [Reference(astroid.Name("var1", lineno=1, col_offset=4), "func1.var1.1.4", astroid.FunctionDef("func1", lineno=1, col_offset=0), "VALUE", [], False)]
        ),
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
             astroid.Name("var2", lineno=2, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
             astroid.Name("var3", lineno=30, col_offset=4, parent=astroid.FunctionDef("func2", lineno=1, col_offset=0))],
            [Reference(astroid.Name("var1", lineno=1, col_offset=4), "func1.var1.1.4", astroid.FunctionDef("func1", lineno=1, col_offset=0), "VALUE", [], False),
             Reference(astroid.Name("var2", lineno=2, col_offset=4), "func1.var2.2.4", astroid.FunctionDef("func1", lineno=1, col_offset=0), "VALUE", [], False),
                Reference(astroid.Name("var3", lineno=30, col_offset=4), "func2.var3.30.4", astroid.FunctionDef("func2", lineno=1, col_offset=0), "VALUE", [], False)]
        ),
        (
            [astroid.AssignName("var1", lineno=12, col_offset=42, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0))],
            [Reference(astroid.AssignName("var1", lineno=12, col_offset=42), "func1.var1.12.42",astroid.FunctionDef("func1", lineno=1, col_offset=0), "TARGET", [], False)]
        ),
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
             astroid.AssignName("var2", lineno=1, col_offset=8, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0))],
            [Reference(astroid.Name("var1", lineno=1, col_offset=4), "func1.var1.1.4", astroid.FunctionDef("func1", lineno=1, col_offset=0), "VALUE", [], False),
             Reference(astroid.AssignName("var2", lineno=1, col_offset=8), "func1.var2.1.8", astroid.FunctionDef("func1", lineno=1, col_offset=0), "TARGET", [], False)]
        ),
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.ClassDef("MyClass", lineno=1, col_offset=0))],
            [Reference(astroid.Name("var1", lineno=1, col_offset=4), "MyClass.var1.1.4",
                       astroid.ClassDef("MyClass", lineno=1, col_offset=0), "VALUE", [], False)]
        ),
        (
            [astroid.Name("glob", lineno=1, col_offset=4, parent=astroid.Module("mod"))],
            [Reference(astroid.Name("glob", lineno=1, col_offset=4), "mod.glob.1.4",
                       astroid.Module("mod"), "VALUE", [], False)]
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
    result = transform_reference_names(result)
    expected = transform_reference_names(expected)
    assert result == expected
    # the data in this test is simplified, so it is easier to compare the results, in the real results name and scope are objects and not strings

def transform_reference_names(names):
    """Transforms the name of the reference to a string for easier comparison (removes the address of the object)"""
    # print(names)
    return [Reference(name.name.name, name.node_id, name.scope.__class__.__name__, name.usage, name.potential_references, name.list_is_complete) for name in names]


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
        ),        (
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
            []
        ),        (
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
