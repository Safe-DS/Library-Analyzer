from __future__ import annotations

import pytest

from library_analyzer.processing.api.purity_analysis import get_module_data, build_call_graph


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "function call - in declaration order"
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
        (  # language=Python "function call - against declaration order"
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
        (  # language=Python "function call - against declaration order with multiple calls"
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
        (  # language=Python "function conditional with branching"
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
        (  # language=Python "function call with cycle - one entry point"
            """
def cycle1():
    cycle2()

def cycle2():
    cycle3()

def cycle3():
    cycle1()

def entry():
    cycle1()

entry()
            """,  # language=none
            {
                "cycle1": {"cycle2"},
                "cycle2": {"cycle3"},
                "cycle3": {"cycle1"},
                "entry": {"cycle1"},
            },
        ),

        (  # language=Python "function call with cycle - many entry points"
            """
def cycle1():
    cycle2()

def cycle2():
    cycle3()

def cycle3():
    cycle1()

def entry1():
    cycle1()

def entry2():
    cycle2()

def entry3():
    cycle3()

entry1()
            """,  # language=none
            {
                "cycle1": {"cycle2"},
                "cycle2": {"cycle3"},
                "cycle3": {"cycle1"},
                "entry1": {"cycle1"},
                "entry2": {"cycle2"},
                "entry3": {"cycle3"},
            },
        ),
        (  # language=Python "function call with cycle - other call in cycle"
            """
def cycle1():
    cycle2()

def cycle2():
    cycle3()
    other()

def cycle3():
    cycle1()

def entry():
    cycle1()

def other():
    pass

entry()
            """,  # language=none
            {
                "cycle1": {"cycle2"},
                "cycle2": {"cycle3", "other"},
                "cycle3": {"cycle1"},
                "entry": {"cycle1"},
                "other": set(),
            },
        ),
        (  # language=Python "function call with cycle - other call in cycle"
            """
def cycle1():
    cycle2()

def cycle2():
    cycle3()

def cycle3():
    inner_cycle1()
    cycle1()

def inner_cycle1():
    inner_cycle2()

def inner_cycle2():
    inner_cycle1()

def entry():
    cycle1()

entry()
            """,  # language=none
            {
                "cycle1": {"cycle2"},
                "cycle2": {"cycle3"},
                "cycle3": {"inner_cycle1", "cycle1"},
                "inner_cycle1": {"inner_cycle2"},
                "inner_cycle2": {"inner_cycle1"},
                "entry": {"cycle1"},
            },
        ),
        (  # language=Python "recursive function call",
            """
def f(a):
    print(a)
    if a > 0:
        f(a - 1)

x = 10
f(x)
            """,  # language=none
            {
                "f": {"f"},
            },
        ),
    ],
    ids=[
        "function call - in declaration order",
        "function call - against declaration flow",
        "function call - against declaration flow with multiple calls",
        "function conditional with branching",
        "function call with cycle - one entry point",
        "function call with cycle - many entry points",
        "function call with cycle - other call in cycle",
        "function call with cycle - cycle within a cycle",
        "recursive function call",
    ],
)
def test_build_call_graph(code: str, expected: dict[str, set]) -> None:
    module_data = get_module_data(code)
    call_graph_forest = build_call_graph(module_data.functions)

    transformed_call_graph_forest: dict = {}
    for tree_name, tree in call_graph_forest.graphs.items():
        transformed_call_graph_forest[tree_name] = set()
        for child in tree.children:
            transformed_call_graph_forest[tree_name].add(child.data.symbol.name)

    assert transformed_call_graph_forest == expected

