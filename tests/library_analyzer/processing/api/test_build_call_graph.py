from __future__ import annotations

import pytest

from library_analyzer.processing.api.purity_analysis import get_module_data, build_call_graph


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "functon call - in declaration order"
            """
def fun1():
    pass

def fun2():
    fun1()

fun2()
            """,  # language=none
            {
                "fun1": set(),
                "fun2": {"fun1"},
            },
        ),
        (  # language=Python "functon call - against declaration order"
            """
def fun1():
    fun2()

def fun2():
    pass

fun1()
            """,  # language=none
            {
                "fun1": {"fun2"},
                "fun2": set(),
            },
        ),

        (  # language=Python "functon call - against declaration order with multiple calls"
            """
def fun1():
    fun2()

def fun2():
    fun3()

def fun3():
    pass

fun1()
            """,  # language=none
            {
                "fun1": {"fun2"},
                "fun2": {"fun3"},
                "fun3": set(),
            },
        ),
        (  # language=Python "functon conditional with branching"
            """
def fun1():
    return "Function 1"

def fun2():
    return "Function 2"

def call_function(a):
    if a == 1:
        return fun1()
    else:
        return fun2()

call_function(1)
            """,  # language=none
            {
                "fun1": set(),
                "fun2": set(),
                "call_function": {"fun1", "fun2"},
            },
        ),
    ],
    ids=[
        "function call - in declaration order",
        "function call - against declaration flow",
        "function call - against declaration flow with multiple calls",
        "functon conditional with branching"
    ],
)
def test_build_call_graph(code: str, expected: dict[str, set]) -> None:
    module_data = get_module_data(code)
    call_graph_forest = build_call_graph(module_data.functions)

    transformed_call_graph_forest: dict = {}
    for tree_name, tree in call_graph_forest.trees.items():
        transformed_call_graph_forest[tree_name] = set()
        for child in tree.children:
            transformed_call_graph_forest[tree_name].add(child.data.symbol.name)

    assert transformed_call_graph_forest == expected

