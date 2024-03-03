from __future__ import annotations

from dataclasses import dataclass, field

import astroid
import pytest
from library_analyzer.processing.api.purity_analysis import (
    get_base_expression,
    resolve_references,
)
from library_analyzer.processing.api.purity_analysis.model import (
    Builtin,
    ClassVariable,
    InstanceVariable,
    MemberAccess,
    MemberAccessTarget,
    MemberAccessValue,
    NodeID,
    Reasons,
    ReferenceNode,
)


@dataclass
class ReferenceTestNode:
    """Class for reference test nodes.

    A simplified class of the ReferenceNode class for testing purposes.

    Attributes
    ----------
    name : str
        The name of the node.
    scope : str
        The scope of the node as string.
    referenced_symbols : list[str]
        The list of referenced symbols as strings.
    """

    name: str
    scope: str
    referenced_symbols: list[str]

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.name}.{self.scope}"


@dataclass
class SimpleReasons:
    """Class for simple reasons.

    A simplified class of the Reasons class for testing purposes.

    Attributes
    ----------
    function_name : str
        The name of the function.
    writes : set[str]
        The set of the functions writes.
    reads : set[str]
        The set of the function reads.
    calls : set[str]
        The set of the function calls.
    """

    function_name: str
    writes: set[str] = field(default_factory=set)
    reads: set[str] = field(default_factory=set)
    calls: set[str] = field(default_factory=set)

    def __hash__(self) -> int:
        return hash(self.function_name)


def transform_reference_nodes(nodes: list[ReferenceNode]) -> list[ReferenceTestNode]:
    """Transform a list of ReferenceNodes to a list of ReferenceTestNodes.

    Parameters
    ----------
    nodes : list[ReferenceNode]
        The list of ReferenceNodes to transform.

    Returns
    -------
    list[ReferenceTestNode]
        The transformed list of ReferenceTestNodes.
    """
    transformed_nodes: list[ReferenceTestNode] = []

    for node in nodes:
        transformed_nodes.append(transform_reference_node(node))

    return transformed_nodes


def transform_reference_node(ref_node: ReferenceNode) -> ReferenceTestNode:
    """Transform a ReferenceNode to a ReferenceTestNode.

    Transforms a ReferenceNode to a ReferenceTestNode, so that they are no longer complex objects and easier to compare.

    Parameters
    ----------
    ref_node : ReferenceNode
        The ReferenceNode to transform.

    Returns
    -------
    ReferenceTestNode
        The transformed ReferenceTestNode.
    """
    if isinstance(ref_node.node.node, MemberAccess | MemberAccessValue | MemberAccessTarget):
        expression = get_base_expression(ref_node.node.node)
        if (
            ref_node.scope.symbol.name == "__init__"
            and isinstance(ref_node.scope.symbol, ClassVariable | InstanceVariable)
            and ref_node.scope.symbol.klass is not None
        ):
            return ReferenceTestNode(
                name=f"{ref_node.node.node.name}.line{expression.lineno}",
                scope=(
                    f"{ref_node.scope.symbol.node.__class__.__name__}."
                    f"{ref_node.scope.symbol.klass.name}."
                    f"{ref_node.scope.symbol.node.name}"
                ),
                referenced_symbols=sorted([str(ref) for ref in ref_node.referenced_symbols]),
            )
        return ReferenceTestNode(
            name=f"{ref_node.node.node.name}.line{expression.lineno}",
            scope=f"{ref_node.scope.symbol.node.__class__.__name__}.{ref_node.scope.symbol.node.name}",
            referenced_symbols=sorted([str(ref) for ref in ref_node.referenced_symbols]),
        )
    if isinstance(ref_node.scope.symbol.node, astroid.Lambda) and not isinstance(
        ref_node.scope.symbol.node,
        astroid.FunctionDef,
    ):
        if isinstance(ref_node.node.node, astroid.Call):
            return ReferenceTestNode(
                name=f"{ref_node.node.node.func.name}.line{ref_node.node.node.func.lineno}",
                scope=f"{ref_node.scope.symbol.node.__class__.__name__}",
                referenced_symbols=sorted([str(ref) for ref in ref_node.referenced_symbols]),
            )
        return ReferenceTestNode(
            name=f"{ref_node.node.node.name}.line{ref_node.node.node.lineno}",
            scope=f"{ref_node.scope.symbol.node.__class__.__name__}",
            referenced_symbols=sorted([str(ref) for ref in ref_node.referenced_symbols]),
        )
    if isinstance(ref_node.node.node, astroid.Call):
        if (
            isinstance(ref_node.scope.symbol.node, astroid.FunctionDef)
            and ref_node.scope.symbol.name == "__init__"
            and isinstance(ref_node.scope.symbol, ClassVariable | InstanceVariable)
            and ref_node.scope.symbol.klass is not None
        ):
            return ReferenceTestNode(
                name=f"{ref_node.node.node.func.name}.line{ref_node.node.node.lineno}",
                scope=f"{ref_node.scope.symbol.node.__class__.__name__}.{ref_node.scope.symbol.klass.name}.{ref_node.scope.symbol.node.name}",
                # type: ignore[union-attr] # "None" has no attribute "name" but since we check for the type before, this is fine
                referenced_symbols=sorted([str(ref) for ref in ref_node.referenced_symbols]),
            )
        if isinstance(ref_node.scope.symbol.node, astroid.ListComp):
            return ReferenceTestNode(
                name=f"{ref_node.node.node.func.name}.line{ref_node.node.node.func.lineno}",
                scope=f"{ref_node.scope.symbol.node.__class__.__name__}.",
                referenced_symbols=sorted([str(ref) for ref in ref_node.referenced_symbols]),
            )
        return ReferenceTestNode(
            name=(
                f"{ref_node.node.node.func.attrname}.line{ref_node.node.node.func.lineno}"
                if isinstance(ref_node.node.node.func, astroid.Attribute)
                else f"{ref_node.node.node.func.name}.line{ref_node.node.node.func.lineno}"
            ),
            scope=f"{ref_node.scope.symbol.node.__class__.__name__}.{ref_node.scope.symbol.node.name}",
            referenced_symbols=sorted([str(ref) for ref in ref_node.referenced_symbols]),
        )
    if isinstance(ref_node.scope.symbol.node, astroid.ListComp):
        return ReferenceTestNode(
            name=f"{ref_node.node.node.name}.line{ref_node.node.node.lineno}",
            scope=f"{ref_node.scope.symbol.node.__class__.__name__}.",
            referenced_symbols=sorted([str(ref) for ref in ref_node.referenced_symbols]),
        )
    if (
        isinstance(ref_node.node.node, astroid.Name)
        and ref_node.scope.symbol.name == "__init__"
        and isinstance(ref_node.scope.symbol, ClassVariable | InstanceVariable)
        and ref_node.scope.symbol.klass is not None
    ):
        return ReferenceTestNode(
            name=f"{ref_node.node.node.name}.line{ref_node.node.node.lineno}",
            scope=f"{ref_node.scope.symbol.node.__class__.__name__}.{ref_node.scope.symbol.klass.name}.{ref_node.scope.symbol.node.name}",
            # type: ignore[union-attr] # "None" has no attribute "name" but since we check for the type before, this is fine
            referenced_symbols=sorted([str(ref) for ref in ref_node.referenced_symbols]),
        )
    return ReferenceTestNode(
        name=f"{ref_node.node.node.name}.line{ref_node.node.node.lineno}",
        scope=f"{ref_node.scope.symbol.node.__class__.__name__}.{ref_node.scope.symbol.node.name}",
        referenced_symbols=sorted([str(ref) for ref in ref_node.referenced_symbols]),
    )


