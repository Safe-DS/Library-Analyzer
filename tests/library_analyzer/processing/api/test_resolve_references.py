from __future__ import annotations

from dataclasses import dataclass

import astroid
import pytest
from library_analyzer.processing.api import (
    _find_name_references,
    get_base_expression,
    resolve_references,
)
from library_analyzer.processing.api.model import (
    ReferenceNode,
    MemberAccess,
    MemberAccessTarget,
    MemberAccessValue,
    Scope,
    NodeID,
)


@pytest.mark.parametrize(
    ("node", "expected"),
    [
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0))],
            [ReferenceNode(astroid.Name("var1", lineno=1, col_offset=4),
                           Scope(astroid.Name("var1", lineno=1, col_offset=4), NodeID(astroid.Module(""), "var1", 1, 4),
                                 []))]
        ),
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
             astroid.Name("var2", lineno=2, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
             astroid.Name("var3", lineno=30, col_offset=4,
                          parent=astroid.FunctionDef("func2", lineno=1, col_offset=0))],
            [ReferenceNode(astroid.Name("var1", lineno=1, col_offset=4),
                           Scope(astroid.Name("var1", lineno=1, col_offset=4), NodeID(astroid.Module(""), "var1", 1, 4),
                                 [])),
             ReferenceNode(astroid.Name("var2", lineno=2, col_offset=4),
                           Scope(astroid.Name("var2", lineno=2, col_offset=4), NodeID(astroid.Module(""), "var2", 2, 4),
                                 [])),
             ReferenceNode(astroid.Name("var3", lineno=30, col_offset=4),
                           Scope(astroid.Name("var3", lineno=30, col_offset=4),
                                 NodeID(astroid.Module(""), "var3", 30, 4), []))]
        ),
        (
            [astroid.AssignName("var1", lineno=12, col_offset=42,
                                parent=astroid.FunctionDef("func1", lineno=1, col_offset=0))],
            [ReferenceNode(astroid.AssignName("var1", lineno=12, col_offset=42),
                           Scope(astroid.AssignName("var1", lineno=12, col_offset=42),
                                 NodeID(astroid.Module(""), "var1", 12, 42), []))]
        ),
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
             astroid.AssignName("var2", lineno=1, col_offset=8,
                                parent=astroid.FunctionDef("func1", lineno=1, col_offset=0))],
            [ReferenceNode(astroid.Name("var1", lineno=1, col_offset=4),
                           Scope(astroid.Name("var1", lineno=1, col_offset=4), NodeID(astroid.Module(""), "var1", 1, 4),
                                 [])),
             ReferenceNode(astroid.AssignName("var2", lineno=1, col_offset=8),
                           Scope(astroid.AssignName("var2", lineno=1, col_offset=8),
                                 NodeID(astroid.Module(""), "var2", 1, 8), []))]
        ),
        (
            [astroid.Name("var1", lineno=1, col_offset=4, parent=astroid.ClassDef("MyClass", lineno=1, col_offset=0))],
            [ReferenceNode(astroid.Name("var1", lineno=1, col_offset=4),
                           Scope(astroid.Name("var1", lineno=1, col_offset=4), NodeID(astroid.Module(""), "var1", 1, 4),
                                 []))]
        ),
        (
            [astroid.Name("glob", lineno=1, col_offset=4, parent=astroid.Module("mod"))],
            [ReferenceNode(astroid.Name("glob", lineno=1, col_offset=4),
                           Scope(astroid.Name("glob", lineno=1, col_offset=4),
                                 NodeID(astroid.Module("mod"), "glob", 1, 4), []))]
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
@pytest.mark.xfail(reason="Not implemented yet")
def test_create_references(node: list[astroid.Name | astroid.AssignName], expected: list[ReferenceNode]) -> None:
    result = _find_name_references(node)[0]
    assert result == expected
    assert_reference_list_equal(result, expected)


# TODO: rewrite this test since the results are no longer just prototypes


def assert_reference_list_equal(result: list[ReferenceNode], expected: list[ReferenceNode]) -> None:
    """ Assert reference list equality.

    The result data as well as the expected data in this test is simplified, so it is easier to compare the results.
    The real results name and scope are objects and not strings"""
    result = [
        ReferenceNode(name.node.name, name.scope.children.__class__.__name__, name.referenced_symbols) for name in
        result]
    expected = [
        ReferenceNode(name.node.name, name.scope.children.__class__.__name__, name.referenced_symbols) for name in
        expected]
    assert result == expected


# TODO: test this when resolve reference is implemented (disabled for now due to test failures)
# def test_add_target_references() -> None:
#     raise NotImplementedError("Test not implemented")


@dataclass
class ReferenceTestNode:
    name: str
    scope: str
    referenced_symbols: list[str]

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.name}.{self.scope}"


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "parameter in function scope"
            """
def local_parameter(pos_arg):
    return 2 * pos_arg
            """,  # language= None
            [ReferenceTestNode("pos_arg.line3", "FunctionDef.local_parameter", ["Parameter.pos_arg.line2"])]
        ),
        (  # language=Python "parameter in function scope with keyword only"
            """
def local_parameter(*, key_arg_only):
    return 2 * key_arg_only
            """,  # language= None
            [ReferenceTestNode("key_arg_only.line3", "FunctionDef.local_parameter", ["Parameter.key_arg_only.line2"])]
        ),
        (  # language=Python "parameter in function scope with positional only"
        """
def local_parameter(pos_arg_only, /):
    return 2 * pos_arg_only
            """,  # language= None
        [ReferenceTestNode("pos_arg_only.line3", "FunctionDef.local_parameter", ["Parameter.pos_arg_only.line2"])]
    ),
        (  # language=Python "parameter in function scope with default value"
            """
def local_parameter(def_arg=10):
    return def_arg
            """,  # language= None
            [ReferenceTestNode("def_arg.line3", "FunctionDef.local_parameter", ["Parameter.def_arg.line2"])]
        ),
        (  # language=Python "parameter in function scope with type annotation"
            """
def local_parameter(def_arg: int):
    return def_arg
            """,  # language= None
            [ReferenceTestNode("def_arg.line3", "FunctionDef.local_parameter", ["Parameter.def_arg.line2"])]
        ),
        (  # language=Python "parameter in function scope with *args"
            """
def local_parameter(*args):
    return args
            """,  # language= None
            [ReferenceTestNode("args.line3", "FunctionDef.local_parameter", ["Parameter.args.line2"])]
        ),
        (  # language=Python "parameter in function scope with **kwargs"
            """
def local_parameter(**kwargs):
    return kwargs
            """,  # language= None
            [ReferenceTestNode("kwargs.line3", "FunctionDef.local_parameter", ["Parameter.kwargs.line2"])]
        ),
        (  # language=Python "parameter in function scope with *args and **kwargs"
            """
def local_parameter(*args, **kwargs):
    return args, kwargs
            """,  # language= None
            [ReferenceTestNode("args.line3", "FunctionDef.local_parameter", ["Parameter.args.line2"]),
             ReferenceTestNode("kwargs.line3", "FunctionDef.local_parameter", ["Parameter.kwargs.line2"])]
        ),
        (  # language=Python "two parameters in function scope"
            """
def local_double_parameter(a, b):
    return a, b
            """,  # language= None
            [ReferenceTestNode("a.line3", "FunctionDef.local_double_parameter", ["Parameter.a.line2"]),
             ReferenceTestNode("b.line3", "FunctionDef.local_double_parameter", ["Parameter.b.line2"])]
        )
    ],
    ids=[
        "parameter in function scope",
        "parameter in function scope with keyword only",
        "parameter in function scope with positional only",
        "parameter in function scope with default value",
        "parameter in function scope with type annotation",
        "parameter in function scope with *args",
        "parameter in function scope with **kwargs",
        "parameter in function scope with *args and **kwargs",
        "two parameters in function scope"
    ]
)
def test_resolve_references_parameters(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code)
    transformed_references: list[ReferenceTestNode] = []

    for node in references:
        transformed_references.append(transform_reference_node(node))

    # assert references == expected
    assert set(transformed_references) == set(expected)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "local variable in function scope"
            """
def local_var():
    var1 = 1
    return var1
            """,  # language= None
            [ReferenceTestNode("var1.line4", "FunctionDef.local_var", ["LocalVariable.var1.line3"])]
        ),
        (  # language=Python "global variable in module scope"
            """
glob1 = 10
glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line3", "Module.", ["GlobalVariable.glob1.line2"])]
        ),
        (  # language=Python "global variable in class scope"
            """
glob1 = 10
class A:
    global glob1
    glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line5", "ClassDef.A", ["GlobalVariable.glob1.line2"])]
        ),
        (  # language=Python "global variable in function scope"
            """
glob1 = 10
def local_global():
    global glob1

    return glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line6", "FunctionDef.local_global", ["GlobalVariable.glob1.line2"])]
        ),
        (  # language=Python "global variable in function scope but after definition"
            """
def local_global():
    global glob1

    return glob1

glob1 = 10
            """,  # language= None
            [ReferenceTestNode("glob1.line5", "FunctionDef.local_global", ["GlobalVariable.glob1.line7"])]
        ),
        (  # language=Python "global variable in class scope and function scope"
            """
glob1 = 10
class A:
    global glob1
    glob1

def local_global():
    global glob1

    return glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line5", "ClassDef.A", ["GlobalVariable.glob1.line2"]),
             ReferenceTestNode("glob1.line10", "FunctionDef.local_global", ["GlobalVariable.glob1.line2"])]
        ),
        (  # language=Python "access of global variable without global keyword"
            """
glob1 = 10
def local_global_access():
    return glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line4", "FunctionDef.local_global_access", ["GlobalVariable.glob1.line2"])]
        ),
        (  # language=Python "local variable in function scope shadowing global variable without global keyword"
            """
glob1 = 10
def local_global_shadow():
    glob1 = 20

    return glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line6", "FunctionDef.local_global_shadow",
                               ["GlobalVariable.glob1.line2", "LocalVariable.glob1.line4"])]
        ),
        (  # language=Python "two globals in class scope"
            """
glob1 = 10
glob2 = 20
class A:
    global glob1, glob2
    glob1, glob2
            """,  # language= None
            [ReferenceTestNode("glob1.line6", "ClassDef.A", ["GlobalVariable.glob1.line2"]),
             ReferenceTestNode("glob2.line6", "ClassDef.A", ["GlobalVariable.glob2.line3"])]
        ),
        (  # language=Python new global variable in class scope
            """
class A:
    global glob1
    glob1 = 10
    glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line5", "ClassDef.A", ["ClassVariable.A.glob1.line4"])]
            # glob1 is not detected as a global variable since it is defined in the class scope - this is intended
        ),
        (  # language=Python new global variable in function scope
            """
def local_global():
    global glob1

    return glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line5", "FunctionDef.local_global", [])]
            # glob1 is not detected as a global variable since it is defined in the function scope - this is intended
        ),
        (  # language=Python new global variable in class scope with outer scope usage
            """
class A:
    global glob1
    value = glob1

a = A().value
glob1 = 10
b = A().value
a, b
            """,  # language= None
            [ReferenceTestNode("A.line6", "Module.", ["GlobalVariable.A.line2"]),
             ReferenceTestNode("A.line8", "Module.", ["GlobalVariable.A.line2"]),
             ReferenceTestNode("glob1.line4", "ClassDef.A", ["GlobalVariable.glob1.line7"]),
             ReferenceTestNode("A.value.line6", "Module.", ["ClassVariable.A.value.line4"]),
             ReferenceTestNode("A.value.line8", "Module.", ["ClassVariable.A.value.line4"]),
             ReferenceTestNode("a.line9", "Module.", ["GlobalVariable.a.line6"]),
             ReferenceTestNode("b.line9", "Module.", ["GlobalVariable.b.line8"])]
        ),
        (  # language=Python new global variable in function scope with outer scope usage
            """
def local_global():
    global glob1
    return glob1

lg = local_global()
glob1 = 10
            """,  # language= None
            [ReferenceTestNode("local_global.line6", "Module.", ["GlobalVariable.local_global.line2"]),
             ReferenceTestNode("glob1.line4", "FunctionDef.local_global", ["GlobalVariable.glob1.line7"])]
        )  # Problem: we can not check weather a function is called before the global variable is declared since
        # this would need a context-sensitive approach
        # For now we just check if the global variable is declared in the module scope at the cost of loosing precision.
    ],
    ids=[
        "local variable in function scope",
        "global variable in module scope",
        "global variable in class scope",
        "global variable in function scope",
        "global variable in function scope but after definition",
        "global variable in class scope and function scope",
        "access of global variable without global keyword",
        "local variable in function scope shadowing global variable without global keyword",
        "two globals in class scope",
        "new global variable in class scope",
        "new global variable in function scope",
        "new global variable in class scope with outer scope usage",
        "new global variable in function scope with outer scope usage",
    ]
)
def test_resolve_references_local_global(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code)
    transformed_references: list[ReferenceTestNode] = []

    for node in references:
        transformed_references.append(transform_reference_node(node))

    # assert references == expected
    assert set(transformed_references) == set(expected)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "class attribute value"
            """
class A:
    class_attr1 = 20

A.class_attr1
A
            """,  # language=none
            [ReferenceTestNode("A.class_attr1.line5", "Module.", ["ClassVariable.A.class_attr1.line3"]),
             ReferenceTestNode("A.line5", "Module.", ["GlobalVariable.A.line2"]),
             ReferenceTestNode("A.line6", "Module.", ["GlobalVariable.A.line2"])],
        ),
        (  # language=Python "class attribute target"
            """
class A:
    class_attr1 = 20

A.class_attr1 = 30
A.class_attr1
            """,  # language=none
            [ReferenceTestNode("A.class_attr1.line6", "Module.", ["ClassVariable.A.class_attr1.line3",
                                                                  "ClassVariable.A.class_attr1.line5"]),
             ReferenceTestNode("A.line6", "Module.", ["GlobalVariable.A.line2"])],
        ),
        (  # language=Python "class attribute multiple usage"
            """
class A:
    class_attr1 = 20

a = A().class_attr1
b = A().class_attr1
c = A().class_attr1
            """,  # language=none
            [ReferenceTestNode("A.class_attr1.line5", "Module.", ["ClassVariable.A.class_attr1.line3"]),
             ReferenceTestNode("A.class_attr1.line6", "Module.", ["ClassVariable.A.class_attr1.line3"]),
             ReferenceTestNode("A.class_attr1.line7", "Module.", ["ClassVariable.A.class_attr1.line3"]),
             ReferenceTestNode("A.line5", "Module.", ["GlobalVariable.A.line2"]),
             ReferenceTestNode("A.line6", "Module.", ["GlobalVariable.A.line2"]),
             ReferenceTestNode("A.line7", "Module.", ["GlobalVariable.A.line2"]),
             ]
        ),
        (  # language=Python "chained class attribute"
            """
class A:
    class_attr1 = 20

class B:
    upper_class: A = A

b = B()
x = b.upper_class.class_attr1
            """,  # language=none
            [ReferenceTestNode("b.upper_class.class_attr1.line9", "Module.", ["ClassVariable.A.class_attr1.line3"]),
             ReferenceTestNode("b.upper_class.line9", "Module.", ["ClassVariable.B.upper_class.line6"]),
             ReferenceTestNode("b.line9", "Module.", ["GlobalVariable.b.line8"]),
             ReferenceTestNode("B.line8", "Module.", ["GlobalVariable.B.line5"]),
             ]
        ),
        (  # language=Python "instance attribute value"
            """
class B:
    def __init__(self):
        self.instance_attr1 : int = 10

b = B()
var1 = b.instance_attr1
            """,  # language=none
            [ReferenceTestNode("b.instance_attr1.line7", "Module.", ["InstanceVariable.B.instance_attr1.line4"]),
             ReferenceTestNode("b.line7", "Module.", ["GlobalVariable.b.line6"]),
             ReferenceTestNode("B.line6", "Module.", ["GlobalVariable.B.line2"])]
        ),
        (  # language=Python "instance attribute target"
            """
class B:
    def __init__(self):
        self.instance_attr1 = 10

b = B()
b.instance_attr1 = 1
b.instance_attr1
            """,  # language=none
            [ReferenceTestNode("b.instance_attr1.line8", "Module.", ["InstanceVariable.B.instance_attr1.line4",
                                                                     "InstanceVariable.B.instance_attr1.line7"]),
             ReferenceTestNode("b.line8", "Module.", ["GlobalVariable.b.line6"]),
             ReferenceTestNode("B.line6", "Module.", ["GlobalVariable.B.line2"])
             ]
        ),
        (  # language=Python "instance attribute with parameter"
            """
class B:
    def __init__(self, name: str):
        self.name = name

b = B("test")
b.name
            """,  # language=none
            [ReferenceTestNode("name.line4", "FunctionDef.__init__", ["Parameter.name.line3"]),
             ReferenceTestNode("b.name.line7", "Module.", ["InstanceVariable.B.name.line4"]),
             ReferenceTestNode("b.line7", "Module.", ["GlobalVariable.b.line6"]),
             ReferenceTestNode("B.line6", "Module.", ["GlobalVariable.B.line2"])]
        ),
        (  # language=Python "instance attribute with parameter and class attribute"
            """
class X:
    class_attr = 10

    def __init__(self, name: str):
        self.name = name

x = X("test")
x.name
x.class_attr
            """,  # language=none
            [ReferenceTestNode("name.line6", "FunctionDef.__init__", ["Parameter.name.line5"]),
             ReferenceTestNode("x.name.line9", "Module.", ["InstanceVariable.X.name.line6"]),
             ReferenceTestNode("x.line9", "Module.", ["GlobalVariable.x.line8"]),
             ReferenceTestNode("x.class_attr.line10", "Module.", ["ClassVariable.X.class_attr.line3"]),
             ReferenceTestNode("x.line10", "Module.", ["GlobalVariable.x.line8"]),
             ReferenceTestNode("X.line8", "Module.", ["GlobalVariable.X.line2"])]
        ),
        (  # language=Python "class attribute initialized with instance attribute"
            """
class B:
    instance_attr1: int

    def __init__(self):
        self.instance_attr1 = 10

b = B()
var1 = b.instance_attr1
            """,  # language=none
            [ReferenceTestNode("b.instance_attr1.line9", "Module.", ["FAILClassVariable.B.instance_attr1.line3",  # TODO: What do we want here?
                                                                     "FAILInstanceVariable.B.instance_attr1.line6"]),

             ReferenceTestNode("b.line9", "Module.", ["GlobalVariable.b.line8"]),
             ReferenceTestNode("B.line8", "Module.", ["GlobalVariable.B.line2"])]
        ),
        (  # language=Python "chained class attribute and instance attribute"
            """
class A:
    def __init__(self):
        self.name = 10

class B:
    upper_class: A = A()

b = B()
x = b.upper_class.name
            """,  # language=none
            [ReferenceTestNode("b.upper_class.name.line10", "Module.", ["InstanceVariable.A.name.line4"]),  # TODO:
             ReferenceTestNode("b.upper_class.line10", "Module.", ["ClassVariable.B.upper_class.line7"]),
             ReferenceTestNode("b.line10", "Module.", ["GlobalVariable.b.line9"]),
             ReferenceTestNode("A.line7", "ClassDef.B", ["GlobalVariable.A.line2"]),
             ReferenceTestNode("B.line9", "Module.", ["GlobalVariable.B.line6"]),
             ]
        ),
        (  # language=Python "chained instance attributes"
            """
class A:
    def __init__(self):
        self.b = B()

class B:
    def __init__(self):
        self.c = C()

class C:
    def __init__(self):
        self.name = "name"

a = A()
a.b.c.name
            """,  # language=none
            [ReferenceTestNode("a.b.c.name.line15", "Module.", ["InstanceVariable.C.name.line12"]),
             ReferenceTestNode("a.b.c.line15", "Module.", ["InstanceVariable.B.c.line8"]),
             ReferenceTestNode("a.b.line15", "Module.", ["InstanceVariable.A.b.line4"]),
             ReferenceTestNode("a.line15", "Module.", ["GlobalVariable.a.line14"]),
             ReferenceTestNode("B.line4", "FunctionDef.A.__init__", ["GlobalVariable.B.line6"]),
             ReferenceTestNode("C.line8", "FunctionDef.B.__init__", ["GlobalVariable.C.line10"]),
             ReferenceTestNode("A.line14", "Module.", ["GlobalVariable.A.line2"]),
             ]
        ),
        (  # language=Python "two classes with same signature"
            """
class A:
    def __init__(self, name: str):
        self.name = name

class B:
    def __init__(self, name: str):
        self.name = name

a = A("value")
b = B("test")
a.name
b.name
            """,  # language=none
            [ReferenceTestNode("name.line4", "FunctionDef.__init__", ["Parameter.name.line3"]),
             ReferenceTestNode("name.line8", "FunctionDef.__init__", ["Parameter.name.line7"]),
             ReferenceTestNode("a.name.line12", "Module.", ["InstanceVariable.A.name.line4",  # class A
                                                            "InstanceVariable.B.name.line8"]),  # class B
             ReferenceTestNode("a.line12", "Module.", ["GlobalVariable.a.line10"]),
             ReferenceTestNode("b.name.line13", "Module.", ["InstanceVariable.A.name.line4",  # class A
                                                            "InstanceVariable.B.name.line8"]),
             ReferenceTestNode("b.line13", "Module.", ["GlobalVariable.b.line11"]),  # class B
             ReferenceTestNode("A.line10", "Module.", ["GlobalVariable.A.line2"]),
             ReferenceTestNode("B.line11", "Module.", ["GlobalVariable.B.line6"]),
             ]
        ),
        (  # language=Python "getter function with self"
            """
class C:
    state: int = 0

    def get_state(self):
        return self.state
            """,  # language= None
            [ReferenceTestNode("self.state.line6", "FunctionDef.get_state", ["ClassVariable.C.state.line3"]),
             ReferenceTestNode("self.line6", "FunctionDef.get_state", ["Parameter.self.line5"])]
        ),
        (  # language=Python "getter function with classname"
            """
class C:
    state: int = 0

    def get_state(self):
        return C.state
            """,  # language= None
            [ReferenceTestNode("C.state.line6", "FunctionDef.get_state", ["ClassVariable.C.state.line3"]),
             ReferenceTestNode("C.line6", "FunctionDef.get_state", ["GlobalVariable.C.line2"])]
        ),
        (  # language=Python "setter function with self"
            """
class C:
    state: int = 0

    def set_state(self, state):
        self.state = state  # TODO: Problem: the parameter "state" has the same name as the class variable "state" unterscheide zwischen MAT und AsssignName um Parameter rauszufilterna
            """,  # language= None
            [ReferenceTestNode("state.line6", "FunctionDef.set_state", ["Parameter.state.line5"]),
             ReferenceTestNode("self.line6", "FunctionDef.set_state", ["Parameter.self.line5"]),
             ReferenceTestNode("self.state.line6", "FunctionDef.set_state", ["ClassVariable.C.state.line3"])]
        ),  # TODO: what do we do with self.state?
        (  # language=Python "setter function with self different name"
            """
class C:
    stateX: int = 0

    def set_state(self, state):  # TODO: find the name of the first parameter
        self.stateX = state
            """,  # language= None
            [ReferenceTestNode("state.line6", "FunctionDef.set_state", ["Parameter.state.line5"])]
        ),  # TODO: what do we do with self.stateX?
        (  # language=Python "setter function with classname different name"
            """
class C:
    stateX: int = 0

    def set_state(self, state):
        C.stateX = state
            """,  # language= None
            [ReferenceTestNode("state.line6", "FunctionDef.set_state", ["Parameter.state.line5"])]
        ),  # TODO: what do we do with C.stateX?
        (  # language=Python "setter function as @staticmethod"
            """
class C:
    state: int = 0

    @staticmethod
    def set_state(self, state):
        self.state = state  # TODO: Problem: the parameter "state" has the same name as the class variable "state"
            """,  # language= None
            [ReferenceTestNode("state.line7", "FunctionDef.set_state", ["Parameter.state.line6"]),
             ReferenceTestNode("self.line7", "FunctionDef.set_state", ["Parameter.self.line6"])]
        ),
        (  # language=Python "setter function as @classmethod"
            """
class C:
    state: int = 0

    @classmethod
    def set_state(cls, state):
        cls.state = state  # TODO: Problem: the parameter "state" has the same name as the class variable "state"
            """,  # language= None
            [ReferenceTestNode("state.line7", "FunctionDef.set_state", ["Parameter.state.line6"]),
             ReferenceTestNode("cls.line7", "FunctionDef.set_state", ["Parameter.cls.line6"])]
        ),
        # TODO: is_instance_methode: check if decorator
        #       if not check first parameter (usually self)
    ],
    ids=[
        "class attribute value",
        "class attribute target",
        "class attribute multiple usage",
        "chained class attribute",
        "instance attribute value",
        "instance attribute target",
        "instance attribute with parameter",
        "instance attribute with parameter and class attribute",
        "class attribute initialized with instance attribute",
        "chained class attribute and instance attribute",
        "chained instance attributes",
        "two classes with same signature",
        "getter function with self",
        "getter function with classname",
        "setter function with self",
        "setter function with self different name",
        "setter function with classname different name",
        "setter function as @staticmethod",
        "setter function as @classmethod",
    ]
)
def test_resolve_references_member_access(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code)
    transformed_references: list[ReferenceTestNode] = []

    for node in references:
        transformed_references.append(transform_reference_node(node))

    # assert references == expected
    assert transformed_references == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "if in statement global scope"
            """
var1 = [1, 2, 3]
if 1 in var1:
    var1
        """,  # language=none
            [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line4", "Module.", ["GlobalVariable.var1.line2"])]
        ),
        (  # language=Python "if statement global scope"
            """
var1 = 10
if var1 > 0:
    var1
        """,  # language=none
            [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line4", "Module.", ["GlobalVariable.var1.line2"])]
        ),
        (  # language=Python "if else statement global scope"
            """
var1 = 10
if var1 > 0:
    var1
else:
    2 * var1
        """,  # language=none
            [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line4", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line6", "Module.", ["GlobalVariable.var1.line2"])]
        ),
        (  # language=Python "if elif else statement global scope"
            """
var1 = 10
if var1 > 0:
    var1
elif var1 < 0:
    -var1
else:
    var1
        """,  # language=none
            [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line4", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line5", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line6", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line8", "Module.", ["GlobalVariable.var1.line2"])]
        ),
        (  # language=Python "match statement global scope"
            """
var1 = 10
match var1:
    case 1: var1
    case 2: 2 * var1
    case (a, b): var1, a, b  # TODO: Match should get its own scope (LATER: for further improvement)  maybe add its parent
        """,  # language=none
            [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line4", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line5", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line6", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("a.line6", "Module.", ["GlobalVariable.a.line6"]),  # TODO: ask Lars
             ReferenceTestNode("b.line6", "Module.", ["GlobalVariable.b.line6"])]
        # TODO: ask Lars if this is true GlobalVariable
        ),
        (  # language=Python "try except statement global scope"
            """
num1 = 2
num2 = 0
try:
    result = num1 / num2
    result
except ZeroDivisionError as zde:   # TODO: zde is not detected as a global variable # TODO: Except should get its own scope (LATER: for further improvement)
    zde
        """,  # language=none
            [ReferenceTestNode("num1.line5", "Module.", ["GlobalVariable.num1.line2"]),
             ReferenceTestNode("num2.line5", "Module.", ["GlobalVariable.num2.line3"]),
             ReferenceTestNode("result.line6", "Module.", ["GlobalVariable.result.line5"]),
             ReferenceTestNode("zde.line8", "Module.", ["GlobalVariable.zde.line7"])]
        ),
    ],
    ids=[
        "if statement global scope",
        "if else statement global scope",
        "if elif else statement global scope",
        "if in statement global scope",
        "match statement global scope",
        "try except statement global scope",
    ]
)
def test_resolve_references_conditional_statements(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code)
    transformed_references: list[ReferenceTestNode] = []

    for node in references:
        transformed_references.append(transform_reference_node(node))

    # assert references == expected
    assert set(transformed_references) == set(expected)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "for loop with global runtime variable global scope"
            """
var1 = 10
for i in range(var1):
    i
        """,  # language=none
            [ReferenceTestNode("range.line3", "Module.", ["Builtin.range"]),
             ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("i.line4", "Module.", ["GlobalVariable.i.line3"])]
        ),
        (  # language=Python "for loop wih local runtime variable local scope"
            """
var1 = 10
def func1():
    for i in range(var1):
        i
        """,  # language=none
            [ReferenceTestNode("range.line4", "FunctionDef.func1", ["Builtin.range"]),
             ReferenceTestNode("var1.line4", "FunctionDef.func1", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("i.line5", "FunctionDef.func1", ["LocalVariable.i.line4"])]
        ),

        (  # language=Python "for loop with local runtime variable global scope"
            """
nums = ["one", "two", "three"]
for num in nums:
    num
        """,  # language=none
            [ReferenceTestNode("nums.line3", "Module.", ["GlobalVariable.nums.line2"]),
             ReferenceTestNode("num.line4", "Module.", ["GlobalVariable.num.line3"])]
        ),
        (  # language=Python "for loop in list comprehension global scope"
            """
nums = ["one", "two", "three"]
lengths = [len(num) for num in nums]  # TODO: list comprehension should get its own scope (LATER: for further improvement)
lengths
        """,  # language=none
            [ReferenceTestNode("len.line3", "Module.", ["Builtin.len"]),
             ReferenceTestNode("num.line3", "List.", ["LocalVariable.num.line3"]),
             ReferenceTestNode("nums.line3", "Module.", ["GlobalVariable.nums.line2"]),
             ReferenceTestNode("lengths.line4", "Module.", ["GlobalVariable.lengths.line3"])]
        ),
        (  # language=Python "while loop global scope"
            """
var1 = 10
while var1 > 0:
    var1
        """,  # language=none
            [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var1.line4", "Module.", ["GlobalVariable.var1.line2"])]
        ),
    ],
    ids=[
        "for loop with global runtime variable global scope",
        "for loop wih local runtime variable local scope",
        "for loop with local runtime variable global scope",
        "for loop in list comprehension global scope",
        "while loop global scope",
    ]
)
def test_resolve_references_loops(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code)
    transformed_references: list[ReferenceTestNode] = []

    for node in references:
        transformed_references.append(transform_reference_node(node))

    # assert references == expected
    assert set(transformed_references) == set(expected)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "array and indexed array global scope"
            """
arr = [1, 2, 3]
val = arr
res = arr[0]
arr[0] = 10
            """,  # language=none
            [ReferenceTestNode("arr.line3", "Module.", ["GlobalVariable.arr.line2"]),
             ReferenceTestNode("arr.line4", "Module.", ["GlobalVariable.arr.line2"]),
             ReferenceTestNode("arr.line5", "Module.", ["GlobalVariable.arr.line2"])]
        ),
        (  # language=Python "dictionary global scope"
            """
dictionary = {"key1": 1, "key2": 2}
dictionary["key1"] = 0
            """,  # language=none
            [ReferenceTestNode("dictionary.line3", "Module.", ["GlobalVariable.dictionary.line2"])]
        ),
        (  # language=Python "map function global scope"
            """
numbers = [1, 2, 3, 4, 5]

def square(x):
    return x ** 2

squares = list(map(square, numbers))
squares
            """,  # language=none
            [ReferenceTestNode("list.line7", "Module.", ["Builtin.list"]),
             ReferenceTestNode("map.line7", "Module.", ["Builtin.map"]),
             ReferenceTestNode("x.line5", "FunctionDef.square", ["Parameter.x.line4"]),
             ReferenceTestNode("square.line7", "Module.", ["GlobalVariable.square.line4"]),
             ReferenceTestNode("numbers.line7", "Module.", ["GlobalVariable.numbers.line2"]),
             ReferenceTestNode("squares.line8", "Module.", ["GlobalVariable.squares.line7"])]
        ),
        (  # language=Python "two variables"
            """
x = 10
y = 20
x + y
            """,  # language=none
            [ReferenceTestNode("x.line4", "Module.", ["GlobalVariable.x.line2"]),
             ReferenceTestNode("y.line4", "Module.", ["GlobalVariable.y.line3"])]
        ),
        (  # language=Python "double return"
            """
def double_return(a, b):
    return a, b

x, y = double_return(10, 20)
x, y
            """,  # language=none
            [ReferenceTestNode("double_return.line5", "Module.", ["GlobalVariable.double_return.line2"]),
             ReferenceTestNode("a.line3", "FunctionDef.double_return", ["Parameter.a.line2"]),
             ReferenceTestNode("b.line3", "FunctionDef.double_return", ["Parameter.b.line2"]),
             ReferenceTestNode("x.line6", "Module.", ["GlobalVariable.x.line5"]),
             ReferenceTestNode("y.line6", "Module.", ["GlobalVariable.y.line5"])]
        ),
        (  # language=Python "reassignment"
            """
x = 10
x = 20
x
            """,  # language=none
            [ReferenceTestNode("x.line4", "Module.", ["GlobalVariable.x.line2", "GlobalVariable.x.line3"])]
        ),
        (  # language=Python "vars with comma"
            """
x = 10
y = 20
x, y
            """,  # language=none
            [ReferenceTestNode("x.line4", "Module.", ["GlobalVariable.x.line2"]),
             ReferenceTestNode("y.line4", "Module.", ["GlobalVariable.y.line3"])]
        ),
        (  # language=Python "vars with extended iterable unpacking"
            """
a, *b, c = [1, 2, 3, 4, 5]
a, b, c
            """,  # language=none
            [ReferenceTestNode("a.line3", "Module.", ["GlobalVariable.a.line2"]),
             ReferenceTestNode("b.line3", "Module.", ["GlobalVariable.b.line2"]),
             ReferenceTestNode("c.line3", "Module.", ["GlobalVariable.c.line2"])]
        ),
        (  # language=Python "f-string"
            """
x = 10
y = 20
f"{x} + {y} = {x + y}"
            """,  # language=none
            [ReferenceTestNode("x.line4", "Module.", ["GlobalVariable.x.line2"]),
             ReferenceTestNode("y.line4", "Module.", ["GlobalVariable.y.line3"]),
             ReferenceTestNode("x.line4", "Module.", ["GlobalVariable.x.line2"]),
             ReferenceTestNode("y.line4", "Module.", ["GlobalVariable.y.line3"])]
        ),
        (  # language=Python "multiple references in one line"
            """
var1 = 10
var2 = 20

res = var1 + var2 - (var1 * var2)
            """,  # language=none
            [ReferenceTestNode("var1.line5", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var2.line5", "Module.", ["GlobalVariable.var2.line3"]),
             ReferenceTestNode("var1.line5", "Module.", ["GlobalVariable.var1.line2"]),
             ReferenceTestNode("var2.line5", "Module.", ["GlobalVariable.var2.line3"])]
        ),
        (  # language=Python "walrus operator"
            """
y = (x := 3) + 10
x, y
            """,  # language=none
            [ReferenceTestNode("x.line3", "Module.", ["GlobalVariable.x.line2"]),
             ReferenceTestNode("y.line3", "Module.", ["GlobalVariable.y.line2"])]
        ),
        (  # language=Python "variable swap"
            """
a = 1
b = 2
a, b = b, a
            """,  # language=none
            [ReferenceTestNode("a.line4", "Module.", ["GlobalVariable.a.line2", "GlobalVariable.a.line4"]),
             ReferenceTestNode("b.line4", "Module.", ["GlobalVariable.b.line3", "GlobalVariable.b.line4"])]
        ),
        (  # language=Python "aliases"
            """
a = 10
b = a
c = b
c
            """,  # language=none
            [ReferenceTestNode("a.line3", "Module.", ["GlobalVariable.a.line2"]),
             ReferenceTestNode("b.line4", "Module.", ["GlobalVariable.b.line3"]),
             ReferenceTestNode("c.line5", "Module.", ["GlobalVariable.c.line4"])]
        ),
        #         (  # language=Python "regex"
        #             """
        # import re
        #
        # regex = re.compile(r"^\s*#")
        # string = "    # comment"
        #
        # if regex.match(string) is None:
        #     print(string, end="")
        #             """,  # language=none
        #             []
        #         ),
    ],
    ids=[
        "array and indexed array global scope",
        "dictionary global scope",
        "map function global scope",
        "two variables",
        "double return",
        "reassignment",
        "vars with comma",
        "vars with extended iterable unpacking",
        "f-string",
        "multiple references in one line",
        "walrus operator",
        "variable swap",
        "aliases",
        # "regex"
    ]
)
def test_resolve_references_miscellaneous(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code)
    transformed_references: list[ReferenceTestNode] = []

    for node in references:
        transformed_references.append(transform_reference_node(node))

    # assert references == expected
    assert set(transformed_references) == set(expected)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "builtin function call"
            """
print("Hello, World!")
            """,  # language=none
            [ReferenceTestNode("print.line2", "Module.", ["Builtin.print"])]
        ),
        (  # language=Python "function call shadowing builtin function"
            """
print("Hello, World!")

def print(s):
    pass

print("Hello, World!")
            """,  # language=none
            [ReferenceTestNode("print.line2", "Module.", ["Builtin.print", "GlobalVariable.print.line4"]),
             ReferenceTestNode("print.line7", "Module.", ["Builtin.print", "GlobalVariable.print.line4"])]
        ),
        (  # language=Python "function call"
            """
def f():
    pass

f()
            """,  # language=none
            [ReferenceTestNode("f.line5", "Module.", ["GlobalVariable.f.line2"])]
        ),
        (  # language=Python "function call with parameter"
            """
def f(a):
    return a

x = 10
f(x)
            """,  # language=none
            [ReferenceTestNode("f.line6", "Module.", ["GlobalVariable.f.line2"]),
             ReferenceTestNode("a.line3", "FunctionDef.f", ["Parameter.a.line2"]),
             ReferenceTestNode("x.line6", "Module.", ["GlobalVariable.x.line5"])]
        ),
        (  # language=Python "function call with keyword parameter"
            """
def f(value):
    return value

x = 10
f(value=x)
            """,  # language=none
            [ReferenceTestNode("f.line6", "Module.", ["GlobalVariable.f.line2"]),
             ReferenceTestNode("value.line3", "FunctionDef.f", ["Parameter.value.line2"]),
             ReferenceTestNode("x.line6", "Module.", ["GlobalVariable.x.line5"])]
        ),
        (  # language=Python "function call as value"
            """
def f(a):
    return a

x = f(10)
            """,  # language=none
            [ReferenceTestNode("f.line5", "Module.", ["GlobalVariable.f.line2"]),
             ReferenceTestNode("a.line3", "FunctionDef.f", ["Parameter.a.line2"])]
        ),
        (  # language=Python "nested function call"
            """
def f(a):
    return a * 2

f(f(f(10)))
            """,  # language=none
            [ReferenceTestNode("f.line5", "Module.", ["GlobalVariable.f.line2"]),
             ReferenceTestNode("f.line5", "Module.", ["GlobalVariable.f.line2"]),
             ReferenceTestNode("f.line5", "Module.", ["GlobalVariable.f.line2"]),
             ReferenceTestNode("a.line3", "FunctionDef.f", ["Parameter.a.line2"])]
        ),
        (  # language=Python "two functions"
            """
def fun1():
    return "Function 1"

def fun2():
    return "Function 2"

fun1()
fun2()
            """,  # language=none
            [ReferenceTestNode("fun1.line8", "Module.", ["GlobalVariable.fun1.line2"]),
             ReferenceTestNode("fun2.line9", "Module.", ["GlobalVariable.fun2.line5"])]
        ),
        (  # language=Python "functon with function as parameter"
            """
def fun1():
    return "Function 1"

def fun2():
    return "Function 2"

def call_function(f):
    return f()

call_function(fun1)
call_function(fun2)
            """,  # language=none
            [ReferenceTestNode("f.line9", "FunctionDef.call_function", ["Parameter.f.line8"]),
             # f should be detected as a call but is treated as a parameter, since the passed function is not known before runtime
             ReferenceTestNode("call_function.line11", "Module.", ["GlobalVariable.call_function.line8"]),
             ReferenceTestNode("call_function.line12", "Module.", ["GlobalVariable.call_function.line8"]),
             ReferenceTestNode("fun1.line11", "Module.", ["GlobalVariable.fun1.line2"]),
             ReferenceTestNode("fun2.line12", "Module.", ["GlobalVariable.fun2.line5"])]
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
            [
             ReferenceTestNode("fun1.line10", "FunctionDef.call_function", ["GlobalVariable.fun1.line2"]),
             ReferenceTestNode("fun2.line12", "FunctionDef.call_function", ["GlobalVariable.fun2.line5"]),
             ReferenceTestNode("call_function.line14", "Module.", ["GlobalVariable.call_function.line8"]),
             ReferenceTestNode("a.line9", "FunctionDef.call_function", ["Parameter.a.line8"])]
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
            [ReferenceTestNode("print.line3", "FunctionDef.f", ["Builtin.print"]),
             ReferenceTestNode("f.line5", "FunctionDef.f", ["GlobalVariable.f.line2"]),
             ReferenceTestNode("f.line8", "Module.", ["GlobalVariable.f.line2"]),
             ReferenceTestNode("a.line3", "FunctionDef.f", ["Parameter.a.line2"]),
             ReferenceTestNode("a.line4", "FunctionDef.f", ["Parameter.a.line2"]),
             ReferenceTestNode("a.line5", "FunctionDef.f", ["Parameter.a.line2"]),
             ReferenceTestNode("x.line8", "Module.", ["GlobalVariable.x.line7"])]
        ),
        (  # language=Python "class instantiation"
            """
class F:
    pass

F()
            """,  # language=none
            [ReferenceTestNode("F.line5", "Module.", ["GlobalVariable.F.line2"])]
        ),
        (  # language=Python "lambda function"
            """
lambda x, y: x + y
            """,  # language=none
            [ReferenceTestNode("x.line2", "Lambda", ["LocalVariable.x.line2"]),
             ReferenceTestNode("y.line2", "Lambda", ["LocalVariable.y.line2"])]
        ),
        (  # language=Python "lambda function call"
            """
(lambda x, y: x + y)(10, 20)
            """,  # language=none
            [ReferenceTestNode("x.line2", "Lambda", ["LocalVariable.x.line2"]),
             ReferenceTestNode("y.line2", "Lambda", ["LocalVariable.y.line2"])]
        ),
        (  # language=Python "lambda function used as normal function"
            """
double = lambda x: 2 * x

double(10)
            """,  # language=none
            [ReferenceTestNode("x.line2", "Lambda", ["LocalVariable.x.line2"]),
             ReferenceTestNode("double.line4", "Module.", ["GlobalVariable.double.line2"])]
        ),
        (  # language=Python "two lambda function used as normal function with same name"
            """
class A:
    double = lambda x: 2 * x

class B:
    double = lambda x: 2 * x

A.double(10)
B.double(10)
            """,  # language=none
            [ReferenceTestNode("x.line3", "Lambda", ["LocalVariable.x.line3"]),
             ReferenceTestNode("A.line8", "Module.", ["GlobalVariable.A.line2"]),
             ReferenceTestNode("A.double.line8", "Module.", ["ClassVariable.A.double.line3",
                                                             "ClassVariable.B.double.line6"]),
             ReferenceTestNode("x.line6", "Lambda", ["LocalVariable.x.line6"]),
             ReferenceTestNode("B.line9", "Module.", ["GlobalVariable.B.line5"]),
             ReferenceTestNode("B.double.line9", "Module.", ["ClassVariable.A.double.line3",
                                                             "ClassVariable.B.double.line6"])]
        ),  # since we only return a list of all possible references, we can't distinguish between the two functions
        (  # language=Python "lambda function used as normal function and normal function with same name"
            """
class A:
    double = lambda x: 2 * x

class B:
    @staticmethod
    def double(x):
        return 2 * x

A.double(10)
B.double(10)
            """,  # language=none
            [ReferenceTestNode("x.line3", "Lambda", ["LocalVariable.x.line3"]),
             ReferenceTestNode("A.line10", "Module.", ["GlobalVariable.A.line2"]),
             ReferenceTestNode("A.double.line10", "Module.", ["ClassVariable.A.double.line3",
                                                              "ClassVariable.B.double.line7"]),
             ReferenceTestNode("x.line8", "FunctionDef.double", ["Parameter.x.line7"]),
             ReferenceTestNode("B.line11", "Module.", ["GlobalVariable.B.line5"]),
             ReferenceTestNode("B.double.line11", "Module.", ["ClassVariable.A.double.line3",
                                                              "ClassVariable.B.double.line7"])]
        ),  # since we only return a list of all possible references, we can't distinguish between the two functions
        (  # language=Python "lambda function as key"
            """
names = ["a", "abc", "ab", "abcd"]

sort = sorted(names, key=lambda x: len(x))
sort
            """,  # language=none
            [ReferenceTestNode("sorted.line4", "Module.", ["Builtin.sorted"]),
             ReferenceTestNode("len.line4", "Lambda", ["Builtin.len"]),
             ReferenceTestNode("names.line4", "Module.", ["GlobalVariable.names.line2"]),
             ReferenceTestNode("x.line4", "Lambda", ["LocalVariable.x.line4"]),
             ReferenceTestNode("sort.line5", "Module.", ["GlobalVariable.sort.line4"])]
        ),
        (  # language=Python "generator function"
            """
def square_generator(limit):
    for i in range(limit):
        yield i**2

gen = square_generator(5)
for value in gen:
    value
            """,  # language=none
            [ReferenceTestNode("range.line3", "FunctionDef.square_generator", ["Builtin.range"]),
             ReferenceTestNode("square_generator.line6", "Module.", ["GlobalVariable.square_generator.line2"]),
             ReferenceTestNode("limit.line3", "FunctionDef.square_generator", ["Parameter.limit.line2"]),
             ReferenceTestNode("i.line4", "FunctionDef.square_generator", ["LocalVariable.i.line3"]),
             ReferenceTestNode("gen.line7", "Module.", ["GlobalVariable.gen.line6"]),
             ReferenceTestNode("value.line8", "Module.", ["GlobalVariable.value.line7"])]
        ),
        (  # language=Python "functions with same name but different classes"
            """
class A:
    @staticmethod
    def add(a, b):
        return a + b

class B:
    @staticmethod
    def add(a, b):
        return a + 2 * b

A.add(1, 2)
B.add(1, 2)
            """,  # language=none
            [ReferenceTestNode("a.line5", "FunctionDef.add", ["Parameter.a.line4"]),
             ReferenceTestNode("b.line5", "FunctionDef.add", ["Parameter.b.line4"]),
             ReferenceTestNode("a.line10", "FunctionDef.add", ["Parameter.a.line9"]),
             ReferenceTestNode("b.line10", "FunctionDef.add", ["Parameter.b.line9"]),
             ReferenceTestNode("A.line12", "Module.", ["GlobalVariable.A.line2"]),
             ReferenceTestNode("A.add.line12", "Module.", ["ClassVariable.A.add.line3",
                                                           "ClassVariable.B.add.line8"]),
             ReferenceTestNode("B.line13", "Module.", ["GlobalVariable.B.line7"]),
             ReferenceTestNode("B.add.line13", "Module.", ["ClassVariable.A.add.line3",
                                                           "ClassVariable.B.add.line8"])]
        ),  # since we only return a list of all possible references, we can't distinguish between the two functions
        (  # language=Python "functions with same name but different signature"
            """
class A:
    @staticmethod
    def add(a, b):
        return a + b

class B:
    @staticmethod
    def add(a, b, c):
        return a + b + c

A.add(1, 2)
B.add(1, 2, 3)
            """,  # language=none
            [ReferenceTestNode("a.line5", "FunctionDef.add", ["Parameter.a.line4"]),
             ReferenceTestNode("b.line5", "FunctionDef.add", ["Parameter.b.line4"]),
             ReferenceTestNode("a.line10", "FunctionDef.add", ["Parameter.a.line9"]),
             ReferenceTestNode("b.line10", "FunctionDef.add", ["Parameter.b.line9"]),
             ReferenceTestNode("A.line12", "Module.", ["GlobalVariable.A.line2"]),
             ReferenceTestNode("A.add.line12", "Module.", ["ClassVariable.A.add.line3",
                                                           "ClassVariable.B.add.line8"]),
             ReferenceTestNode("B.line13", "Module.", ["GlobalVariable.B.line7"]),
             ReferenceTestNode("B.add.line13", "Module.", ["ClassVariable.A.add.line3",
                                                           "ClassVariable.B.add.line8"])]
            # TODO: [LATER] we should detect the different signatures
        ),
        (  # language=Python "class function call"
            """
class A:
    def fun_a(self):
        return

a = A()
a.fun_a()
            """,  # language=none
            [ReferenceTestNode("A.line6", "Module.", ["GlobalVariable.A.line2"]),
             ReferenceTestNode("a.fun_a.line7", "Module.", ["ClassVariable.A.fun_a.line3"]),
             ReferenceTestNode("a.line7", "Module.", ["GlobalVariable.a.line6"])]
        ),
        (  # language=Python "class function call, direct call"
            """
class A:
    def fun_a(self):
        return

A().fun_a()
            """,  # language=none
            [ReferenceTestNode("A.line6", "Module.", ["GlobalVariable.A.line2"]),
             ReferenceTestNode("A.fun_a.line6", "Module.", ["ClassVariable.A.fun_a.line3"])]
        ),
    ],
    ids=[
        "builtin function call",
        "function call shadowing builtin function",
        "function call",
        "function call with parameter",
        "function call with keyword parameter",
        "function call as value",
        "nested function call",
        "two functions",
        "functon with function as parameter",
        "function with conditional branching",
        "recursive function call",
        "class instantiation",
        "lambda function",
        "lambda function call",
        "lambda function used as normal function",
        "two lambda function used as normal function with same name",
        "lambda function used as normal function and normal function with same name",
        "lambda function as key",
        "generator function",
        "functions with same name but different classes",
        "functions with same name but different signature",
        "class function call",
        "class function call, direct call",
    ]
)
def test_resolve_references_calls(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code)
    transformed_references: list[ReferenceTestNode] = []

    # assert references == expected
    for node in references:
        transformed_references.append(transform_reference_node(node))

    assert set(transformed_references) == set(expected)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "import"
            """
import math

math
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python "import with use"
            """
