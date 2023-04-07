import pytest
import astroid

from library_analyzer.processing.api import (
    resolve_references, get_name_nodes
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
                def local_const():
                    var1 = 20
                    res = var1
                    return res
            """,
            ["var1", "res"]
        ),
        (
            """
                def local_parameter(a):
                    var1 = a
                    res = var1
                    return res
            """,
            ["a", "var1", "res"]
        ),        (
            """
                glob1 = 10
                def local_global():
                    global glob1

                    var1 = glob1
                    res = var1
                    return res
            """,
            ["var1", "glob1", "res"]
        ),        (
            """
                class A:
                    class_attr1 = 10

                def local_class_attr():
                    var1 = A.class_attr1
                    res = var1
                    return res
            """,
            ["var1", "res", "A.class_attr1"]  # TODO: how do we need those (A.class_attr1)?
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
            ["var1", "res", "B().instance_attr1"]  # TODO: how do we need those (B().instance_attr1)?
        ),
    ], ids=
    [
        "constant as local variable",
        "parameter as local variable",
        "global as local variable",
        "class attribute as local variable",
        "instance attribute as local variable",
    ]
)
def test_get_name_nodes(code: str, expected: str) -> None:
    names_list_str = []
    module = astroid.parse(code)
    # print(module.repr_tree(), "\n")
    names_list = get_name_nodes(module)
    if not names_list_str:
        for i, name in enumerate(names_list[0]):
            names_list_str.append(name.name)
    if not names_list_str:
        for i, name in enumerate(names_list[1]):
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
    ], ids=
    [
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