def transform_reasons(reasons: dict[NodeID, Reasons]) -> dict[str, SimpleReasons]:
    """Transform the function references.

    The function references are transformed to a dictionary with the name of the function as key
    and the transformed Reasons instance as value.

    Parameters
    ----------
    reasons : dict[str, Reasons]
        The function references to transform.

    Returns
    -------
    dict[str, SimpleReasons]
        The transformed function references.
    """
    transformed_function_references = {}
    for function_id, function_references in reasons.items():
        transformed_function_references.update({
            function_id.__str__(): SimpleReasons(
                function_references.function_scope.symbol.name,  # type: ignore[union-attr] # function_scope is not None
                {
                    (
                        f"{target_reference.__class__.__name__}.{target_reference.klass.name}.{target_reference.node.name}.line{target_reference.node.fromlineno}"  # type: ignore[union-attr] # "None" has no attribute "name" but since we check for the type before, this is fine
                        if isinstance(target_reference, ClassVariable) and target_reference.klass is not None
                        else (
                            f"{target_reference.__class__.__name__}.{target_reference.klass.name}.{target_reference.node.member}.line{target_reference.node.node.fromlineno}"  # type: ignore[union-attr] # "None" has no attribute "name" but since we check for the type before, this is fine
                            if isinstance(target_reference, InstanceVariable)
                            else f"{target_reference.__class__.__name__}.{target_reference.node.name}.line{target_reference.node.fromlineno}"
                        )
                    )
                    for target_reference in function_references.writes_to
                },
                {
                    (
                        f"{value_reference.__class__.__name__}.{value_reference.klass.name}.{value_reference.node.name}.line{value_reference.node.fromlineno}"  # type: ignore[union-attr] # "None" has no attribute "name" but since we check for the type before, this is fine
                        if isinstance(value_reference, ClassVariable) and value_reference is not None
                        else (
                            f"{value_reference.__class__.__name__}.{value_reference.klass.name}.{value_reference.node.member}.line{value_reference.node.node.fromlineno}"  # type: ignore[union-attr] # "None" has no attribute "name" but since we check for the type before, this is fine
                            if isinstance(value_reference, InstanceVariable)
                            else f"{value_reference.__class__.__name__}.{value_reference.node.name}.line{value_reference.node.fromlineno}"
                        )
                    )
                    for value_reference in function_references.reads_from
                },
                {
                    (
                        f"{function_reference.__class__.__name__}.{function_reference.node.attrname}.line{function_reference.node.fromlineno}"
                        if isinstance(function_reference.node, astroid.Attribute)
                        else (
                            f"{function_reference.__class__.__name__}.{function_reference.node.name}"
                            if isinstance(
                                function_reference,
                                Builtin,
                            )  # Special case for builtin functions since we do not get their line.
                            else (
                                f"{function_reference.__class__.__name__}.{function_reference.klass.name}.{function_reference.node.name}.line{function_reference.node.fromlineno}"
                                if isinstance(function_reference, ClassVariable)
                                and function_reference.klass is not None
                                else (
                                    f"{function_reference.__class__.__name__}.{function_reference.klass.name}.{function_reference.node.member}.line{function_reference.node.node.fromlineno}"  # type: ignore[union-attr] # "None" has no attribute "name" but since we check for the type before, this is fine
                                    if isinstance(function_reference, InstanceVariable)
                                    and function_reference.klass is not None
                                    else f"{function_reference.__class__.__name__}.{function_reference.node.name}.line{function_reference.node.fromlineno}"
                                )
                            )
                        )
                    )
                    for function_reference in function_references.calls
                },
            ),
        })

    return transformed_function_references


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "Local variable in function scope"
            """
def local_var():
    var1 = 1
    return var1
            """,  # language= None
            [ReferenceTestNode("var1.line4", "FunctionDef.local_var", ["LocalVariable.var1.line3"])],
        ),
        (  # language=Python "Global variable in module scope"
            """
glob1 = 10
glob1
            """,  # language= None
            [],  # TODO: LARS - is there any problem with this not being detected?
        ),
        (  # language=Python "Global variable in class scope"
            """
glob1 = 10
class A:
    global glob1
    glob1
            """,  # language= None
            [],  # TODO: LARS - is there any problem with this not being detected?
        ),
        (  # language=Python "Global variable in function scope"
            """
glob1 = 10
def local_global():
    global glob1

    return glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line6", "FunctionDef.local_global", ["GlobalVariable.glob1.line2"])],
        ),
        (  # language=Python "Global variable in function scope but after definition"
            """
def local_global():
    global glob1

    return glob1

glob1 = 10
            """,  # language= None
            [ReferenceTestNode("glob1.line5", "FunctionDef.local_global", ["GlobalVariable.glob1.line7"])],
        ),
        (  # language=Python "Global variable in class scope and function scope"
            """
glob1 = 10
class A:
    global glob1
    glob1

def local_global():
    global glob1

    return glob1
            """,  # language= None
            [
                # ReferenceTestNode("glob1.line5", "ClassDef.A", ["GlobalVariable.glob1.line2"]), # TODO: LARS - is there any problem with this not being detected?
                ReferenceTestNode("glob1.line10", "FunctionDef.local_global", ["GlobalVariable.glob1.line2"]),
            ],
        ),
        (  # language=Python "Access of global variable without global keyword"
            """
glob1 = 10
def local_global_access():
    return glob1
            """,  # language= None
            [ReferenceTestNode("glob1.line4", "FunctionDef.local_global_access", ["GlobalVariable.glob1.line2"])],
        ),
        (  # language=Python "Local variable in function scope shadowing global variable without global keyword"
            """
glob1 = 10
def local_global_shadow():
    glob1 = 20

    return glob1
            """,  # language= None
            [
                ReferenceTestNode(
                    "glob1.line6",
                    "FunctionDef.local_global_shadow",
                    ["LocalVariable.glob1.line4"],
                ),
            ],
        ),
        (  # language=Python "Two globals in class scope"
            """
glob1 = 10
glob2 = 20
class A:
    global glob1, glob2
    glob1, glob2
            """,  # language= None
            [
                # ReferenceTestNode("glob1.line6", "ClassDef.A", ["GlobalVariable.glob1.line2"]),  # TODO: LARS - is there any problem with this not being detected?
                # ReferenceTestNode("glob2.line6", "ClassDef.A", ["GlobalVariable.glob2.line3"]),
            ],
        ),
        (  # language=Python "New global variable in class scope"
            """
class A:
    global glob1
    glob1 = 10
    glob1
            """,  # language= None
            # [ReferenceTestNode("glob1.line5", "ClassDef.A", ["ClassVariable.A.glob1.line4"])],
            [],  # TODO: LARS - is there any problem with this not being detected?
            # glob1 is not detected as a global variable since it is defined in the class scope - this is intended
        ),
        (  # language=Python "New global variable in function scope"
            """
def local_global():
    global glob1

    return glob1
            """,  # language= None
            [],
            # glob1 is not detected as a global variable since it is defined in the function scope - this is intended
        ),
        (  # language=Python "New global variable in class scope with outer scope usage"
            """
class A:
    global glob1
    value = glob1

def f():
    a = A().value
    glob1 = 10
    b = A().value
    a, b
            """,  # language= None
            [
                ReferenceTestNode("A.line7", "FunctionDef.f", ["GlobalVariable.A.line2"]),
                ReferenceTestNode("A.line9", "FunctionDef.f", ["GlobalVariable.A.line2"]),
                # ReferenceTestNode("glob1.line4", "ClassDef.A", ["GlobalVariable.glob1.line7"]),
                ReferenceTestNode("A.value.line7", "FunctionDef.f", ["ClassVariable.A.value.line4"]),
                ReferenceTestNode("A.value.line9", "FunctionDef.f", ["ClassVariable.A.value.line4"]),
                ReferenceTestNode("a.line10", "FunctionDef.f", ["LocalVariable.a.line7"]),
                ReferenceTestNode("b.line10", "FunctionDef.f", ["LocalVariable.b.line9"]),
            ],
        ),
        (  # language=Python "New global variable in function scope with outer scope usage"
            """
def local_global():
    global glob1
    return glob1

def f():
    lg = local_global()
    glob1 = 10
            """,  # language= None
            [
                ReferenceTestNode("local_global.line7", "FunctionDef.f", ["GlobalVariable.local_global.line2"]),
                # ReferenceTestNode("glob1.line4", "FunctionDef.local_global", ["GlobalVariable.glob1.line7"]),
            ],
        ),  # Problem: we cannot check weather a function is called before the global variable is declared since
        # this would need a context-sensitive approach
        # For now we just check if the global variable is declared in the module scope at the cost of loosing precision.
    ],
    ids=[
        "Local variable in function scope",
        "Global variable in module scope",
        "Global variable in class scope",
        "Global variable in function scope",
        "Global variable in function scope but after definition",
        "Global variable in class scope and function scope",
        "Access of global variable without global keyword",
        "Local variable in function scope shadowing global variable without global keyword",
        "Two globals in class scope",
        "New global variable in class scope",
        "New global variable in function scope",
        "New global variable in class scope with outer scope usage",
        "New global variable in function scope with outer scope usage",
    ],
)
def test_resolve_references_local_global(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code).resolved_references
    transformed_references: list[ReferenceTestNode] = []

    for node in references.values():
        transformed_references.extend(transform_reference_nodes(node))

    # assert references == expected
    assert transformed_references == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "Parameter in function scope"
            """
def local_parameter(pos_arg):
    return 2 * pos_arg
            """,  # language= None
            [ReferenceTestNode("pos_arg.line3", "FunctionDef.local_parameter", ["Parameter.pos_arg.line2"])],
        ),
        (  # language=Python "Parameter in function scope with keyword only"
            """
def local_parameter(*, key_arg_only):
    return 2 * key_arg_only
            """,  # language= None
            [ReferenceTestNode("key_arg_only.line3", "FunctionDef.local_parameter", ["Parameter.key_arg_only.line2"])],
        ),
        (  # language=Python "Parameter in function scope with positional only"
            """
def local_parameter(pos_arg_only, /):
    return 2 * pos_arg_only
            """,  # language= None
            [ReferenceTestNode("pos_arg_only.line3", "FunctionDef.local_parameter", ["Parameter.pos_arg_only.line2"])],
        ),
        (  # language=Python "Parameter in function scope with default value"
            """
def local_parameter(def_arg=10):
    return def_arg
            """,  # language= None
            [ReferenceTestNode("def_arg.line3", "FunctionDef.local_parameter", ["Parameter.def_arg.line2"])],
        ),
        (  # language=Python "Parameter in function scope with type annotation"
            """
def local_parameter(def_arg: int):
    return def_arg
            """,  # language= None
            [ReferenceTestNode("def_arg.line3", "FunctionDef.local_parameter", ["Parameter.def_arg.line2"])],
        ),
        (  # language=Python "Parameter in function scope with *args"
            """
def local_parameter(*args):
    return args
            """,  # language= None
            [ReferenceTestNode("args.line3", "FunctionDef.local_parameter", ["Parameter.args.line2"])],
        ),
        (  # language=Python "Parameter in function scope with **kwargs"
            """
def local_parameter(**kwargs):
    return kwargs
            """,  # language= None
            [ReferenceTestNode("kwargs.line3", "FunctionDef.local_parameter", ["Parameter.kwargs.line2"])],
        ),
        (  # language=Python "Parameter in function scope with *args and **kwargs"
            """
def local_parameter(*args, **kwargs):
    return args, kwargs
            """,  # language= None
            [
                ReferenceTestNode("args.line3", "FunctionDef.local_parameter", ["Parameter.args.line2"]),
                ReferenceTestNode("kwargs.line3", "FunctionDef.local_parameter", ["Parameter.kwargs.line2"]),
            ],
        ),
        (  # language=Python "Two parameters in function scope"
            """
def local_double_parameter(a, b):
    return a, b
            """,  # language= None
            [
                ReferenceTestNode("a.line3", "FunctionDef.local_double_parameter", ["Parameter.a.line2"]),
                ReferenceTestNode("b.line3", "FunctionDef.local_double_parameter", ["Parameter.b.line2"]),
            ],
        ),
        (  # language=Python "Self"
            """
class A:
    def __init__(self):
        self

    def f(self):
        x = self
            """,  # language= None
            [
                ReferenceTestNode("self.line4", "FunctionDef.A.__init__", ["Parameter.self.line3"]),
                ReferenceTestNode("self.line7", "FunctionDef.f", ["Parameter.self.line6"]),
            ],
        ),
    ],
    ids=[
        "Parameter in function scope",
        "Parameter in function scope with keyword only",
        "Parameter in function scope with positional only",
        "Parameter in function scope with default value",
        "Parameter in function scope with type annotation",
        "Parameter in function scope with *args",
        "Parameter in function scope with **kwargs",
        "Parameter in function scope with *args and **kwargs",
        "Two parameters in function scope",
        "Self",
    ],
)
def test_resolve_references_parameters(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code).resolved_references
    transformed_references: list[ReferenceTestNode] = []

    for node in references.values():
        transformed_references.extend(transform_reference_nodes(node))

    # assert references == expected
    assert set(transformed_references) == set(expected)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "Class attribute value"
            """
class A:
    class_attr1 = 20

def f():
    A.class_attr1
    A
            """,  # language=none
            [
                ReferenceTestNode("A.class_attr1.line6", "FunctionDef.f", ["ClassVariable.A.class_attr1.line3"]),
                ReferenceTestNode("A.line6", "FunctionDef.f", ["GlobalVariable.A.line2"]),
                ReferenceTestNode("A.line7", "FunctionDef.f", ["GlobalVariable.A.line2"]),
            ],
        ),
        (  # language=Python "Class attribute target"
            """
class A:
    class_attr1 = 20

def f():
    A.class_attr1 = 30
    A.class_attr1
            """,  # language=none
            [
                ReferenceTestNode(
                    "A.class_attr1.line7",
                    "FunctionDef.f",
                    ["ClassVariable.A.class_attr1.line3", "ClassVariable.A.class_attr1.line6"],
                ),
                ReferenceTestNode("A.line7", "FunctionDef.f", ["GlobalVariable.A.line2"]),
                ReferenceTestNode("A.class_attr1.line6", "FunctionDef.f", ["ClassVariable.A.class_attr1.line3"]),
                ReferenceTestNode("A.line6", "FunctionDef.f", ["GlobalVariable.A.line2"]),
            ],
        ),
        (  # language=Python "Class attribute multiple usage"
            """
class A:
    class_attr1 = 20

def f():
    a = A().class_attr1
    b = A().class_attr1
    c = A().class_attr1
            """,  # language=none
            [
                ReferenceTestNode("A.class_attr1.line6", "FunctionDef.f", ["ClassVariable.A.class_attr1.line3"]),
                ReferenceTestNode("A.class_attr1.line7", "FunctionDef.f", ["ClassVariable.A.class_attr1.line3"]),
                ReferenceTestNode("A.class_attr1.line8", "FunctionDef.f", ["ClassVariable.A.class_attr1.line3"]),
                ReferenceTestNode("A.line6", "FunctionDef.f", ["GlobalVariable.A.line2"]),
                ReferenceTestNode("A.line7", "FunctionDef.f", ["GlobalVariable.A.line2"]),
                ReferenceTestNode("A.line8", "FunctionDef.f", ["GlobalVariable.A.line2"]),
            ],
        ),
        (  # language=Python "Chained class attribute"
            """
class A:
    class_attr1 = 20

class B:
    upper_class: A = A

def f():
    b = B()
    x = b.upper_class.class_attr1
            """,  # language=none
            [
                ReferenceTestNode(
                    "UNKNOWN.class_attr1.line10",
                    "FunctionDef.f",
                    # we do not analyze the target of the member access, hence the name does not matter.
                    ["ClassVariable.A.class_attr1.line3"],
                ),
                ReferenceTestNode("b.upper_class.line10", "FunctionDef.f", ["ClassVariable.B.upper_class.line6"]),
                ReferenceTestNode("b.line10", "FunctionDef.f", ["LocalVariable.b.line9"]),
                ReferenceTestNode("B.line9", "FunctionDef.f", ["GlobalVariable.B.line5"]),
            ],
        ),
        (  # language=Python "Instance attribute value"
            """
class B:
    def __init__(self):
        self.instance_attr1 : int = 10

def f():
    b = B()
    var1 = b.instance_attr1
            """,  # language=none
            [
                ReferenceTestNode(
                    "b.instance_attr1.line8",
                    "FunctionDef.f",
                    ["InstanceVariable.B.instance_attr1.line4"],
                ),
                ReferenceTestNode("b.line8", "FunctionDef.f", ["LocalVariable.b.line7"]),
                ReferenceTestNode("self.line4", "FunctionDef.B.__init__", ["Parameter.self.line3"]),
                ReferenceTestNode("B.line7", "FunctionDef.f", ["GlobalVariable.B.line2"]),
            ],
        ),
        (  # language=Python "Instance attribute target"
            """
class B:
    def __init__(self):
        self.instance_attr1 = 10

def f():
    b = B()
    b.instance_attr1 = 1
    b.instance_attr1
            """,  # language=none
            [
                ReferenceTestNode(
                    "b.instance_attr1.line9",
                    "FunctionDef.f",
                    ["InstanceVariable.B.instance_attr1.line4", "InstanceVariable.B.instance_attr1.line8"],
                ),
                ReferenceTestNode("b.line9", "FunctionDef.f", ["LocalVariable.b.line7"]),
                ReferenceTestNode("self.line4", "FunctionDef.B.__init__", ["Parameter.self.line3"]),
                ReferenceTestNode(
                    "b.instance_attr1.line8",
                    "FunctionDef.f",
                    ["InstanceVariable.B.instance_attr1.line4"],
                ),
                ReferenceTestNode("b.line8", "FunctionDef.f", ["LocalVariable.b.line7"]),
                ReferenceTestNode("B.line7", "FunctionDef.f", ["GlobalVariable.B.line2"]),
            ],
        ),
        (  # language=Python "Instance attribute with parameter"
            """
class B:
    def __init__(self, name: str):
        self.name = name

def f():
    b = B("test")
    b.name
            """,  # language=none
            [
                ReferenceTestNode("name.line4", "FunctionDef.B.__init__", ["Parameter.name.line3"]),
                ReferenceTestNode("b.name.line8", "FunctionDef.f", ["InstanceVariable.B.name.line4"]),
                ReferenceTestNode("b.line8", "FunctionDef.f", ["LocalVariable.b.line7"]),
                ReferenceTestNode("self.line4", "FunctionDef.B.__init__", ["Parameter.self.line3"]),
                ReferenceTestNode("B.line7", "FunctionDef.f", ["GlobalVariable.B.line2"]),
            ],
        ),
        (  # language=Python "Instance attribute with parameter and class attribute"
            """
class X:
    class_attr = 10

    def __init__(self, name: str):
        self.name = name

def f():
    x = X("test")
    x.name
    x.class_attr
            """,  # language=none
            [
                ReferenceTestNode("name.line6", "FunctionDef.X.__init__", ["Parameter.name.line5"]),
                ReferenceTestNode("x.name.line10", "FunctionDef.f", ["InstanceVariable.X.name.line6"]),
                ReferenceTestNode("x.line10", "FunctionDef.f", ["LocalVariable.x.line9"]),
                ReferenceTestNode("x.class_attr.line11", "FunctionDef.f", ["ClassVariable.X.class_attr.line3"]),
                ReferenceTestNode("x.line11", "FunctionDef.f", ["LocalVariable.x.line9"]),
                ReferenceTestNode("self.line6", "FunctionDef.X.__init__", ["Parameter.self.line5"]),
                ReferenceTestNode("X.line9", "FunctionDef.f", ["GlobalVariable.X.line2"]),
            ],
        ),
        (  # language=Python "Class attribute initialized with instance attribute"
            """
class B:
    instance_attr1: int

    def __init__(self):
        self.instance_attr1 = 10

def f():
    b = B()
    var1 = b.instance_attr1
            """,  # language=none
            [
                ReferenceTestNode(
                    "b.instance_attr1.line10",
                    "FunctionDef.f",
                    ["ClassVariable.B.instance_attr1.line3", "InstanceVariable.B.instance_attr1.line6"],
                ),
                ReferenceTestNode("b.line10", "FunctionDef.f", ["LocalVariable.b.line9"]),
                ReferenceTestNode(
                    "self.instance_attr1.line6",
                    "FunctionDef.B.__init__",
                    ["ClassVariable.B.instance_attr1.line3"],
                ),
                ReferenceTestNode("self.line6", "FunctionDef.B.__init__", ["Parameter.self.line5"]),
                ReferenceTestNode("B.line9", "FunctionDef.f", ["GlobalVariable.B.line2"]),
            ],
        ),
        (  # language=Python "Chained class attribute and instance attribute"
            """
class A:
    def __init__(self):
        self.name = 10

class B:
    upper_class: A = A()

def f():
    b = B()
    x = b.upper_class.name
            """,  # language=none
            [
                ReferenceTestNode("UNKNOWN.name.line11", "FunctionDef.f", ["InstanceVariable.A.name.line4"]),
                # we do not analyze the target of the member access, hence the name does not matter.
                ReferenceTestNode("b.upper_class.line11", "FunctionDef.f", ["ClassVariable.B.upper_class.line7"]),
                ReferenceTestNode("b.line11", "FunctionDef.f", ["LocalVariable.b.line10"]),
                ReferenceTestNode("self.line4", "FunctionDef.A.__init__", ["Parameter.self.line3"]),
                ReferenceTestNode("B.line10", "FunctionDef.f", ["GlobalVariable.B.line6"]),
            ],
        ),
        (  # language=Python "Chained instance attributes value"
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

def f():
    a = A()
    a.b.c.name
            """,  # language=none
            [
                ReferenceTestNode("UNKNOWN.name.line16", "FunctionDef.f", ["InstanceVariable.C.name.line12"]),
                # we do not analyze the target of the member access, hence the name does not matter.
                ReferenceTestNode("UNKNOWN.c.line16", "FunctionDef.f", ["InstanceVariable.B.c.line8"]),
                # we do not analyze the target of the member access, hence the name does not matter.
                ReferenceTestNode("a.b.line16", "FunctionDef.f", ["InstanceVariable.A.b.line4"]),
                ReferenceTestNode("a.line16", "FunctionDef.f", ["LocalVariable.a.line15"]),
                ReferenceTestNode("self.line4", "FunctionDef.A.__init__", ["Parameter.self.line3"]),
                ReferenceTestNode("self.line8", "FunctionDef.B.__init__", ["Parameter.self.line7"]),
                ReferenceTestNode("self.line12", "FunctionDef.C.__init__", ["Parameter.self.line11"]),
                ReferenceTestNode("B.line4", "FunctionDef.A.__init__", ["GlobalVariable.B.line6"]),
                ReferenceTestNode("C.line8", "FunctionDef.B.__init__", ["GlobalVariable.C.line10"]),
                ReferenceTestNode("A.line15", "FunctionDef.f", ["GlobalVariable.A.line2"]),
            ],
        ),
        (  # language=Python "Chained instance attributes target"
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

def f():
    a = A()
    a.b.c.name = "test"
            """,  # language=none
            [
                ReferenceTestNode("self.line4", "FunctionDef.A.__init__", ["Parameter.self.line3"]),
                ReferenceTestNode("self.line8", "FunctionDef.B.__init__", ["Parameter.self.line7"]),
                ReferenceTestNode("self.line12", "FunctionDef.C.__init__", ["Parameter.self.line11"]),
                ReferenceTestNode("UNKNOWN.name.line16", "FunctionDef.f", ["InstanceVariable.C.name.line12"]),
                ReferenceTestNode("UNKNOWN.c.line16", "FunctionDef.f", ["InstanceVariable.B.c.line8"]),
                ReferenceTestNode("a.line16", "FunctionDef.f", ["LocalVariable.a.line15"]),
                ReferenceTestNode("a.b.line16", "FunctionDef.f", ["InstanceVariable.A.b.line4"]),
                ReferenceTestNode("B.line4", "FunctionDef.A.__init__", ["GlobalVariable.B.line6"]),
                ReferenceTestNode("C.line8", "FunctionDef.B.__init__", ["GlobalVariable.C.line10"]),
                ReferenceTestNode("A.line15", "FunctionDef.f", ["GlobalVariable.A.line2"]),
            ],
        ),
        (  # language=Python "Two classes with the same signature"
            """
class A:
    name: str = ""

    def __init__(self, name: str):
        self.name = name

class B:
    name: str = ""

    def __init__(self, name: str):
        self.name = name

def f():
    a = A("value")
    b = B("test")
    a.name
    b.name
            """,  # language=none
            [
                ReferenceTestNode("name.line6", "FunctionDef.A.__init__", ["Parameter.name.line5"]),
                ReferenceTestNode("name.line12", "FunctionDef.B.__init__", ["Parameter.name.line11"]),
                ReferenceTestNode(
                    "a.name.line17",
                    "FunctionDef.f",
                    [
                        "ClassVariable.A.name.line3",  # class A
                        "ClassVariable.B.name.line9",  # class B
                        "InstanceVariable.A.name.line6",  # class A
                        "InstanceVariable.B.name.line12",  # class B
                    ],
                ),
                ReferenceTestNode("a.line17", "FunctionDef.f", ["LocalVariable.a.line15"]),
                ReferenceTestNode(
                    "b.name.line18",
                    "FunctionDef.f",
                    [
                        "ClassVariable.A.name.line3",  # class A
                        "ClassVariable.B.name.line9",  # class B
                        "InstanceVariable.A.name.line6",  # class A
                        "InstanceVariable.B.name.line12",  # class B
                    ],
                ),
                ReferenceTestNode("b.line18", "FunctionDef.f", ["LocalVariable.b.line16"]),
                ReferenceTestNode("self.name.line6", "FunctionDef.A.__init__", ["ClassVariable.A.name.line3"]),
                ReferenceTestNode("self.line6", "FunctionDef.A.__init__", ["Parameter.self.line5"]),
                ReferenceTestNode("self.name.line12", "FunctionDef.B.__init__", ["ClassVariable.B.name.line9"]),
                ReferenceTestNode("self.line12", "FunctionDef.B.__init__", ["Parameter.self.line11"]),
                ReferenceTestNode("A.line15", "FunctionDef.f", ["GlobalVariable.A.line2"]),
                ReferenceTestNode("B.line16", "FunctionDef.f", ["GlobalVariable.B.line8"]),
            ],
        ),
        (  # language=Python "Getter function with self"
            """
class C:
    state: int = 0

    def get_state(self):
        return self.state
            """,  # language= None
            [
                ReferenceTestNode("self.state.line6", "FunctionDef.get_state", ["ClassVariable.C.state.line3"]),
                ReferenceTestNode("self.line6", "FunctionDef.get_state", ["Parameter.self.line5"]),
            ],
        ),
        (  # language=Python "Getter function with classname"
            """
class C:
    state: int = 0

    @staticmethod
    def get_state():
        return C.state
            """,  # language= None
            [
                ReferenceTestNode("C.state.line7", "FunctionDef.get_state", ["ClassVariable.C.state.line3"]),
                ReferenceTestNode("C.line7", "FunctionDef.get_state", ["GlobalVariable.C.line2"]),
            ],
        ),
        (  # language=Python "Setter function with self"
            """
class C:
    state: int = 0

    def set_state(self, state):
        self.state = state
            """,  # language= None
            [
                ReferenceTestNode("state.line6", "FunctionDef.set_state", ["Parameter.state.line5"]),
                ReferenceTestNode("self.state.line6", "FunctionDef.set_state", ["ClassVariable.C.state.line3"]),
                ReferenceTestNode("self.line6", "FunctionDef.set_state", ["Parameter.self.line5"]),
            ],
        ),
        (  # language=Python "Setter function with self different name"
            """
class A:
    stateX: str = "A"

class C:
    stateX: int = 0

    def set_state(self, state):
        self.stateX = state
            """,  # language= None
            [
                ReferenceTestNode("state.line9", "FunctionDef.set_state", ["Parameter.state.line8"]),
                ReferenceTestNode(
                    "self.stateX.line9",
                    "FunctionDef.set_state",
                    ["ClassVariable.C.stateX.line6"],
                ),  # here self indicates that we are in class C -> therefore only C.stateX is detected
                ReferenceTestNode("self.line9", "FunctionDef.set_state", ["Parameter.self.line8"]),
            ],
        ),
        (  # language=Python "Setter function with classname different name"
            """
class C:
    stateX: int = 0

    @staticmethod
    def set_state(state):
        C.stateX = state
            """,  # language= None
            [
                ReferenceTestNode("state.line7", "FunctionDef.set_state", ["Parameter.state.line6"]),
                ReferenceTestNode("C.stateX.line7", "FunctionDef.set_state", ["ClassVariable.C.stateX.line3"]),
                ReferenceTestNode("C.line7", "FunctionDef.set_state", ["GlobalVariable.C.line2"]),
            ],
        ),
        (  # language=Python "Setter function as @staticmethod"
            """
class A:
    state: str = "A"

class C:
    state: int = 0

    @staticmethod
    def set_state(node, state):
        node.state = state
            """,  # language= None
            [
                ReferenceTestNode("state.line10", "FunctionDef.set_state", ["Parameter.state.line9"]),
                ReferenceTestNode(
                    "node.state.line10",
                    "FunctionDef.set_state",
                    ["ClassVariable.A.state.line3", "ClassVariable.C.state.line6"],
                ),
                ReferenceTestNode("node.line10", "FunctionDef.set_state", ["Parameter.node.line9"]),
            ],
        ),
        (  # language=Python "Setter function as @classmethod"
            """
class A:
    state: str = "A"

class C:
    state: int = 0

    @classmethod
    def set_state(cls, state):
        cls.state = state
            """,  # language= None
            [
                ReferenceTestNode("state.line10", "FunctionDef.set_state", ["Parameter.state.line9"]),
                ReferenceTestNode(
                    "cls.state.line10",
                    "FunctionDef.set_state",
                    ["ClassVariable.A.state.line3", "ClassVariable.C.state.line6"],
                    # TODO: [LATER] A.state should be removed!
                ),
                ReferenceTestNode("cls.line10", "FunctionDef.set_state", ["Parameter.cls.line9"]),
            ],
        ),
        (  # language=Python "Class call - init",
            """
class A:
    pass

def fun():
    a = A()

            """,  # language=none
            [
                ReferenceTestNode("A.line6", "FunctionDef.fun", ["GlobalVariable.A.line2"]),
            ],
        ),
        (  # language=Python "Member access - class",
            """
class A:
    class_attr1 = 20

def fun():
    a = A().class_attr1

            """,  # language=none
            [
                ReferenceTestNode("A.line6", "FunctionDef.fun", ["GlobalVariable.A.line2"]),
                ReferenceTestNode("A.class_attr1.line6", "FunctionDef.fun", ["ClassVariable.A.class_attr1.line3"]),
            ],
        ),
        (  # language=Python "Member access - class without init",
            """
class A:
    class_attr1 = 20

def fun():
    a = A.class_attr1

            """,  # language=none
            [
                ReferenceTestNode("A.line6", "FunctionDef.fun", ["GlobalVariable.A.line2"]),
                ReferenceTestNode("A.class_attr1.line6", "FunctionDef.fun", ["ClassVariable.A.class_attr1.line3"]),
            ],
        ),
        (  # language=Python "Member access - methode",
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
            [
                ReferenceTestNode("A.line9", "FunctionDef.fun1", ["GlobalVariable.A.line2"]),
                ReferenceTestNode("a.line10", "FunctionDef.fun1", ["LocalVariable.a.line9"]),
                ReferenceTestNode("g.line10", "FunctionDef.fun1", ["ClassVariable.A.g.line5"]),
                ReferenceTestNode("A.line13", "FunctionDef.fun2", ["GlobalVariable.A.line2"]),
                ReferenceTestNode("g.line13", "FunctionDef.fun2", ["ClassVariable.A.g.line5"]),
            ],
        ),
        (  # language=Python "Member access - init",
            """
class A:
    def __init__(self):
        pass

def fun():
    a = A()

            """,  # language=none
            [
                ReferenceTestNode("A.line7", "FunctionDef.fun", ["GlobalVariable.A.line2"]),
            ],
        ),
        (  # language=Python "Member access - instance function",
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
            [
                ReferenceTestNode("self.line4", "FunctionDef.A.__init__", ["Parameter.self.line3"]),
                ReferenceTestNode("B.line4", "FunctionDef.A.__init__", ["GlobalVariable.B.line6"]),
                ReferenceTestNode("A.line14", "FunctionDef.fun1", ["GlobalVariable.A.line2"]),
                ReferenceTestNode("a.line15", "FunctionDef.fun1", ["LocalVariable.a.line14"]),
                ReferenceTestNode("a.a_inst.line15", "FunctionDef.fun1", ["InstanceVariable.A.a_inst.line4"]),
                ReferenceTestNode("b_fun.line15", "FunctionDef.fun1", ["ClassVariable.B.b_fun.line10"]),
                ReferenceTestNode("A.line18", "FunctionDef.fun2", ["GlobalVariable.A.line2"]),
                ReferenceTestNode("A.a_inst.line18", "FunctionDef.fun2", ["InstanceVariable.A.a_inst.line4"]),
                ReferenceTestNode("b_fun.line18", "FunctionDef.fun2", ["ClassVariable.B.b_fun.line10"]),
            ],
        ),
        (  # language=Python "Member access - function call of functions with same name"
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
            [
                ReferenceTestNode("a.line5", "FunctionDef.add", ["Parameter.a.line4"]),
                ReferenceTestNode("b.line5", "FunctionDef.add", ["Parameter.b.line4"]),
                ReferenceTestNode("a.line10", "FunctionDef.add", ["Parameter.a.line9"]),
                ReferenceTestNode("b.line10", "FunctionDef.add", ["Parameter.b.line9"]),
                ReferenceTestNode("A.line13", "FunctionDef.fun_a", ["GlobalVariable.A.line2"]),
                ReferenceTestNode("x.line14", "FunctionDef.fun_a", ["LocalVariable.x.line13"]),
                ReferenceTestNode(
                    "add.line14",
                    "FunctionDef.fun_a",
                    ["ClassVariable.A.add.line4", "ClassVariable.B.add.line9"],
                ),
                ReferenceTestNode("B.line17", "FunctionDef.fun_b", ["GlobalVariable.B.line7"]),
                ReferenceTestNode("x.line18", "FunctionDef.fun_b", ["LocalVariable.x.line17"]),
                ReferenceTestNode(
                    "add.line18",
                    "FunctionDef.fun_b",
                    ["ClassVariable.A.add.line4", "ClassVariable.B.add.line9"],
                ),
            ],
        ),
        (  # language=Python "Member access - function call of functions with same name and nested calls",
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
            [
                ReferenceTestNode("print.line6", "FunctionDef.fun2", ["Builtin.print"]),
                ReferenceTestNode("a.line12", "FunctionDef.add", ["Parameter.a.line10"]),
                ReferenceTestNode("b.line12", "FunctionDef.add", ["Parameter.b.line10"]),
                ReferenceTestNode("fun1.line11", "FunctionDef.add", ["GlobalVariable.fun1.line2"]),
                ReferenceTestNode("a.line18", "FunctionDef.add", ["Parameter.a.line16"]),
                ReferenceTestNode("b.line18", "FunctionDef.add", ["Parameter.b.line16"]),
                ReferenceTestNode("fun2.line17", "FunctionDef.add", ["GlobalVariable.fun2.line5"]),
            ],
        ),
        (  # language=Python "Member access - function call of functions with same name (no distinction possible)"
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
            [
                ReferenceTestNode("a.line13", "FunctionDef.fun_out", ["Parameter.a.line12"]),
                ReferenceTestNode("A.line14", "FunctionDef.fun_out", ["GlobalVariable.A.line2"]),
                ReferenceTestNode("B.line16", "FunctionDef.fun_out", ["GlobalVariable.B.line7"]),
                ReferenceTestNode("x.line16", "FunctionDef.fun_out", ["LocalVariable.x.line14"]),
                # this is an assumption we need to make since we cannot differentiate between branches before runtime
                ReferenceTestNode(
                    "x.line17",
                    "FunctionDef.fun_out",
                    ["LocalVariable.x.line14", "LocalVariable.x.line16"],
                ),
                ReferenceTestNode(
                    "fun.line17",
                    "FunctionDef.fun_out",
                    ["ClassVariable.A.fun.line4", "ClassVariable.B.fun.line9"],
                ),
                # here we can't distinguish between the two functions
            ],
        ),
        (  # language=Python "Member access - function call of functions with same name (different signatures)"
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
            [
                ReferenceTestNode("a.line5", "FunctionDef.add", ["Parameter.a.line4"]),
                ReferenceTestNode("b.line5", "FunctionDef.add", ["Parameter.b.line4"]),
                ReferenceTestNode("a.line10", "FunctionDef.add", ["Parameter.a.line9"]),
                ReferenceTestNode("b.line10", "FunctionDef.add", ["Parameter.b.line9"]),
                ReferenceTestNode("c.line10", "FunctionDef.add", ["Parameter.c.line9"]),
                ReferenceTestNode("A.line13", "FunctionDef.fun", ["GlobalVariable.A.line2"]),
                ReferenceTestNode(
                    "add.line13",
                    "FunctionDef.fun",
                    ["ClassVariable.A.add.line4", "ClassVariable.B.add.line9"],
                ),
                ReferenceTestNode("B.line14", "FunctionDef.fun", ["GlobalVariable.B.line7"]),
                ReferenceTestNode(
                    "add.line14",
                    "FunctionDef.fun",
                    ["ClassVariable.A.add.line4", "ClassVariable.B.add.line9"],
                ),
            ],
        ),
        # TODO: [Later] we could add a check for the number of parameters in the function call and the function definition
        #         (  # language=Python "Builtins for dict"
        #             """
        # def f():
        #     dictionary = {"a": 1, "b": 2, "c": 3}
        #
        #     dictionary["a"] = 10
        #     dictionary.get("a")
        #     dictionary.update({"d": 4})
        #     dictionary.pop("a")
        #     dictionary.popitem()
        #     dictionary.clear()
        #     dictionary.copy()
        #     dictionary.fromkeys("a")
        #     dictionary.items()
        #     dictionary.keys()
        #     dictionary.values()
        #     dictionary.setdefault("a", 10)
        #
        #     dictionary.__contains__("a")
        #             """,  # language=none
        #             [
        #
        #             ]
        #         ),
        #         (  # language=Python "Builtins for list"
        #             """
        # def f():
        #     list1 = [1, 2, 3]
        #     list2 = [4, 5, 6]
        #
        #     list1.append(4)
        #     list1.clear()
        #     list1.copy()
        #     list1.count(1)
        #     list1.extend(list2)
        #     list1.index(1)
        #     list1.insert(1, 10)
        #     list1.pop()
        #     list1.remove(1)
        #     list1.reverse()
        #     list1.sort()
        #
        #     list1.__contains__(1)
        #             """,  # language=none
        #             [
        #
        #             ]
        #         ),
        #         (  # language=Python "Builtins for set"
        #             """
        # def f():
        #
        #             """,  # language=none
        #             [
        #
        #             ]
        #         ),
    ],
    ids=[
        "Class attribute value",
        "Class attribute target",
        "Class attribute multiple usage",
        "Chained class attribute",
        "Instance attribute value",
        "Instance attribute target",
        "Instance attribute with parameter",
        "Instance attribute with parameter and class attribute",
        "Class attribute initialized with instance attribute",
        "Chained class attribute and instance attribute",
        "Chained instance attributes value",
        "Chained instance attributes target",
        "Two classes with the same signature",
        "Getter function with self",
        "Getter function with classname",
        "Setter function with self",
        "Setter function with self different name",
        "Setter function with classname different name",
        "Setter function as @staticmethod",
        "Setter function as @classmethod",
        "Class call - init",
        "Member access - class",
        "Member access - class without init",
        "Member access - methode",
        "Member access - init",
        "Member access - instance function",
        "Member access - function call of functions with the same name",
        "Member access - function call of functions with the same name and nested calls",
        "Member access - function call of functions with the same name (no distinction possible)",
        "Member access - function call of functions with the same name (different signatures)",
        # "Builtins for dict",  # TODO: We will only implement these special cases if they are needed
        # "Builtins for list",
        # "Builtins for set",
    ],
)
def test_resolve_references_member_access(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code).resolved_references
    transformed_references: list[ReferenceTestNode] = []

    for node in references.values():
        transformed_references.extend(transform_reference_nodes(node))

    # assert references == expected
    assert set(transformed_references) == set(expected)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "If statement"
            """
def f():
    var1 = 10
    if var1 > 0:
        var1
        """,  # language=none
            [
                ReferenceTestNode("var1.line4", "FunctionDef.f", ["LocalVariable.var1.line3"]),
                ReferenceTestNode("var1.line5", "FunctionDef.f", ["LocalVariable.var1.line3"]),
            ],
        ),
        (  # language=Python "If in statement"
            """
def f():
    var1 = [1, 2, 3]
    if 1 in var1:
        var1
        """,  # language=none
            [
                ReferenceTestNode("var1.line4", "FunctionDef.f", ["LocalVariable.var1.line3"]),
                ReferenceTestNode("var1.line5", "FunctionDef.f", ["LocalVariable.var1.line3"]),
            ],
        ),
        (  # language=Python "If else statement"
            """
def f():
    var1 = 10
    if var1 > 0:
        var1
    else:
        2 * var1
        """,  # language=none
            [
                ReferenceTestNode("var1.line4", "FunctionDef.f", ["LocalVariable.var1.line3"]),
                ReferenceTestNode("var1.line5", "FunctionDef.f", ["LocalVariable.var1.line3"]),
                ReferenceTestNode("var1.line7", "FunctionDef.f", ["LocalVariable.var1.line3"]),
            ],
        ),
        (  # language=Python "If elif else statement"
            """
def f():
    var1 = 10
    if var1 > 0:
        var1
    elif var1 < 0:
        -var1
    else:
        var1
        """,  # language=none
            [
                ReferenceTestNode("var1.line4", "FunctionDef.f", ["LocalVariable.var1.line3"]),
                ReferenceTestNode("var1.line5", "FunctionDef.f", ["LocalVariable.var1.line3"]),
                ReferenceTestNode("var1.line6", "FunctionDef.f", ["LocalVariable.var1.line3"]),
                ReferenceTestNode("var1.line7", "FunctionDef.f", ["LocalVariable.var1.line3"]),
                ReferenceTestNode("var1.line9", "FunctionDef.f", ["LocalVariable.var1.line3"]),
            ],
        ),
        (  # language=Python "Ternary operator"
            """
def f():
    var1 = 10
    result = "even" if var1 % 2 == 0 else "odd"
        """,  # language=none
            [
                ReferenceTestNode("var1.line4", "FunctionDef.f", ["LocalVariable.var1.line3"]),
            ],
        ),
        #         (  # language=Python "match statement global scope"
        #             """
        # var1, var2 = 10, 20
        # match var1:
        #     case 1: var1
        #     case 2: 2 * var1
        #     case (a, b): var1, a, b  # TODO: Match should get its own scope (LATER: for further improvement)  maybe add its parent
        #     case _: var2
        #         """,  # language=none
        #             [ReferenceTestNode("var1.line3", "Module.", ["GlobalVariable.var1.line2"]),
        #              ReferenceTestNode("var1.line4", "Module.", ["GlobalVariable.var1.line2"]),
        #              ReferenceTestNode("var1.line5", "Module.", ["GlobalVariable.var1.line2"]),
        #              ReferenceTestNode("var1.line6", "Module.", ["GlobalVariable.var1.line2"]),
        #              ReferenceTestNode("var2.line7", "Module.", ["GlobalVariable.var2.line2"]),
        #              ReferenceTestNode("a.line6", "Module.", ["GlobalVariable.a.line6"]),  # TODO: ask Lars
        #              ReferenceTestNode("b.line6", "Module.", ["GlobalVariable.b.line6"])]
        #             # TODO: ask Lars if this is true GlobalVariable
        #         ),
        #         (  # language=Python "try except statement global scope"
        #             """
        # num1 = 2
        # num2 = 0
        # try:
        #     result = num1 / num2
        #     result
        # except ZeroDivisionError as zde:   # TODO: zde is not detected as a global variable -> do we really want that?
        #     zde
        #         """,  # language=none
        #             [ReferenceTestNode("num1.line5", "Module.", ["GlobalVariable.num1.line2"]),
        #              ReferenceTestNode("num2.line5", "Module.", ["GlobalVariable.num2.line3"]),
        #              ReferenceTestNode("result.line6", "Module.", ["GlobalVariable.result.line5"]),
        #              ReferenceTestNode("zde.line8", "Module.", ["GlobalVariable.zde.line7"])]
        #         ),
    ],
    ids=[
        "If statement",
        "If in statement",
        "If else statement global scope",
        "If elif else statement global scope",
        "Ternary operator",
        # "match statement global scope",
        # "try except statement global scope",
    ],  # TODO: add cases with try except finally -> first check scope detection
)
def test_resolve_references_conditional_statements(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code).resolved_references
    transformed_references: list[ReferenceTestNode] = []

    for node in references.values():
        transformed_references.extend(transform_reference_nodes(node))

    # assert references == expected
    assert set(transformed_references) == set(expected)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "For loop with global runtime variable"
            """
var1 = 10
def f():
    for i in range(var1):
        i
            """,  # language=none
            [
                ReferenceTestNode("range.line4", "FunctionDef.f", ["Builtin.range"]),
                ReferenceTestNode("var1.line4", "FunctionDef.f", ["GlobalVariable.var1.line2"]),
                ReferenceTestNode("i.line5", "FunctionDef.f", ["LocalVariable.i.line4"]),
            ],
        ),
        (  # language=Python "For loop wih local runtime variable"
            """
def f():
    var1 = 10
    for i in range(var1):
        i
            """,  # language=none
            [
                ReferenceTestNode("range.line4", "FunctionDef.f", ["Builtin.range"]),
                ReferenceTestNode("var1.line4", "FunctionDef.f", ["LocalVariable.var1.line3"]),
                ReferenceTestNode("i.line5", "FunctionDef.f", ["LocalVariable.i.line4"]),
            ],
        ),
        (  # language=Python "For loop in list comprehension"
            """
nums = ["one", "two", "three"]
def f():
    lengths = [len(num) for num in nums]
    lengths
            """,  # language=none
            [
                ReferenceTestNode("len.line4", "FunctionDef.f", ["Builtin.len"]),
                # ReferenceTestNode("num.line4", "ListComp.", ["LocalVariable.num.line4"]),
                ReferenceTestNode("nums.line4", "FunctionDef.f", ["GlobalVariable.nums.line2"]),
                ReferenceTestNode("lengths.line5", "FunctionDef.f", ["LocalVariable.lengths.line4"]),
            ],
        ),
        (  # language=Python "While loop"
            """
def f():
    var1 = 10
    while var1 > 0:
        var1
            """,  # language=none
            [
                ReferenceTestNode("var1.line4", "FunctionDef.f", ["LocalVariable.var1.line3"]),
                ReferenceTestNode("var1.line5", "FunctionDef.f", ["LocalVariable.var1.line3"]),
            ],
        ),
        (  # language=Python "While else loop"
            """
def f():
    var1 = 10
    while var1 > 0:
        var1
    else:
        2 * var1
            """,  # language=none
            [
                ReferenceTestNode("var1.line4", "FunctionDef.f", ["LocalVariable.var1.line3"]),
                ReferenceTestNode("var1.line5", "FunctionDef.f", ["LocalVariable.var1.line3"]),
                ReferenceTestNode("var1.line7", "FunctionDef.f", ["LocalVariable.var1.line3"]),
            ],
        ),
    ],
    ids=[
        "For loop with global runtime variable",
        "For loop wih local runtime variable",
        "For loop in list comprehension",
        "While loop",
        "While else loop",
    ],
)
def test_resolve_references_loops(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code).resolved_references
    transformed_references: list[ReferenceTestNode] = []

    for node in references.values():
        transformed_references.extend(transform_reference_nodes(node))

    # assert references == expected
    assert set(transformed_references) == set(expected)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "Array and indexed array"
            """
def f():
    arr = [1, 2, 3]
    val = arr
    res = arr[0]
    arr[0] = 10
            """,  # language=none
            [
                ReferenceTestNode("arr.line4", "FunctionDef.f", ["LocalVariable.arr.line3"]),
                ReferenceTestNode("arr.line5", "FunctionDef.f", ["LocalVariable.arr.line3"]),
                ReferenceTestNode("arr.line6", "FunctionDef.f", ["LocalVariable.arr.line3"]),
            ],
        ),
        (  # language=Python "Dictionary"
            """
def f():
    dictionary = {"key1": 1, "key2": 2}
    dictionary["key1"] = 0
            """,  # language=none
            [ReferenceTestNode("dictionary.line4", "FunctionDef.f", ["LocalVariable.dictionary.line3"])],
        ),
        (  # language=Python "Map function"
            """
numbers = [1, 2, 3, 4, 5]

def square(x):
    return x ** 2

def f():
    squares = list(map(square, numbers))
    squares
            """,  # language=none
            [
                ReferenceTestNode("list.line8", "FunctionDef.f", ["Builtin.list"]),
                ReferenceTestNode("map.line8", "FunctionDef.f", ["Builtin.map"]),
                ReferenceTestNode("x.line5", "FunctionDef.square", ["Parameter.x.line4"]),
                ReferenceTestNode("square.line8", "FunctionDef.f", ["GlobalVariable.square.line4"]),
                ReferenceTestNode("numbers.line8", "FunctionDef.f", ["GlobalVariable.numbers.line2"]),
                ReferenceTestNode("squares.line9", "FunctionDef.f", ["LocalVariable.squares.line8"]),
            ],
        ),
        (  # language=Python "Two variables"
            """
def f():
    x = 10
    y = 20
    x + y
            """,  # language=none
            [
                ReferenceTestNode("x.line5", "FunctionDef.f", ["LocalVariable.x.line3"]),
                ReferenceTestNode("y.line5", "FunctionDef.f", ["LocalVariable.y.line4"]),
            ],
        ),
        (  # language=Python "Double return"
            """
def double_return(a, b):
    return a, b

def f():
    x, y = double_return(10, 20)
    x, y
            """,  # language=none
            [
                ReferenceTestNode("double_return.line6", "FunctionDef.f", ["GlobalVariable.double_return.line2"]),
                ReferenceTestNode("a.line3", "FunctionDef.double_return", ["Parameter.a.line2"]),
                ReferenceTestNode("b.line3", "FunctionDef.double_return", ["Parameter.b.line2"]),
                ReferenceTestNode("x.line7", "FunctionDef.f", ["LocalVariable.x.line6"]),
                ReferenceTestNode("y.line7", "FunctionDef.f", ["LocalVariable.y.line6"]),
            ],
        ),
        (  # language=Python "Reassignment"
            """
def f():
    x = 10
    x = 20
    x
            """,  # language=none
            [
                ReferenceTestNode("x.line5", "FunctionDef.f", ["LocalVariable.x.line3", "LocalVariable.x.line4"]),
                ReferenceTestNode("x.line4", "FunctionDef.f", ["LocalVariable.x.line3"]),
            ],
        ),
        (  # language=Python "Vars with comma"
            """
def f():
    x = 10
    y = 20
    x, y
            """,  # language=none
            [
                ReferenceTestNode("x.line5", "FunctionDef.f", ["LocalVariable.x.line3"]),
                ReferenceTestNode("y.line5", "FunctionDef.f", ["LocalVariable.y.line4"]),
            ],
        ),
        (  # language=Python "Vars with extended iterable unpacking"
            """
def f():
    a, *b, c = [1, 2, 3, 4, 5]
    a, b, c
            """,  # language=none
            [
                ReferenceTestNode("a.line4", "FunctionDef.f", ["LocalVariable.a.line3"]),
                ReferenceTestNode("b.line4", "FunctionDef.f", ["LocalVariable.b.line3"]),
                ReferenceTestNode("c.line4", "FunctionDef.f", ["LocalVariable.c.line3"]),
            ],
        ),
        (  # language=Python "String (f-string)"
            """
def f():
    x = 10
    y = 20
    f"{x} + {y} = {x + y}"
            """,  # language=none
            [
                ReferenceTestNode("x.line5", "FunctionDef.f", ["LocalVariable.x.line3"]),
                ReferenceTestNode("y.line5", "FunctionDef.f", ["LocalVariable.y.line4"]),
                ReferenceTestNode("x.line5", "FunctionDef.f", ["LocalVariable.x.line3"]),
                ReferenceTestNode("y.line5", "FunctionDef.f", ["LocalVariable.y.line4"]),
            ],
        ),
        (  # language=Python "Multiple references in one line"
            """
def f():
    var1 = 10
    var2 = 20

    res = var1 + var2 - (var1 * var2)
            """,  # language=none
            [
                ReferenceTestNode("var1.line6", "FunctionDef.f", ["LocalVariable.var1.line3"]),
                ReferenceTestNode("var2.line6", "FunctionDef.f", ["LocalVariable.var2.line4"]),
                ReferenceTestNode("var1.line6", "FunctionDef.f", ["LocalVariable.var1.line3"]),
                ReferenceTestNode("var2.line6", "FunctionDef.f", ["LocalVariable.var2.line4"]),
            ],
        ),
        (  # language=Python "Walrus operator"
            """
def f():
    y = (x := 3) + 10
    x, y
            """,  # language=none
            [
                ReferenceTestNode("x.line4", "FunctionDef.f", ["LocalVariable.x.line3"]),
                ReferenceTestNode("y.line4", "FunctionDef.f", ["LocalVariable.y.line3"]),
            ],
        ),
        (  # language=Python "Variable swap"
            """
def f():
    a = 1
    b = 2
    a, b = b, a
            """,  # language=none
            [
                ReferenceTestNode("a.line5", "FunctionDef.f", ["LocalVariable.a.line3", "LocalVariable.a.line5"]),
                ReferenceTestNode("b.line5", "FunctionDef.f", ["LocalVariable.b.line4", "LocalVariable.b.line5"]),
                ReferenceTestNode("b.line5", "FunctionDef.f", ["LocalVariable.b.line4"]),
                ReferenceTestNode("a.line5", "FunctionDef.f", ["LocalVariable.a.line3"]),
            ],
        ),
        (  # language=Python "Aliases"
            """
def f():
    a = 10
    b = a
    c = b
    c
            """,  # language=none
            [
                ReferenceTestNode("a.line4", "FunctionDef.f", ["LocalVariable.a.line3"]),
                ReferenceTestNode("b.line5", "FunctionDef.f", ["LocalVariable.b.line4"]),
                ReferenceTestNode("c.line6", "FunctionDef.f", ["LocalVariable.c.line5"]),
            ],
        ),
        (  # language=Python "Various assignments"
            """
def f():
    a = 10
    a = 20
    a = a + 10
    a = a * 2
    a
            """,  # language=none
            [
                ReferenceTestNode(
                    "a.line5",
                    "FunctionDef.f",
                    [
                        "LocalVariable.a.line3",
                        "LocalVariable.a.line4",
                        "LocalVariable.a.line5",
                    ],
                ),
                ReferenceTestNode(
                    "a.line6",
                    "FunctionDef.f",
                    [
                        "LocalVariable.a.line3",
                        "LocalVariable.a.line4",
                        "LocalVariable.a.line5",
                        "LocalVariable.a.line6",
                    ],
                ),
                ReferenceTestNode(
                    "a.line7",
                    "FunctionDef.f",
                    [
                        "LocalVariable.a.line3",
                        "LocalVariable.a.line4",
                        "LocalVariable.a.line5",
                        "LocalVariable.a.line6",
                    ],
                ),
                ReferenceTestNode(
                    "a.line6",
                    "FunctionDef.f",
                    ["LocalVariable.a.line3", "LocalVariable.a.line4", "LocalVariable.a.line5"],
                ),
                ReferenceTestNode("a.line5", "FunctionDef.f", ["LocalVariable.a.line3", "LocalVariable.a.line4"]),
                ReferenceTestNode("a.line4", "FunctionDef.f", ["LocalVariable.a.line3"]),
            ],
        ),
        (  # language=Python "Chained assignment"
            """
var1 = 1
var2 = 2
var3 = 3

def f():
    inp = input()

    var1 = a = inp  # var1 is now a local variable
    a = var2 = inp  # var2 is now a local variable
    var1 = a = var3
            """,  # language=none
            [
                ReferenceTestNode("input.line7", "FunctionDef.f", ["Builtin.input"]),
                ReferenceTestNode("inp.line9", "FunctionDef.f", ["LocalVariable.inp.line7"]),
                ReferenceTestNode("a.line10", "FunctionDef.f", ["LocalVariable.a.line9"]),
                ReferenceTestNode("inp.line10", "FunctionDef.f", ["LocalVariable.inp.line7"]),
                ReferenceTestNode("var1.line11", "FunctionDef.f", ["LocalVariable.var1.line9"]),
                ReferenceTestNode("a.line11", "FunctionDef.f", ["LocalVariable.a.line10", "LocalVariable.a.line9"]),
                ReferenceTestNode("var3.line11", "FunctionDef.f", ["GlobalVariable.var3.line4"]),
            ],
        ),
        (  # language=Python "Chained assignment global keyword"
            """
var1 = 1
var2 = 2
var3 = 3

def f(a):
    global var1, var2, var3
    inp = input()

    var1 = a = inp
    a = var2 = inp
    var1 = a = var3
            """,  # language=none
            [
                ReferenceTestNode("input.line8", "FunctionDef.f", ["Builtin.input"]),
                ReferenceTestNode("a.line10", "FunctionDef.f", ["Parameter.a.line6"]),
                ReferenceTestNode("inp.line10", "FunctionDef.f", ["LocalVariable.inp.line8"]),
                ReferenceTestNode("var1.line10", "FunctionDef.f", ["GlobalVariable.var1.line2"]),
                ReferenceTestNode("a.line11", "FunctionDef.f", ["LocalVariable.a.line10", "Parameter.a.line6"]),
                ReferenceTestNode("var2.line11", "FunctionDef.f", ["GlobalVariable.var2.line3"]),
                ReferenceTestNode("inp.line11", "FunctionDef.f", ["LocalVariable.inp.line8"]),
                ReferenceTestNode(
                    "var1.line12",
                    "FunctionDef.f",
                    ["GlobalVariable.var1.line10", "GlobalVariable.var1.line2"],
                ),
                ReferenceTestNode(
                    "a.line12",
                    "FunctionDef.f",
                    ["LocalVariable.a.line10", "LocalVariable.a.line11", "Parameter.a.line6"],
                ),
                ReferenceTestNode("var3.line12", "FunctionDef.f", ["GlobalVariable.var3.line4"]),
            ],
        ),
        (  # language=Python "With Statement Function"
            """
def fun():
    with open("text.txt") as f:
        text = f.read()
        print(text)
        f.close()
            """,  # language=none
            [
                ReferenceTestNode("open.line3", "FunctionDef.fun", ["BuiltinOpen.open"]),
                ReferenceTestNode("read.line4", "FunctionDef.fun", ["BuiltinOpen.read"]),
                ReferenceTestNode("f.line4", "FunctionDef.fun", ["LocalVariable.f.line3"]),
                ReferenceTestNode("print.line5", "FunctionDef.fun", ["Builtin.print"]),
                ReferenceTestNode("text.line5", "FunctionDef.fun", ["LocalVariable.text.line4"]),
                ReferenceTestNode("close.line6", "FunctionDef.fun", ["BuiltinOpen.close"]),
                ReferenceTestNode("f.line6", "FunctionDef.fun", ["LocalVariable.f.line3"]),
            ],
        ),
    ],
    ids=[
        "Array and indexed array",
        "Dictionary",
        "Map function",
        "Two variables",
        "Double return",
        "Reassignment",
        "Vars with comma",
        "Vars with extended iterable unpacking",
        "String (f-string)",
        "Multiple references in one line",
        "Walrus operator",
        "Variable swap",
        "Aliases",
        "Various assignments",
        "Chained assignment",
        "Chained assignment global keyword",
        "With open",
    ],
)
def test_resolve_references_miscellaneous(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code).resolved_references
    transformed_references: list[ReferenceTestNode] = []

    for node in references.values():
        transformed_references.extend(transform_reference_nodes(node))

    # assert references == expected
    assert set(transformed_references) == set(expected)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "Builtin function call"
            """
def f():
    print("Hello, World!")
            """,  # language=none
            [ReferenceTestNode("print.line3", "FunctionDef.f", ["Builtin.print"])],
        ),
        (  # language=Python "Function call shadowing builtin function"
            """
def print(s):
    pass

def f():
    print("Hello, World!")
            """,  # language=none
            [
                ReferenceTestNode("print.line6", "FunctionDef.f", ["Builtin.print", "GlobalVariable.print.line2"]),
            ],
        ),
        (  # language=Python "Function call"
            """
def f():
    pass

def g():
    f()
            """,  # language=none
            [ReferenceTestNode("f.line6", "FunctionDef.g", ["GlobalVariable.f.line2"])],
        ),
        (  # language=Python "Function call with parameter"
            """
def f(a):
    return a

def g():
    x = 10
    f(x)
            """,  # language=none
            [
                ReferenceTestNode("f.line7", "FunctionDef.g", ["GlobalVariable.f.line2"]),
                ReferenceTestNode("a.line3", "FunctionDef.f", ["Parameter.a.line2"]),
                ReferenceTestNode("x.line7", "FunctionDef.g", ["LocalVariable.x.line6"]),
            ],
        ),
        (  # language=Python "Function call with keyword parameter"
            """
def f(value):
    return value

def g():
    x = 10
    f(value=x)
            """,  # language=none
            [
                ReferenceTestNode("f.line7", "FunctionDef.g", ["GlobalVariable.f.line2"]),
                ReferenceTestNode("value.line3", "FunctionDef.f", ["Parameter.value.line2"]),
                ReferenceTestNode("x.line7", "FunctionDef.g", ["LocalVariable.x.line6"]),
            ],
        ),
        (  # language=Python "Function call as value"
            """
def f(a):
    return a

def g():
    x = f(10)
            """,  # language=none
            [
                ReferenceTestNode("f.line6", "FunctionDef.g", ["GlobalVariable.f.line2"]),
                ReferenceTestNode("a.line3", "FunctionDef.f", ["Parameter.a.line2"]),
            ],
        ),
        (  # language=Python "Nested function call"
            """
def f(a):
    return a * 2

def g():
    f(f(f(10)))
            """,  # language=none
            [
                ReferenceTestNode("f.line6", "FunctionDef.g", ["GlobalVariable.f.line2"]),
                ReferenceTestNode("f.line6", "FunctionDef.g", ["GlobalVariable.f.line2"]),
                ReferenceTestNode("f.line6", "FunctionDef.g", ["GlobalVariable.f.line2"]),
                ReferenceTestNode("a.line3", "FunctionDef.f", ["Parameter.a.line2"]),
            ],
        ),
        (  # language=Python "Two functions"
            """
def fun1():
    return "Function 1"

def fun2():
    return "Function 2"

def g():
    fun1()
    fun2()
            """,  # language=none
            [
                ReferenceTestNode("fun1.line9", "FunctionDef.g", ["GlobalVariable.fun1.line2"]),
                ReferenceTestNode("fun2.line10", "FunctionDef.g", ["GlobalVariable.fun2.line5"]),
            ],
        ),
        (  # language=Python "Functon with function as parameter"
            """
def fun1():
    return "Function 1"

def fun2():
    return "Function 2"

def call_function(f):
    return f()

def g():
    call_function(fun1)
    call_function(fun2)
            """,  # language=none
            [
                ReferenceTestNode("f.line9", "FunctionDef.call_function", ["Parameter.f.line8"]),
                # f should be detected as a call but is treated as a parameter, since the passed function is not known before runtime
                # this is later handled as an unknown call
                ReferenceTestNode("call_function.line12", "FunctionDef.g", ["GlobalVariable.call_function.line8"]),
                ReferenceTestNode("call_function.line13", "FunctionDef.g", ["GlobalVariable.call_function.line8"]),
                ReferenceTestNode("fun1.line12", "FunctionDef.g", ["GlobalVariable.fun1.line2"]),
                ReferenceTestNode("fun2.line13", "FunctionDef.g", ["GlobalVariable.fun2.line5"]),
            ],
        ),
        (  # language=Python "Functon conditional with branching"
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

def g():
    call_function(1)
            """,  # language=none
            [
                ReferenceTestNode("fun1.line10", "FunctionDef.call_function", ["GlobalVariable.fun1.line2"]),
                ReferenceTestNode("fun2.line12", "FunctionDef.call_function", ["GlobalVariable.fun2.line5"]),
                ReferenceTestNode("call_function.line15", "FunctionDef.g", ["GlobalVariable.call_function.line8"]),
                ReferenceTestNode("a.line9", "FunctionDef.call_function", ["Parameter.a.line8"]),
            ],
        ),
        (  # language=Python "Recursive function call",
            """
def f(a):
    print(a)
    if a > 0:
        f(a - 1)

def g():
    x = 10
    f(x)
            """,  # language=none
            [
                ReferenceTestNode("print.line3", "FunctionDef.f", ["Builtin.print"]),
                ReferenceTestNode("f.line5", "FunctionDef.f", ["GlobalVariable.f.line2"]),
                ReferenceTestNode("f.line9", "FunctionDef.g", ["GlobalVariable.f.line2"]),
                ReferenceTestNode("a.line3", "FunctionDef.f", ["Parameter.a.line2"]),
                ReferenceTestNode("a.line4", "FunctionDef.f", ["Parameter.a.line2"]),
                ReferenceTestNode("a.line5", "FunctionDef.f", ["Parameter.a.line2"]),
                ReferenceTestNode("x.line9", "FunctionDef.g", ["LocalVariable.x.line8"]),
            ],
        ),
        (  # language=Python "Class instantiation"
            """
class F:
    pass

def g():
    F()
            """,  # language=none
            [ReferenceTestNode("F.line6", "FunctionDef.g", ["GlobalVariable.F.line2"])],
        ),
        (  # language=Python "Lambda function"
            """
var1 = 1

def f():
    global var1
    lambda x, y: x + y + var1
            """,  # language=none
            [
                ReferenceTestNode("var1.line6", "FunctionDef.f", ["GlobalVariable.var1.line2"]),
            ],
        ),
        (  # language=Python "Lambda function call"
            """
var1 = 1

def f():
    (lambda x, y: x + y + var1)(10, 20)
            """,  # language=none
            [
                ReferenceTestNode("var1.line5", "FunctionDef.f", ["GlobalVariable.var1.line2"]),
            ],
        ),
        (  # language=Python "Lambda function used as normal function"
            """
double = lambda x: 2 * x

def f():
    double(10)
            """,  # language=none
            [
                ReferenceTestNode("x.line2", "Lambda", ["Parameter.x.line2"]),
                ReferenceTestNode("double.line5", "FunctionDef.f", ["GlobalVariable.double.line2"]),
            ],
        ),
        (  # language=Python "Two lambda function used as normal function with the same name"
            """
class A:
    double = lambda x: 2 * x

class B:
    double = lambda x: 2 * x

def f():
    A.double(10)
    B.double(10)
            """,  # language=none
            [
                ReferenceTestNode("x.line3", "Lambda", ["Parameter.x.line3"]),
                ReferenceTestNode("A.line9", "FunctionDef.f", ["GlobalVariable.A.line2"]),
                ReferenceTestNode(
                    "double.line9",
                    "FunctionDef.f",
                    ["ClassVariable.A.double.line3", "ClassVariable.B.double.line6"],
                ),
                ReferenceTestNode("x.line6", "Lambda", ["Parameter.x.line6"]),
                ReferenceTestNode("B.line10", "FunctionDef.f", ["GlobalVariable.B.line5"]),
                ReferenceTestNode(
                    "double.line10",
                    "FunctionDef.f",
                    ["ClassVariable.A.double.line3", "ClassVariable.B.double.line6"],
                ),
            ],
        ),  # since we only return a list of all possible references, we can't distinguish between the two functions
        (  # language=Python "Lambda function used as normal function and normal function with the same name"
            """
class A:
    double = lambda x: 2 * x

class B:
    @staticmethod
    def double(x):
        return 2 * x

def f():
    A.double(10)
    B.double(10)
            """,  # language=none
            [
                ReferenceTestNode("x.line3", "Lambda", ["Parameter.x.line3"]),
                ReferenceTestNode("A.line11", "FunctionDef.f", ["GlobalVariable.A.line2"]),
                ReferenceTestNode(
                    "double.line11",
                    "FunctionDef.f",
                    ["ClassVariable.A.double.line3", "ClassVariable.B.double.line7"],
                ),
                ReferenceTestNode("x.line8", "FunctionDef.double", ["Parameter.x.line7"]),
                ReferenceTestNode("B.line12", "FunctionDef.f", ["GlobalVariable.B.line5"]),
                ReferenceTestNode(
                    "double.line12",
                    "FunctionDef.f",
                    ["ClassVariable.A.double.line3", "ClassVariable.B.double.line7"],
                ),
            ],
        ),  # since we only return a list of all possible references, we can't distinguish between the two functions
        (  # language=Python "Lambda function as key"
            """
def f():
    names = ["a", "abc", "ab", "abcd"]

    sort = sorted(names, key=lambda x: len(x))
    sort
            """,  # language=none
            [
                ReferenceTestNode("sorted.line5", "FunctionDef.f", ["Builtin.sorted"]),
                ReferenceTestNode("len.line5", "FunctionDef.f", ["Builtin.len"]),
                ReferenceTestNode("names.line5", "FunctionDef.f", ["LocalVariable.names.line3"]),
                # ReferenceTestNode("x.line5", "Lambda", ["Parameter.x.line5"]),
                ReferenceTestNode("sort.line6", "FunctionDef.f", ["LocalVariable.sort.line5"]),
            ],
        ),
        (  # language=Python "Generator function"
            """
def square_generator(limit):
    for i in range(limit):
        yield i**2

def g():
    gen = square_generator(5)
    for value in gen:
        value
            """,  # language=none
            [
                ReferenceTestNode("range.line3", "FunctionDef.square_generator", ["Builtin.range"]),
                ReferenceTestNode("square_generator.line7", "FunctionDef.g", ["GlobalVariable.square_generator.line2"]),
                ReferenceTestNode("limit.line3", "FunctionDef.square_generator", ["Parameter.limit.line2"]),
                ReferenceTestNode("i.line4", "FunctionDef.square_generator", ["LocalVariable.i.line3"]),
                ReferenceTestNode("gen.line8", "FunctionDef.g", ["LocalVariable.gen.line7"]),
                ReferenceTestNode("value.line9", "FunctionDef.g", ["LocalVariable.value.line8"]),
            ],
        ),
        (  # language=Python "Functions with the same name but different classes"
            """
class A:
    @staticmethod
    def add(a, b):
        return a + b

class B:
    @staticmethod
    def add(a, b):
        return a + 2 * b

def g():
    A.add(1, 2)
    B.add(1, 2)
            """,  # language=none
            [
                ReferenceTestNode("a.line5", "FunctionDef.add", ["Parameter.a.line4"]),
                ReferenceTestNode("b.line5", "FunctionDef.add", ["Parameter.b.line4"]),
                ReferenceTestNode("a.line10", "FunctionDef.add", ["Parameter.a.line9"]),
                ReferenceTestNode("b.line10", "FunctionDef.add", ["Parameter.b.line9"]),
                ReferenceTestNode("A.line13", "FunctionDef.g", ["GlobalVariable.A.line2"]),
                ReferenceTestNode(
                    "add.line13",
                    "FunctionDef.g",
                    ["ClassVariable.A.add.line4", "ClassVariable.B.add.line9"],
                ),
                ReferenceTestNode("B.line14", "FunctionDef.g", ["GlobalVariable.B.line7"]),
                ReferenceTestNode(
                    "add.line14",
                    "FunctionDef.g",
                    ["ClassVariable.A.add.line4", "ClassVariable.B.add.line9"],
                ),
            ],
        ),  # since we only return a list of all possible references, we can't distinguish between the two functions
        (  # language=Python "Functions with the same name but different signature"
            """
class A:
    @staticmethod
    def add(a, b):
        return a + b

class B:
    @staticmethod
    def add(a, b, c):
        return a + b + c

def g():
    A.add(1, 2)
    B.add(1, 2, 3)
            """,  # language=none
            [
                ReferenceTestNode("a.line5", "FunctionDef.add", ["Parameter.a.line4"]),
                ReferenceTestNode("b.line5", "FunctionDef.add", ["Parameter.b.line4"]),
                ReferenceTestNode("a.line10", "FunctionDef.add", ["Parameter.a.line9"]),
                ReferenceTestNode("b.line10", "FunctionDef.add", ["Parameter.b.line9"]),
                ReferenceTestNode("c.line10", "FunctionDef.add", ["Parameter.c.line9"]),
                ReferenceTestNode("A.line13", "FunctionDef.g", ["GlobalVariable.A.line2"]),
                ReferenceTestNode(
                    "add.line13",
                    "FunctionDef.g",
                    ["ClassVariable.A.add.line4", "ClassVariable.B.add.line9"],
                ),  # remove this
                ReferenceTestNode("B.line14", "FunctionDef.g", ["GlobalVariable.B.line7"]),
                ReferenceTestNode(
                    "add.line14",
                    "FunctionDef.g",
                    ["ClassVariable.A.add.line4", "ClassVariable.B.add.line9"],  # remove this
                ),
            ],
            # TODO: [LATER] we should detect the different signatures
        ),
        (  # language=Python "Class function call"
            """
class A:
    def fun_a(self):
        return

def g():
    a = A()
    a.fun_a()
            """,  # language=none
            [
                ReferenceTestNode("A.line7", "FunctionDef.g", ["GlobalVariable.A.line2"]),
                ReferenceTestNode("fun_a.line8", "FunctionDef.g", ["ClassVariable.A.fun_a.line3"]),
                ReferenceTestNode("a.line8", "FunctionDef.g", ["LocalVariable.a.line7"]),
            ],
        ),
        (  # language=Python "Class function call, direct call"
            """
class A:
    def fun_a(self):
        return

def g():
    A().fun_a()
            """,  # language=none
            [
                ReferenceTestNode("A.line7", "FunctionDef.g", ["GlobalVariable.A.line2"]),
                ReferenceTestNode("fun_a.line7", "FunctionDef.g", ["ClassVariable.A.fun_a.line3"]),
            ],
        ),
        #         (  # language=Python "class function and class variable with same name"
        #             """
        # class A:
        #     fun = 1
        #
        #     def fun(self):
        #         return
        #
        # def g():
        #     A().fun()
        #             """,  # language=none
        #             [ReferenceTestNode("fun.line9", "FunctionDef.g", ["ClassVariable.A.fun.line3",
        #                                                               "ClassVariable.A.fun.line5"]),
        #              ReferenceTestNode("A.line9", "FunctionDef.g", ["GlobalVariable.A.line2"])]
        #         ),
    ],
    ids=[
        "Builtin function call",
        "Function call shadowing builtin function",
        "Function call",
        "Function call with parameter",
        "Function call with keyword parameter",
        "Function call as value",
        "Nested function call",
        "Two functions",
        "Function with function as parameter",
        "Function with conditional branching",
        "Recursive function call",
        "Class instantiation",
        "Lambda function",
        "Lambda function call",
        "Lambda function used as normal function",
        "Two lambda functions used as normal function with the same name",
        "Lambda function used as normal function and normal function with the same name",
        "Lambda function as key",
        "Generator function",
        "Functions with the same name but different classes",
        "Functions with the same name but different signature",
        "Class function call",
        "Class function call, direct call",
        # "Class function and class variable with the same name"  # This is bad practice and therfore is not covered- only the function def will be found in this case
    ],
)
def test_resolve_references_calls(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code).resolved_references
    transformed_references: list[ReferenceTestNode] = []

    # assert references == expected
    for node in references.values():
        transformed_references.extend(transform_reference_nodes(node))

    assert set(transformed_references) == set(expected)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "Import"
            """
import math

math
            """,  # language=none
            [""],  # TODO
        ),
        (  # language=Python "Import with use"
            """
import math

math.pi
            """,  # language=none
            [""],  # TODO
        ),
        (  # language=Python "Import multiple"
            """
import math, sys

math.pi
sys.version
            """,  # language=none
            [""],  # TODO
        ),
        (  # language=Python "Import as"
            """
import math as m

m.pi
            """,  # language=none
            [""],  # TODO
        ),
        (  # language=Python "Import from"
            """
from math import sqrt

sqrt(4)
            """,  # language=none
            [""],  # TODO
        ),
        (  # language=Python "Import from multiple"
            """
from math import pi, sqrt

pi
sqrt(4)
            """,  # language=none
            [""],  # TODO
        ),
        (  # language=Python "Import from as"
            """
from math import sqrt as s

s(4)
            """,  # language=none
            [""],  # TODO
        ),
        (  # language=Python "Import from as multiple"
            """
from math import pi as p, sqrt as s

p
s(4)
            """,  # language=none
            [""],  # TODO
        ),
    ],
    ids=[
        "Import",
        "Import with use",
        "Import multiple",
        "Import as",
        "Import from",
        "Import from multiple",
        "Import from as",
        "Import from as multiple",
    ],
)
@pytest.mark.xfail(reason="Not implemented yet")
def test_resolve_references_imports(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code).resolved_references
    transformed_references: list[ReferenceTestNode] = []

    for node in references.values():
        transformed_references.extend(transform_reference_nodes(node))

    # assert references == expected
    assert set(transformed_references) == set(expected)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "Dataclass"
            """
from dataclasses import dataclass

@dataclass
class State:
    pass

def f():
    State()
            """,  # language=none
            [ReferenceTestNode("State.line9", "FunctionDef.f", ["GlobalVariable.State.line5"])],
        ),
        (  # language=Python "Dataclass with default attribute"
            """
from dataclasses import dataclass

@dataclass
class State:
    state: int = 0

def f():
    State().state
            """,  # language=none
            [
                ReferenceTestNode("State.line9", "FunctionDef.f", ["GlobalVariable.State.line5"]),
                ReferenceTestNode("State.state.line9", "FunctionDef.f", ["ClassVariable.State.state.line6"]),
            ],
        ),
        (  # language=Python "Dataclass with attribute"
            """
from dataclasses import dataclass

@dataclass
class State:
    state: int

def f():
    State(0).state
            """,  # language=none
            [
                ReferenceTestNode("State.line9", "FunctionDef.f", ["GlobalVariable.State.line5"]),
                ReferenceTestNode("State.state.line9", "FunctionDef.f", ["ClassVariable.State.state.line6"]),
            ],
        ),
        (  # language=Python "Dataclass with @property and @setter"
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
        self._state = value

def f():
    a = State(1)
    a.state = 2
            """,  # language=none
            [
                ReferenceTestNode("self.line10", "FunctionDef.state", ["Parameter.self.line9"]),
                ReferenceTestNode("self._state.line10", "FunctionDef.state", ["ClassVariable.State._state.line6"]),
                ReferenceTestNode("self.line14", "FunctionDef.state", ["Parameter.self.line13"]),
                ReferenceTestNode("self._state.line14", "FunctionDef.state", ["ClassVariable.State._state.line6"]),
                ReferenceTestNode("value.line14", "FunctionDef.state", ["Parameter.value.line13"]),
                ReferenceTestNode("State.line17", "FunctionDef.f", ["GlobalVariable.State.line5"]),
                ReferenceTestNode(
                    "a.state.line18",
                    "FunctionDef.f",
                    ["ClassVariable.State.state.line13", "ClassVariable.State.state.line9"],
                ),
                ReferenceTestNode("a.line18", "FunctionDef.f", ["LocalVariable.a.line17"]),
            ],
        ),
    ],
    ids=[
        "Dataclass",
        "Dataclass with default attribute",
        "Dataclass with attribute",
        "Dataclass with @property and @setter",
    ],
)
def test_resolve_references_dataclasses(code: str, expected: list[ReferenceTestNode]) -> None:
    references = resolve_references(code).resolved_references
    transformed_references: list[ReferenceTestNode] = []

    for node in references.values():
        transformed_references.extend(transform_reference_nodes(node))

    # assert references == expected
    assert set(transformed_references) == set(expected)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "Basics"
            """
b = 1
c = 2
d = 3
def g():
    pass

def f():
    global b
    a = 1  # LocaleWrite
    b = 2  # NonLocalVariableWrite
    a      # LocaleRead
    c      # NonLocalVariableRead
    b = d  # NonLocalVariableWrite, NonLocalVariableRead
    g()    # Call
    x = open("text.txt") # LocalWrite, Call
            """,  # language=none
            {
                ".f.8.0": SimpleReasons(
                    "f",
                    {"GlobalVariable.b.line2", "GlobalVariable.b.line11"},
                    {
                        "GlobalVariable.c.line3",
                        "GlobalVariable.d.line4",
                    },
                    {
                        "GlobalVariable.g.line5",
                        "BuiltinOpen.open",
                    },
                ),
                ".g.5.0": SimpleReasons("g", set(), set(), set()),
            },
        ),
        (  # language=Python "Control flow statements"
            """
b = 1
c = 0

def f():
    global b, c
    if b > 1:  # we ignore all control flow statements
        a = 1  # LocaleWrite
    else:
        c = 2  # NonLocalVariableWrite

    while a < 10:  # we ignore all control flow statements
        b += 1  # NonLocalVariableWrite
            """,  # language=none
            {
                ".f.5.0": SimpleReasons(
                    "f",
                    {
                        "GlobalVariable.c.line3",
                        "GlobalVariable.b.line2",
                    },
                    {
                        "GlobalVariable.b.line2",
                    },
                ),
            },
        ),
        (  # language=Python "Class attribute"
            """
class A:
    class_attr1 = 20

def f():
    a = A()
    a.class_attr1 = 10  # NonLocalVariableWrite

def g():
    a = A()
    c = a.class_attr1  # NonLocalVariableRead
            """,  # language=none
            {
                ".f.5.0": SimpleReasons(
                    "f",
                    {
                        "ClassVariable.A.class_attr1.line3",
                    },
                    set(),
                    {"GlobalVariable.A.line2"},
                ),
                ".g.9.0": SimpleReasons("g", set(), {"ClassVariable.A.class_attr1.line3"}, {"GlobalVariable.A.line2"}),
            },
        ),
        (  # language=Python "Instance attribute"
            """
class A:
    def __init__(self):
        self.instance_attr1 = 20

def f1():
    a = A()
    a.instance_attr1 = 10  # NonLocalVariableWrite  # TODO [Later] we should detect that this is a local variable

b = A()
def f2(x):
    x.instance_attr1 = 10  # NonLocalVariableWrite

def f3():
    global b
    b.instance_attr1 = 10  # NonLocalVariableWrite

def g1():
    a = A()
    c = a.instance_attr1  # NonLocalVariableRead  # TODO [Later] we should detect that this is a local variable

def g2(x):
    c = x.instance_attr1  # NonLocalVariableRead

def g3():
    global b
    c = b.instance_attr1  # NonLocalVariableRead
            """,  # language=none
            {
                ".__init__.3.4": SimpleReasons("__init__"),
                ".f1.6.0": SimpleReasons(
                    "f1",
                    {
                        "InstanceVariable.A.instance_attr1.line4",
                    },
                    set(),
                    {"GlobalVariable.A.line2"},
                ),
                ".f2.11.0": SimpleReasons(
                    "f2",
                    {
                        "InstanceVariable.A.instance_attr1.line4",
                    },
                ),
                ".f3.14.0": SimpleReasons(
                    "f3",
                    {"GlobalVariable.b.line10", "InstanceVariable.A.instance_attr1.line4"},
                ),
                ".g1.18.0": SimpleReasons(
                    "g1",
                    set(),
                    {
                        "InstanceVariable.A.instance_attr1.line4",
                    },
                    {"GlobalVariable.A.line2"},
                ),
                ".g2.22.0": SimpleReasons(
                    "g2",
                    set(),
                    {
                        "InstanceVariable.A.instance_attr1.line4",
                    },
                ),
                ".g3.25.0": SimpleReasons(
                    "g3",
                    set(),
                    {
                        "GlobalVariable.b.line10",
                        "InstanceVariable.A.instance_attr1.line4",
                    },
                ),
            },
        ),
        (  # language=Python "Chained attributes"
            """
class A:
    def __init__(self):
        self.name = 10

    def set_name(self, name):
        self.name = name

class B:
    upper_class: A = A()

def f():
    b = B()
    x = b.upper_class.name
    b.upper_class.set_name("test")
            """,  # language=none
            {
                ".__init__.3.4": SimpleReasons("__init__"),
                ".set_name.6.4": SimpleReasons("set_name", {"InstanceVariable.A.name.line4"}),
                ".f.12.0": SimpleReasons(
                    "f",
                    set(),
                    {
                        "InstanceVariable.A.name.line4",
                        "ClassVariable.B.upper_class.line10",
                    },
                    {
                        "GlobalVariable.B.line9",
                        "ClassVariable.A.set_name.line6",
                    },
                ),
            },
        ),
        (  # language=Python "Chained class function call"
            """
class B:
    def __init__(self):
        self.b = 20

    def f(self):
        pass

class A:
    class_attr1 = B()

def g():
    A().class_attr1.f()
            """,  # language=none
            {
                ".__init__.3.4": SimpleReasons("__init__"),
                ".f.6.4": SimpleReasons("f", set(), set(), set()),
                ".g.12.0": SimpleReasons(
                    "g",
                    set(),
                    {
                        "ClassVariable.A.class_attr1.line10",
                    },
                    {"GlobalVariable.A.line9", "ClassVariable.B.f.line6"},
                ),
            },
        ),
        (  # language=Python "Two classes with same attribute name"
            """
class A:
    name: str = ""

    def __init__(self, name: str):
        self.name = name

class B:
    name: str = ""

    def __init__(self, name: str):
        self.name = name

def f():
    a = A("value")
    b = B("test")
    a.name
    b.name
            """,  # language=none
            {
                ".__init__.5.4": SimpleReasons("__init__", {"ClassVariable.A.name.line3"}),
                ".__init__.11.4": SimpleReasons("__init__", {"ClassVariable.B.name.line9"}),
                ".f.14.0": SimpleReasons(
                    "f",
                    set(),
                    {  # Here we find both: ClassVariables and InstanceVariables because we can't distinguish between them
                        "ClassVariable.A.name.line3",
                        "ClassVariable.B.name.line9",
                        "InstanceVariable.A.name.line6",
                        "InstanceVariable.B.name.line12",
                    },
                    {"GlobalVariable.A.line2", "GlobalVariable.B.line8"},
                ),
            },
        ),
        (  # language=Python "Multiple classes with same function name - same signature"
            """
z = 2

class A:
    @staticmethod
    def add(a, b):
        global z
        return a + b + z

class B:
    @staticmethod
    def add(a, b):
        return a + 2 * b

def f():
    x = A.add(1, 2)  # This is not a global read of A. Since we define classes and functions as immutable.
    y = B.add(1, 2)
    if x == y:
        pass
            """,  # language=none
            {
                ".add.6.4": SimpleReasons("add", set(), {"GlobalVariable.z.line2"}, set()),
                ".add.12.4": SimpleReasons(
                    "add",
                ),
                ".f.15.0": SimpleReasons(
                    "f",
                    set(),
                    set(),
                    {
                        "ClassVariable.A.add.line6",
                        "ClassVariable.B.add.line12",
                    },
                ),
            },
        ),  # since we only return a list of all possible references, we can't distinguish between the two functions
        (  # language=Python "Multiple classes with same function name - different signature"
            """
class A:
    @staticmethod
    def add(a, b):
        return a + b

class B:
    @staticmethod
    def add(a, b, c):
        return a + b + c

def f():
    A.add(1, 2)
    B.add(1, 2, 3)
            """,  # language=none
            {
                ".add.4.4": SimpleReasons(
                    "add",
                ),
                ".add.9.4": SimpleReasons(
                    "add",
                ),
                ".f.12.0": SimpleReasons(
                    "f",
                    set(),
                    set(),
                    {
                        "ClassVariable.A.add.line4",
                        "ClassVariable.B.add.line9",
                    },
                ),
            },
        ),  # TODO: [LATER] we should detect the different signatures
    ],
    ids=[
        "Basics",
        "Control flow statements",
        "Class attribute",
        "Instance attribute",
        "Chained attributes",
        "Chained class function call",
        "Two classes with same attribute name",
        "Multiple classes with same function name - same signature",
        "Multiple classes with same function name - different signature",
        # TODO: [LATER] we should detect the different signatures
    ],
)
@pytest.mark.xfail(reason="Calls are removed after call graph is built")
def test_get_module_data_reasons(code: str, expected: dict[str, SimpleReasons]) -> None:
    function_references = resolve_references(code).raw_reasons

    transformed_function_references = transform_reasons(function_references)
    # assert function_references == expected

    assert transformed_function_references == expected


# TODO: testcases for cyclic calls and recursive calls