import math

math.pi
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python "import multiple"
            """
import math, sys

math.pi
sys.version
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python "import as"
            """
import math as m

m.pi
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python "import from"
            """
from math import sqrt

sqrt(4)
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python "import from multiple"
            """
from math import pi, sqrt

pi
sqrt(4)
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python "import from as"
            """
from math import sqrt as s

s(4)
            """,  # language=none
            [""]  # TODO
        ),
        (  # language=Python "import from as multiple"
            """
from math import pi as p, sqrt as s

p
s(4)
            """,  # language=none
            [""]  # TODO
        ),
    ],
    ids=[
        "import",
        "import with use",
        "import multiple",
        "import as",
        "import from",
        "import from multiple",
        "import from as",
        "import from as multiple",
    ]
)
@pytest.mark.xfail(reason="Not implemented yet")
def test_resolve_references_imports(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code)
    transformed_references: list[ReferenceTestNode] = []

    for node in references:
        transformed_references.append(transform_reference_node(node))

    # assert references == expected
    assert set(transformed_references) == set(expected)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "dataclass"
            """
from dataclasses import dataclass

@dataclass
class State:
    pass

State()
            """,  # language=none
            [ReferenceTestNode("State.line8", "Module.", ["GlobalVariable.State.line5"])]
        ),
        (  # language=Python "dataclass with default attribute"
            """
from dataclasses import dataclass

@dataclass
class State:
    state: int = 0

State().state
            """,  # language=none
            [ReferenceTestNode("State.line8", "Module.", ["GlobalVariable.State.line5"]),
             ReferenceTestNode("State.state.line8", "Module.", ["ClassVariable.State.state.line6"])]
        ),
        (  # language=Python "dataclass with attribute"
            """
from dataclasses import dataclass

@dataclass
class State:
    state: int

State(0).state
            """,  # language=none
            [ReferenceTestNode("State.line8", "Module.", ["GlobalVariable.State.line5"]),
             ReferenceTestNode("State.state.line8", "Module.", ["ClassVariable.State.state.line6"])]
        ),
        (  # language=Python "dataclass with @property and @setter"
            """
from dataclasses import dataclass

@dataclass
class State:
    _state: int

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value # TODO: what do we do with self._state?

State(10).state
            """,  # language=none
            [ReferenceTestNode("State.line16", "Module.", ["GlobalVariable.State.line5"]),
             ReferenceTestNode("self._state.line10", "FunctionDef.state", ["ClassVariable.State._state.line6"]),
             ReferenceTestNode("value.line14", "FunctionDef.state", ["Parameter.value.line13"]),
             ReferenceTestNode("State.state.line16", "Module.", ["ClassVariable.State._state.line6"])]
        ),
    ],
    ids=[
        "dataclass",
        "dataclass with default attribute",
        "dataclass with attribute",
        "dataclass with @property and @setter",
    ]
)
# TODO: it is problematic, that the order of references is relevant, since it does not matter in the later usage
#       of these results. Therefore, we should return a set of references instead of a list.
#       For now convert the result to a set for testing purposes
def test_resolve_references_dataclasses(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code)
    transformed_references: list[ReferenceTestNode] = []

    for node in references:
        transformed_references.append(transform_reference_node(node))

    # assert references == expected
    assert set(transformed_references) == set(expected)


