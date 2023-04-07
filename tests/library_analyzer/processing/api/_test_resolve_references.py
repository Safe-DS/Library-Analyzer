import pytest
import astroid

from library_analyzer.processing.api import (
    resolve_references,
    get_name_nodes
)


# # language=Python
# x = """
# def my_func():
#     var1 = 20
#     res = var1
# """
# module = astroid.parse(x)
#
# for node in module.body:
#     resolve_references(node)
# ...


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (
            """
                def variable():
                    var1 = 20
            """,
            ["var1"]
        ),
        (
            """
                def parameter(a):
                    var1 = a
            """,
            ["a", "var1"]
        ),
        (
            """
                def glob():
                    global glob1
            """,
            # TODO: "global glob1" is not a Name node - what should we do, since it is never used?
            #  see next case:
            ["glob1"]
        ),
        (
            """
                def glob():
                    global glob1
                    var1 = glob1
            """,
            ["var1", "glob1"]
        ),
        (
            """
                def class_attr():
                    var1 = A.class_attr
            """,
            ["var1", "A.class_attr"]  # TODO: how do we need A.class_attr1?
        ),  # TODO: Problem with instance attributes since: A.class_attr1 is not a Name node
        (
            """
                def instance_attr():
                    var1 = B().instance_attr
            """,
            ["var1", "b.instance_attr"]  # TODO: how do we need B().instance_attr1?
        ),  # TODO: Problem with instance attributes since: B().instance_attr1 is not a Name node
        (
            """
                def aug_assign():
                    var1 = 10
                    var1 += 1
            """, ["var1"]
        ),
        (
            """
                def assign_attr():
                    a.res = 1
            """, ["a.res"]
        ),  # TODO: Problem with instance attributes since: a.res is not a Name node
        (
            """
                def assign_return():
                    return var1
            """, ["var1"]
        ),
        (
            """
                def while_loop():
                    while var1 > 0:
                        do_something()
            """, ["var1"]
        ),
        (
            """
                def for_loop():
                    for var1 in range(10):
                        do_something()
            """, ["var1"]
        ),
        (
            """
                def if_state():
                    if var1 > 0:
                        do_something()
            """, ["var1"]
        ),
        (
            """
                def if_else_state():
                    if var1 > 0:
                        do_something()
                    else:
                        do_something_else()
            """, ["var1"]
        ),
        (
            """
                def if_elif_state():
                    if var1 > 0:
                        do_something()
                    elif var1 > var2:
                        do_something_else()
            """, ["var1", "var2"]
        ),
        (
            """
                def ann_assign():
                    var1: int = 10
            """, ["var1"]
        ),
    ],
    ids=[
        "Assign",
        "Assign Parameter",
        "Global",
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
        "AnnAssign"
    ]
)
def test_get_name_nodes(code: str, expected: str) -> None:
    names_list_str = []
    module = astroid.parse(code)
    print(module.repr_tree(), "\n")
    names_list = get_name_nodes(module)
    if not names_list_str:
        for i, name in enumerate(names_list[0]):
            names_list_str.append(name.name)
    assert set(names_list_str) == set(expected)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (
            """
                def local_const():
                    var1 = 20
                    res = var1
                    return res
            """,
            []
        ),
        (
            """
                def local_parameter(a):
                    var1 = a
                    res = var1
                    return res
            """,
            []
        ),        (
            """
                glob1 = 10
                def local_global():
                    global glob1

                    var1 = glob1
                    res = var1
                    return res
            """,
            []
        ),        (
            """
                class A:
                    class_attr1 = 10

                def local_class_attr():
                    var1 = A.class_attr1
                    res = var1
                    return res
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
                    res = var1
                    return res
            """,
            []
        ),
    ],
    ids=[
        "constant as local variable",
        "parameter as local variable",
        "global as local variable",
        "class attribute as local variable",
        "instance attribute as local variable",
    ]
)
def test_resolve_references_local(code, expected):
    module = astroid.parse(code)
    print(module.repr_tree(), "\n")
    names_list = get_name_nodes(module)
    for node in names_list:
        resolve_references(node)
