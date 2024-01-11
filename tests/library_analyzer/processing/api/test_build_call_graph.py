from __future__ import annotations

import pytest
from library_analyzer.processing.api.purity_analysis import build_call_graph, get_module_data


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "function call - in declaration order"
            """
def fun1():
    pass

def fun2():
    fun1()
            """,  # language=none
            {
                ".fun1.2.0": set(),
                ".fun2.5.0": {".fun1.2.0"},
            },
        ),
        (  # language=Python "function call - against declaration order"
            """
def fun1():
    fun2()

def fun2():
    pass
            """,  # language=none
            {
                ".fun1.2.0": {".fun2.5.0"},
                ".fun2.5.0": set(),
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
            """,  # language=none
            {
                ".fun1.2.0": {".fun2.5.0"},
                ".fun2.5.0": {".fun3.8.0"},
                ".fun3.8.0": set(),
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
            """,  # language=none
            {
                ".fun1.2.0": set(),
                ".fun2.5.0": set(),
                ".call_function.8.0": {".fun1.2.0", ".fun2.5.0"},
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
            """,  # language=none
            {
                ".fun1.2.0+.fun2.6.0": set(),
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
            """,  # language=none
            {
                ".cycle1.2.0+.cycle2.5.0+.cycle3.8.0": set(),
                ".entry.11.0": {".cycle1.2.0+.cycle2.5.0+.cycle3.8.0"},
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
            """,  # language=none
            {
                ".cycle1.2.0+.cycle2.5.0+.cycle3.8.0": set(),
                ".entry1.11.0": {".cycle1.2.0+.cycle2.5.0+.cycle3.8.0"},
                ".entry2.14.0": {".cycle1.2.0+.cycle2.5.0+.cycle3.8.0"},
                ".entry3.17.0": {".cycle1.2.0+.cycle2.5.0+.cycle3.8.0"},
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
            """,  # language=none
            {
                ".cycle1.2.0+.cycle2.5.0+.cycle3.9.0": {".other.15.0"},
                ".entry.12.0": {".cycle1.2.0+.cycle2.5.0+.cycle3.9.0"},
                ".other.15.0": set(),
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
            """,  # language=none
            {
                ".cycle1.2.0+.cycle2.6.0+.cycle3.10.0": {".other1.17.0", ".other3.23.0"},
                ".entry.13.0": {".cycle1.2.0+.cycle2.6.0+.cycle3.10.0", ".other2.20.0"},
                ".other1.17.0": set(),
                ".other2.20.0": set(),
                ".other3.23.0": set(),
            },
        ),
        # TODO: add a case with a cycle and a node inside the cycle has multiple more than one funcdef with the same name
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
            """,  # language=none
            {
                ".f.2.0": set(),
            },
        ),
        (  # language=Python "builtin function call",
            """
def fun1():
    fun2()

def fun2():
    print("Function 2")
            """,  # language=none
            {
                ".fun1.2.0": {".fun2.5.0"},
                ".fun2.5.0": {".print.6.4"},  # print is a builtin function and therefore has no function def to reference -> we use the id of the call node for simplicity
            },
        ),
        (  # language=Python "external function call",
            """
def fun1():
    call()
            """,  # language=none
            {
                ".fun1.2.0": set(),
            },
        ),
        (  # language=Python "lambda call",
            """
double = lambda x: 2 * x
            """,  # language=none
            {
                ".double.2.9": set(),
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
        "lambda call",
    ],
)
def test_build_call_graph(code: str, expected: dict[str, set]) -> None:
    module_data = get_module_data(code)
    call_graph_forest = build_call_graph(module_data.functions, module_data.classes, module_data.function_references)

    transformed_call_graph_forest: dict = {}
    for tree_id, tree in call_graph_forest.graphs.items():
        transformed_call_graph_forest[f"{tree_id}"] = set()
        for child in tree.children:
            transformed_call_graph_forest[f"{tree_id}"].add(child.data.symbol.id.__str__())

    assert transformed_call_graph_forest == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "class call - init",
            """
class A:
    pass

def fun():
    a = A()

            """,  # language=none
            {
                ".A.2.0": set(),
                ".fun.5.0": {".A.2.0"},
            },
        ),
        (  # language=Python "member access - class",
            """
class A:
    class_attr1 = 20

def fun():
    a = A().class_attr1

            """,  # language=none
            {
                ".A.2.0": set(),
                ".fun.5.0": {".A.2.0"},
            },
        ),
        (  # language=Python "member access - class without init",
            """
class A:
    class_attr1 = 20

def fun():
    a = A.class_attr1

            """,  # language=none
            {
                ".A.2.0": set(),
                ".fun.5.0": {".A.2.0"},  # TODO: LARS do we want this?
            },
        ),
        (  # language=Python "member access - methode",
            """
class A:
    class_attr1 = 20

    def g(self):
        pass

def fun1():
    a = A()
    a.g()

def fun2():
    a = A().g()

            """,  # language=none
            {
                ".A.2.0": set(),
                ".g.5.4": set(),
                ".fun1.8.0": {".A.2.0", ".g.5.4"},
                ".fun2.12.0": {".A.2.0", ".g.5.4"},
            },
        ),
        (  # language=Python "member access - init",
            """
class A:
    def __init__(self):
        pass

def fun():
    a = A()

            """,  # language=none
            {
                ".A.2.0": {".__init__.3.4"},
                ".__init__.3.4": set(),
                ".fun.6.0": {".A.2.0"},
            },
        ),
        (  # language=Python "member access - instance function",
            """
class A:
    def __init__(self):
        self.a_inst = B()

class B:
    def __init__(self):
        pass

    def b_fun(self):
        pass

def fun1():
    a = A()
    a.a_inst.b_fun()

def fun2():
    a = A().a_inst.b_fun()

            """,  # language=none
            {
                ".A.2.0": {".__init__.3.4"},
                ".__init__.3.4": {".B.6.0"},
                ".B.6.0": {".__init__.7.4"},
                ".__init__.7.4": set(),
                ".b_fun.10.4": set(),
                ".fun1.13.0": {".A.2.0", ".b_fun.10.4"},
                ".fun2.17.0": {".A.2.0", ".b_fun.10.4"},
            },
        ),
        (  # language=Python "member access - function call of functions with same name"
            """
class A:
    @staticmethod
    def add(a, b):
        return a + b

class B:
    @staticmethod
    def add(a, b):
        return a + 2 * b

def fun_a():
    x = A()
    x.add(1, 2)

def fun_b():
    x = B()
    x.add(1, 2)
            """,  # language=none
            {
                ".A.2.0": set(),
                ".B.7.0": set(),
                ".add.4.4": set(),
                ".add.9.4": set(),
                ".fun_a.12.0": {".A.2.0", ".add.4.4"},  # TODO: is it possible to distinguish between the two add functions?
                ".fun_b.17.0": {".B.7.0", ".add.9.4"},
            },
        ),
        (  # language=Python "member access - function call of functions with same name and nested calls",
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
            """,  # language=none
            {
                ".A.8.0": set(),
                ".B.14.0": set(),
                ".fun1.2.0": set(),
                ".fun2.5.0": {".print.6.4"},  # print is a builtin function and therefore has no function def to reference -> we use the id of the call node for simplicity
                ".add.10.4": {".fun1.2.0"},
                ".add.16.4": {".fun2.5.0"},
            },
        ),
        (  # language=Python "member access - function call of functions with same name (no distinction possible)"
            """
class A:
    @staticmethod
    def fun():
        return "Function A"

class B:
    @staticmethod
    def fun():
        return "Function B"

def fun_out(a):
    if a == 1:
        x = A()
    else:
        x = B()
    x.fun()
            """,  # language=none
            {
                ".A.2.0": set(),
                ".B.7.0": set(),
                ".fun.4.4": set(),
                ".fun.9.4": set(),
                ".fun_out.12.0": {".A.2.0", ".B.7.0", ".fun.4.4", ".fun.9.4"},   # here we cannot distinguish between the two fun functions
            },
        ),
        (  # language=Python "member access - function call of functions with same name (different signatures)"
            """
class A:
    @staticmethod
    def add(a, b):
        return a + b

class B:
    @staticmethod
    def add(a, b, c):
        return a + b + c

def fun():
    A.add(1, 2)
    B.add(1, 2, 3)
            """,  # language=none
            {
                ".A.2.0": set(),
                ".B.7.0": set(),
                ".add.4.4": set(),
                ".add.9.4": set(),
                ".fun.12.0": {".A.2.0", ".B.7.0", ".add.4.4", ".add.9.4"},   # TODO: here we maybe can distinguish between the two add functions because of their signature
            },
        ),
        (  # language=Python "member access - function call of functions with same name (but different instance variables)"
            """
class A:
    @staticmethod
    def add(a, b):
        return a + b

class B:
    def __init__(self):
        self.value = C()

class C:
    @staticmethod
    def add(a, b):
        return a + b

def fun_a():
    x = A()
    x.add(1, 2)

def fun_b():
    x = B()
    x.value.add(1, 2)
            """,  # language=none
            {
                ".A.2.0": set(),
                ".add.4.4": set(),
                ".B.7.0": {".__init__.8.4"},
                ".__init__.8.4": {".C.11.0"},
                ".C.11.0": set(),
                ".add.13.4": set(),
                ".fun_a.16.0": {".A.2.0", ".add.4.4"},
                ".fun_b.20.0": {".B.7.0", ".add.13.4"},   # TODO: here we maybe can distinguish between the two add functions because of their instance variables
            },  # TODO: it should be easy to add filters later: check if a target exists inside a class before adding its impurity reasons to the impurity result
        ),
    ],
    ids=[
        "class call - init",
        "member access - class",
        "member access - class without init",
        "member access - methode",
        "member access - init",
        "member access - instance function",
        "member access - function call of functions with same name",
        "member access - function call of functions with same name and nested calls",
        "member access - function call of functions with same name (no distinction possible)",
        "member access - function call of functions with same name (different signatures)",
        "member access - function call of functions with same name (but different instance variables)",
    ],  # TODO: add cyclic cases
)
def test_build_call_graph_member_access(code: str, expected: dict[str, set]) -> None:
    module_data = get_module_data(code)
    call_graph_forest = build_call_graph(module_data.functions, module_data.classes, module_data.function_references)

    transformed_call_graph_forest: dict = {}
    for tree_id, tree in call_graph_forest.graphs.items():
        transformed_call_graph_forest[f"{tree_id}"] = set()
        for child in tree.children:
            transformed_call_graph_forest[f"{tree_id}"].add(child.data.symbol.id.__str__())

    assert transformed_call_graph_forest == expected