def transform_reference_node(node: ReferenceNode) -> ReferenceTestNode:
    if isinstance(node.node, MemberAccess | MemberAccessValue | MemberAccessTarget):
        expression = get_base_expression(node.node)
        return ReferenceTestNode(name=f"{node.node.name}.line{expression.lineno}",
                                 scope=f"{node.scope.symbol.node.__class__.__name__}.{node.scope.symbol.node.name}",
                                 referenced_symbols=sorted([str(ref) for ref in node.referenced_symbols]))
    if isinstance(node.scope.symbol.node, astroid.Lambda) and not isinstance(node.scope.symbol.node,
                                                                             astroid.FunctionDef):
        if isinstance(node.node, astroid.Call):
            return ReferenceTestNode(name=f"{node.node.func.name}.line{node.node.func.lineno}",
                                     scope=f"{node.scope.symbol.node.__class__.__name__}",
                                     referenced_symbols=sorted([str(ref) for ref in node.referenced_symbols]))
        return ReferenceTestNode(name=f"{node.node.name}.line{node.node.lineno}",
                                 scope=f"{node.scope.symbol.node.__class__.__name__}",
                                 referenced_symbols=sorted([str(ref) for ref in node.referenced_symbols]))
    if isinstance(node.node, astroid.Call):
        if isinstance(node.scope.symbol.node, astroid.FunctionDef) and node.scope.symbol.name == "__init__":
            return ReferenceTestNode(name=f"{node.node.func.name}.line{node.node.lineno}",
                                     scope=f"{node.scope.symbol.node.__class__.__name__}.{node.scope.symbol.klass.name}.{node.scope.symbol.node.name}",
                                     referenced_symbols=sorted([str(ref) for ref in node.referenced_symbols]))
        return ReferenceTestNode(name=f"{node.node.func.name}.line{node.node.func.lineno}",
                                 scope=f"{node.scope.symbol.node.__class__.__name__}.{node.scope.symbol.node.name}",
                                 referenced_symbols=sorted([str(ref) for ref in node.referenced_symbols]))
    return ReferenceTestNode(name=f"{node.node.name}.line{node.node.lineno}",
                             scope=f"{node.scope.symbol.node.__class__.__name__}.{node.scope.symbol.node.name}",
                             referenced_symbols=sorted([str(ref) for ref in node.referenced_symbols]))
