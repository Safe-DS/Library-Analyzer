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
        (  # language=Python "function call with cycle - direct entry"
            """
def fun1(count):
    if count > 0:
        fun2(count - 1)

def fun2(count):
    if count > 0:
        fun1(count - 1)

fun1(3)
            """,  # language=none
            {
                "fun1+fun2": set(),
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
                "cycle1+cycle2+cycle3": set(),
                "entry": {"cycle1+cycle2+cycle3"},
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
                "cycle1+cycle2+cycle3": set(),
                "entry1": {"cycle1+cycle2+cycle3"},
                "entry2": {"cycle1+cycle2+cycle3"},
                "entry3": {"cycle1+cycle2+cycle3"},
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
                "cycle1+cycle2+cycle3": {"other"},
                "entry": {"cycle1+cycle2+cycle3"},
                "other": set(),
            },
        ),
        (  # language=Python "function call with cycle - multiple other calls in cycle"
            """
def cycle1():
    cycle2()
    other3()

def cycle2():
    cycle3()
    other1()

def cycle3():
    cycle1()

def entry():
    cycle1()
    other2()

def other1():
    pass

def other2():
    pass

def other3():
    pass

entry()
            """,  # language=none
            {
                "cycle1+cycle2+cycle3": {"other1", "other3"},
                "entry": {"cycle1+cycle2+cycle3", "other2"},
                "other1": set(),
                "other2": set(),
                "other3": set(),
            },
        ),
        # TODO: this case is disabled for merging to main [ENABLE AFTER MERGE]
#         (  # language=Python "function call with cycle - cycle within a cycle"
#             """
# def cycle1():
#     cycle2()
#
# def cycle2():
#     cycle3()
#
# def cycle3():
#     inner_cycle1()
#     cycle1()
#
# def inner_cycle1():
#     inner_cycle2()
#
# def inner_cycle2():
#     inner_cycle1()
#
# def entry():
#     cycle1()
#
# entry()
#             """,  # language=none
#             {
#                 "cycle1+cycle2+cycle3": {"inner_cycle1+inner_cycle2"},
#                 "inner_cycle1+inner_cycle2": set(),
#                 "entry": {"cycle1+cycle2+cycle3"},
#             },
#         ),
        (  # language=Python "recursive function call",
            """
def f(a):
    if a > 0:
        f(a - 1)

x = 10
f(x)
            """,  # language=none
            {
                "f": set(),
            },
        ),
        (  # language=Python "recursive function call",
            """
def fun1():
    fun2()

def fun2():
    print("Function 2")

fun1()
            """,  # language=none
            {
                "fun1": {"fun2"},
                "fun2": {"print"},
            },
        ),
        (  # language=Python "external function call",
            """
def fun1():
    call()
            """,  # language=none
            {
                "fun1": set(),
            },
        ),
        (  # language=Python "recursive function call",
            """
def fun1():
    pass

def fun2():
    print("Function 2")

class A:
    @staticmethod
    def add(a, b):
        fun1()
        return a + b

class B:
    @staticmethod
    def add(a, b):
        fun2()
        return a + 2 * b

x = A()
x.add(1, 2)
            """,  # language=none
            {
                "fun1": set(),
                "fun2": {"print"},
                "add": {"fun1", "fun2"},
            },
        ),
    ],
    ids=[
        "function call - in declaration order",
        "function call - against declaration flow",
        "function call - against declaration flow with multiple calls",
        "function conditional with branching",
        "function call with cycle - direct entry",
        "function call with cycle - one entry point",
        "function call with cycle - many entry points",
        "function call with cycle - other call in cycle",
        "function call with cycle - multiple other calls in cycle",
        # "function call with cycle - cycle within a cycle",
        "recursive function call",
        "builtin function call",
        "external function call",
        "function call of function with same name",
    ],  # TODO: LARS how do we build a call graph for a.b.c.d()?
)
def test_build_call_graph(code: str, expected: dict[str, set]) -> None:
    module_data = get_module_data(code)
    call_graph_forest = build_call_graph(module_data.functions, module_data.function_references)

    transformed_call_graph_forest: dict = {}
    for tree_name, tree in call_graph_forest.graphs.items():
        transformed_call_graph_forest[tree_name] = set()
        for child in tree.children:
            transformed_call_graph_forest[tree_name].add(child.data.symbol.name)

    assert transformed_call_graph_forest == expected
