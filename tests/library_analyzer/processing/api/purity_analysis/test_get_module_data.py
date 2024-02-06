from __future__ import annotations

from dataclasses import dataclass, field

import astroid
import pytest
from library_analyzer.processing.api.purity_analysis import (
    calc_node_id,
    get_module_data,
)
from library_analyzer.processing.api.purity_analysis.model import (
    ClassScope,
    FunctionScope,
    MemberAccess,
    MemberAccessTarget,
    MemberAccessValue,
    NodeID,
    Reasons,
    Scope,
    Symbol,
)


# TODO: refactor: move functions to top of file
@dataclass
class SimpleScope:
    """Class for simple scopes.

    A simplified class of the Scope class for testing purposes.

    Attributes
    ----------
    node_name : str | None
        The name of the node.
    children : list[SimpleScope] | None
        The children of the node.
        None if the node has no children.
    """

    node_name: str | None
    children: list[SimpleScope] | None


@dataclass
class SimpleClassScope(SimpleScope):
    """Class for simple class scopes.

    A simplified class of the ClassScope class for testing purposes.

    Attributes
    ----------
    node_name : str | None
        The name of the node.
    children : list[SimpleScope] | None
        The children of the node.
        None if the node has no children.
    class_variables : list[str]
        The list of class variables.
    instance_variables : list[str]
        The list of instance variables.
    super_class : list[str]
        The list of super classes.
    """

    class_variables: list[str]
    instance_variables: list[str]
    super_class: list[str] = field(default_factory=list)


@dataclass
class SimpleFunctionScope(SimpleScope):
    """Class for simple function scopes.

    A simplified class of the FunctionScope class for testing purposes.

    Attributes
    ----------
    node_name : str | None
        The name of the node.
    children : list[SimpleScope] | None
        The children of the node.
        None if the node has no children.
    values : list[str]
        The list of value nodes used in the function as string.
    calls : list[str]
        The list of call nodes used in the function as string.
    """

    values: list[str]
    calls: list[str]
    parameters: list[str] = field(default_factory=list)


@dataclass
class SimpleReasons:
    """Class for simple reasons.

    A simplified class of the Reasons class for testing purposes.

    Attributes
    ----------
    function_name : str
        The name of the function.
    writes : set[SimpleFunctionReference]
        The set of the functions writes.
    reads : set[SimpleFunctionReference]
        The set of the function reads.
    calls : set[SimpleFunctionReference]
        The set of the function calls.
    """

    function_name: str
    writes: set[SimpleFunctionReference] = field(default_factory=set)
    reads: set[SimpleFunctionReference] = field(default_factory=set)
    calls: set[SimpleFunctionReference] = field(default_factory=set)

    def __hash__(self) -> int:
        return hash(self.function_name)


@dataclass
class SimpleFunctionReference:
    """Class for simple function references.

    A simplified class of the FunctionReference class for testing purposes.

    Attributes
    ----------
    node : str
        The name of the node.
    kind : str
        The kind of the Reason as string.
    """

    node: str
    kind: str

    def __hash__(self) -> int:
        return hash((self.node, self.kind))


def transform_scope_node(
    node: Scope | ClassScope | FunctionScope) -> SimpleScope | SimpleClassScope | SimpleFunctionScope:
    """Transform a Scope, ClassScope or FunctionScope instance.

    Parameters
    ----------
    node : Scope | ClassScope | FunctionScope
        The node to transform.

    Returns
    -------
    SimpleScope | SimpleClassScope | SimpleFunctionScope
        The transformed node.
    """
    if node.children is not None:
        if isinstance(node, ClassScope):
            instance_vars_transformed = []
            class_vars_transformed = []
            super_classes_transformed = []
            for child in node.instance_variables.values():
                for c in child:
                    c_str = to_string_class(c.node.member)
                    if c_str is not None:
                        instance_vars_transformed.append(
                            c_str)  # type: ignore[misc] # it is not possible that c_str is None
            for child in node.class_variables.values():
                for c in child:
                    c_str = to_string_class(c.node)
                    if c_str is not None:
                        class_vars_transformed.append(
                            c_str)  # type: ignore[misc] # it is not possible that c_str is None

            for klass in node.super_classes:
                c_str = to_string_class(klass)
                if c_str is not None:
                    super_classes_transformed.append(
                        c_str)  # type: ignore[misc] # it is not possible that c_str is None

            return SimpleClassScope(
                to_string(node.symbol),
                [transform_scope_node(child) for child in node.children],
                class_vars_transformed,
                instance_vars_transformed,
                super_classes_transformed,
            )
        if isinstance(node, FunctionScope):
            values_transformed = []
            calls_transformed = []
            parameters_transformed = []
            for value in node.values:
                values_transformed.append(to_string_func(value.symbol.node))
            for call in node.calls:
                calls_transformed.append(to_string_func(call.symbol.node))
            for parameter in node.parameters.values():
                parameters_transformed.append(to_string_func(parameter.node))

            return SimpleFunctionScope(
                to_string(node.symbol),
                [transform_scope_node(child) for child in node.children],
                values_transformed,
                calls_transformed,
                parameters_transformed,
            )

        return SimpleScope(to_string(node.symbol), [transform_scope_node(child) for child in node.children])
    else:
        return SimpleScope(to_string(node.symbol), [])


def to_string(symbol: Symbol) -> str:
    """Transform a Symbol instance to a string.

    Parameters
    ----------
    symbol : Symbol
        The Symbol instance to transform.

    Returns
    -------
    str
        The transformed Symbol instance as string.
    """
    if isinstance(symbol.node, astroid.Module):
        return f"{symbol.node.__class__.__name__}"
    elif isinstance(symbol.node, astroid.ClassDef | astroid.FunctionDef | astroid.AssignName):
        return f"{symbol.__class__.__name__}.{symbol.node.__class__.__name__}.{symbol.node.name}"
    elif isinstance(symbol.node, astroid.AssignAttr):
        return f"{symbol.__class__.__name__}.{symbol.node.__class__.__name__}.{symbol.node.attrname}"
    elif isinstance(symbol.node, MemberAccess):
        result = transform_member_access(symbol.node)
        return f"{symbol.__class__.__name__}.MemberAccess.{result}"
    elif isinstance(symbol.node, astroid.Import):
        return (  # TODO: handle multiple imports and aliases
            f"{symbol.__class__.__name__}.{symbol.node.__class__.__name__}.{symbol.node.names[0][0]}"
        )
    elif isinstance(symbol.node, astroid.ImportFrom):
        return f"{symbol.__class__.__name__}.{symbol.node.__class__.__name__}.{symbol.node.modname}.{symbol.node.names[0][0]}"  # TODO: handle multiple imports and aliases
    elif isinstance(symbol.node, astroid.Name):
        return f"{symbol.__class__.__name__}.{symbol.node.__class__.__name__}.{symbol.node.name}"
    elif isinstance(symbol.node, astroid.ListComp | astroid.TryExcept | astroid.TryFinally | astroid.With):
        return f"{symbol.node.__class__.__name__}"
    elif isinstance(symbol.node, astroid.Lambda):
        if symbol.name != "Lambda":
            return f"{symbol.__class__.__name__}.{symbol.node.__class__.__name__}.{symbol.name}"
        return f"{symbol.__class__.__name__}.{symbol.node.__class__.__name__}"
    raise NotImplementedError(f"Unknown node type: {symbol.node.__class__.__name__}")


def to_string_class(node: astroid.NodeNG | ClassScope) -> str | None:
    """Transform a NodeNG or ClassScope instance to a string.

    Parameters
    ----------
    node : astroid.NodeNG | ClassScope
        The NodeNG or ClassScope instance to transform.

    Returns
    -------
    str | None
        The transformed NodeNG or ClassScope instance as string.
        None if the node is a Lambda, TryExcept, TryFinally or ListComp instance.
    """
    if isinstance(node, astroid.AssignAttr):
        return f"{node.__class__.__name__}.{node.attrname}"
    elif isinstance(node, astroid.AssignName | astroid.FunctionDef | astroid.ClassDef):
        return f"{node.__class__.__name__}.{node.name}"
    elif isinstance(node, astroid.Lambda | astroid.TryExcept | astroid.TryFinally | astroid.ListComp):
        return None
    elif isinstance(node, ClassScope):
        return f"{node.symbol.node.__class__.__name__}.{node.symbol.node.name}"
    raise NotImplementedError(f"Unknown node type: {node.__class__.__name__}")


def to_string_func(node: astroid.NodeNG | MemberAccess) -> str:
    """Transform a NodeNG or MemberAccess instance to a string.

    Parameters
    ----------
    node : astroid.NodeNG | MemberAccess
        The NodeNG or MemberAccess instance to transform.

    Returns
    -------
    str
        The transformed NodeNG or FunctionScope instance as string.
    """
    if isinstance(node, astroid.Name | astroid.AssignName):
        return f"{node.__class__.__name__}.{node.name}"
    elif isinstance(node, MemberAccess):
        return f"{node.__class__.__name__}.{transform_member_access(node)}"
    elif isinstance(node, astroid.Call):
        if isinstance(node.func, astroid.Attribute):
            return f"Call.{node.func.attrname}"
        return f"Call.{node.func.name}"
    return f"{node.as_string()}"


def transform_value_nodes(value_nodes: dict[astroid.Name | MemberAccessValue, Scope | ClassScope]) -> dict[str, str]:
    """Transform the value nodes.

    The value nodes are transformed to a dictionary with the name of the node as key and the transformed node as value.

    Parameters
    ----------
    value_nodes : dict[astroid.Name | MemberAccessValue, Scope | ClassScope]
        The value nodes to transform.

    Returns
    -------
    dict[str, str]
        The transformed value nodes.
    """
    value_nodes_transformed = {}
    for node in value_nodes:
        if isinstance(node, astroid.Name):
            value_nodes_transformed.update({node.name: f"{node.__class__.__name__}.{node.name}"})
        elif isinstance(node, MemberAccessValue):
            result = transform_member_access(node)
            value_nodes_transformed.update({result: f"{node.__class__.__name__}.{result}"})

    return value_nodes_transformed


def transform_target_nodes(
    target_nodes: dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope | ClassScope],
) -> dict[str, str]:
    """Transform the target nodes.

    The target nodes are transformed to a dictionary with the name of the node as key and the transformed node as value.

    Parameters
    ----------
    target_nodes : dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope | ClassScope]

    Returns
    -------
    dict[str, str]
        The transformed target nodes.
    """
    target_nodes_transformed = {}
    for node in target_nodes:
        if isinstance(node, astroid.AssignName | astroid.Name):
            target_nodes_transformed.update({node.name: f"{node.__class__.__name__}.{node.name}"})
        elif isinstance(node, MemberAccessTarget):
            result = transform_member_access(node)
            target_nodes_transformed.update({result: f"{node.__class__.__name__}.{result}"})

    return target_nodes_transformed


def transform_member_access(member_access: MemberAccess) -> str:
    """Transform a MemberAccess instance to a string.

    Parameters
    ----------
    member_access : MemberAccess
        The MemberAccess instance to transform.

    Returns
    -------
    str
        The transformed MemberAccess instance as string.
    """
    attribute_names = []

    while isinstance(member_access, MemberAccess):
        if isinstance(member_access.member, astroid.AssignAttr | astroid.Attribute):
            attribute_names.append(member_access.member.attrname)
        else:
            attribute_names.append(member_access.member.name)
        member_access = member_access.receiver
    if isinstance(member_access, astroid.Name):
        attribute_names.append(member_access.name)

    return ".".join(reversed(attribute_names))


def transform_function_references(function_calls: dict[NodeID, Reasons]) -> dict[str, SimpleReasons]:
    """Transform the function references.

    The function references are transformed to a dictionary with the name of the function as key
    and the transformed Reasons instance as value.

    Parameters
    ----------
    function_calls : dict[str, Reasons]
        The function references to transform.

    Returns
    -------
    dict[str, SimpleReasons]
        The transformed function references.
    """
    transformed_function_references = {}
    for function_id, function_references in function_calls.items():
        transformed_function_references.update({
            function_id.__str__(): SimpleReasons(
                function_references.function.name,
                {
                    SimpleFunctionReference(
                        f"{function_reference.node.__class__.__name__}.{function_reference.node.name}.line{function_reference.node.member.fromlineno}",
                        function_reference.kind,
                    ) if isinstance(function_reference.node, MemberAccessTarget) else
                    SimpleFunctionReference(
                        f"{function_reference.node.__class__.__name__}.{function_reference.node.name}.line{function_reference.node.fromlineno}",
                        function_reference.kind,
                    )
                    for function_reference in function_references.writes
                },
                {
                    SimpleFunctionReference(
                        f"{function_reference.node.__class__.__name__}.{function_reference.node.name}.line{function_reference.node.member.fromlineno}",
                        function_reference.kind,
                    ) if isinstance(function_reference.node, MemberAccessValue) else
                    SimpleFunctionReference(
                        f"{function_reference.node.__class__.__name__}.{function_reference.node.name}.line{function_reference.node.fromlineno}",
                        function_reference.kind,
                    )
                    for function_reference in function_references.reads
                },
                {
                    SimpleFunctionReference(
                        f"{function_reference.node.__class__.__name__}.{function_reference.node.func.attrname}.line{function_reference.node.fromlineno}",
                        function_reference.kind,
                    ) if isinstance(function_reference.node.func, astroid.Attribute) else
                    SimpleFunctionReference(
                        f"{function_reference.node.__class__.__name__}.{function_reference.node.func.name}.line{function_reference.node.fromlineno}",
                        function_reference.kind,
                    )
                    for function_reference in function_references.calls
                },
            ),
        })

    return transformed_function_references


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
            astroid.FunctionDef(
                "local_func",
                lineno=1,
                col_offset=0,
                parent=astroid.ClassDef("A", lineno=2, col_offset=3),
            ),
            "A.local_func.1.0",
        ),
        (
            astroid.FunctionDef(
                "global_func",
                lineno=1,
                col_offset=0,
                parent=astroid.ClassDef("A", lineno=2, col_offset=3, parent=astroid.Module("numpy")),
            ),
            "numpy.global_func.1.0",
        ),
        (
            astroid.AssignName(
                "var1",
                lineno=1,
                col_offset=5,
                parent=astroid.FunctionDef("func1", lineno=1, col_offset=0),
            ),
            "func1.var1.1.5",
        ),
        (
            astroid.Name("var2", lineno=20, col_offset=0, parent=astroid.FunctionDef("func1", lineno=1, col_offset=0)),
            "func1.var2.20.0",
        ),
        (
            astroid.Name(
                "glob",
                lineno=20,
                col_offset=0,
                parent=astroid.FunctionDef(
                    "func1",
                    lineno=1,
                    col_offset=0,
                    parent=astroid.ClassDef("A", lineno=2, col_offset=3, parent=astroid.Module("numpy")),
                ),
            ),
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
    ],  # TODO: add AssignAttr, Import, ImportFrom, Call, Lambda, ListComp, MemberAccess
)
def test_calc_node_id(
    node: astroid.Module | astroid.ClassDef | astroid.FunctionDef | astroid.AssignName | astroid.Name,
    expected: str,
) -> None:
    result = calc_node_id(node)
    assert result.__str__() == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "Seminar Example"
            """
glob = 1
class A:
    def __init__(self):
        self.value = 10
        self.test = 20
    def f(self):
        var1 = 1
def g():
    var2 = 2
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope("GlobalVariable.AssignName.glob", []),
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.A",
                            [
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.__init__",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("InstanceVariable.MemberAccess.self.value", []),
                                        SimpleScope("InstanceVariable.MemberAccess.self.test", []),
                                    ],
                                    [],
                                    [],
                                ),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.f",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("LocalVariable.AssignName.var1", []),
                                    ],
                                    [],
                                    [],
                                ),
                            ],
                            ["FunctionDef.__init__", "FunctionDef.f"],
                            ["AssignAttr.value", "AssignAttr.test"],
                        ),
                        SimpleFunctionScope("GlobalVariable.FunctionDef.g",
                                            [SimpleScope("LocalVariable.AssignName.var2", [])], [], []),
                    ],
                ),
            ],
        ),
        (  # language=Python "Function Scope"
            """
def function_scope():
    res = 23
    return res
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleFunctionScope(
                            "GlobalVariable.FunctionDef.function_scope",
                            [SimpleScope("LocalVariable.AssignName.res", [])],
                            ["Name.res"],
                            []
                        ),
                    ],
                ),
            ],
        ),
        (  # language=Python "Function Scope with variable"
            """
var1 = 10
def function_scope():
    res = var1
    return res
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope("GlobalVariable.AssignName.var1", []),
                        SimpleFunctionScope(
                            "GlobalVariable.FunctionDef.function_scope",
                            [SimpleScope("LocalVariable.AssignName.res", [])],
                            ["Name.var1", "Name.res"],
                            []
                        ),
                    ],
                ),
            ],
        ),
        (  # language=Python "Function Scope with global variables"
            """
var1 = 10
var2 = 20
def function_scope():
    global var1, var2
    res = var1 + var2
    return res
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope("GlobalVariable.AssignName.var1", []),
                        SimpleScope("GlobalVariable.AssignName.var2", []),
                        SimpleFunctionScope(
                            "GlobalVariable.FunctionDef.function_scope",
                            [SimpleScope("LocalVariable.AssignName.res", [])],
                            ["Name.var1", "Name.var2", "Name.res"],
                            []
                        ),
                    ],
                ),
            ],
        ),
        (  # language=Python "Function Scope with Parameter"
            """
def function_scope(parameter):
    res = parameter
    return res
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleFunctionScope(
                            "GlobalVariable.FunctionDef.function_scope",
                            [
                                SimpleScope("Parameter.AssignName.parameter", []),
                                SimpleScope("LocalVariable.AssignName.res", []),
                            ],
                            ["Name.parameter", "Name.res"],
                            [],
                            ["AssignName.parameter"],
                        ),
                    ],
                ),
            ],
        ),
        (  # language=Python "Class Scope with class attribute and class function"
            """
class A:
    class_attr1 = 20

    def local_class_attr(self):
        var1 = A.class_attr1
        return var1
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.A",
                            [
                                SimpleScope("ClassVariable.AssignName.class_attr1", []),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.local_class_attr",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("LocalVariable.AssignName.var1", []),
                                    ],
                                    ["MemberAccessValue.A.class_attr1", "Name.var1"],
                                    [],
                                ),
                            ],
                            ["AssignName.class_attr1", "FunctionDef.local_class_attr"],
                            [],
                        ),
                    ],
                ),
            ],
        ),
        (  # language=Python "Class Scope with instance attribute and class function"
            """
class B:
    local_class_attr1 = 20
    local_class_attr2 = 30

    def __init__(self):
        self.instance_attr1 = 10

    def local_instance_attr(self):
        var1 = self.instance_attr1
        return var1
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.B",
                            [
                                SimpleScope("ClassVariable.AssignName.local_class_attr1", []),
                                SimpleScope("ClassVariable.AssignName.local_class_attr2", []),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.__init__",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("InstanceVariable.MemberAccess.self.instance_attr1", []),
                                    ],
                                    [],
                                    [],
                                ),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.local_instance_attr",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("LocalVariable.AssignName.var1", []),
                                    ],
                                    ["MemberAccessValue.self.instance_attr1", "Name.var1"],
                                    [],
                                ),
                            ],
                            [
                                "AssignName.local_class_attr1",
                                "AssignName.local_class_attr2",
                                "FunctionDef.__init__",
                                "FunctionDef.local_instance_attr",
                            ],
                            ["AssignAttr.instance_attr1"],
                        ),
                    ],
                ),
            ],
        ),
        (  # language=Python "Class Scope with instance attribute and module function"
            """
class B:
    def __init__(self):
        self.instance_attr1 = 10

def local_instance_attr():
    var1 = B().instance_attr1
    return var1
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.B",
                            [
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.__init__",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("InstanceVariable.MemberAccess.self.instance_attr1", []),
                                    ],
                                    [],
                                    [],
                                ),
                            ],
                            ["FunctionDef.__init__"],
                            ["AssignAttr.instance_attr1"],
                        ),
                        SimpleFunctionScope(
                            "GlobalVariable.FunctionDef.local_instance_attr",
                            [SimpleScope("LocalVariable.AssignName.var1", [])],
                            ["MemberAccessValue.B.instance_attr1", "Name.var1"],
                            ["Call.B"],
                        ),
                    ],
                ),
            ],
        ),
        (  # language=Python "Class Scope within Class Scope"
            """
class A:
    var1 = 10

    class B:
        var2 = 20
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.A",
                            [
                                SimpleScope("ClassVariable.AssignName.var1", []),
                                SimpleClassScope(
                                    "ClassVariable.ClassDef.B",
                                    [SimpleScope("ClassVariable.AssignName.var2", [])],
                                    ["AssignName.var2"],
                                    [],
                                ),
                            ],
                            ["AssignName.var1", "ClassDef.B"],
                            [],
                        ),
                    ],
                ),
            ],
        ),
        (  # language=Python "Class Scope with subclass"
            """
class A:
    var1 = 10

class X:
    var3 = 30

class B(A, X):
    var2 = 20
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.A",
                            [SimpleScope("ClassVariable.AssignName.var1", [])],
                            ["AssignName.var1"],
                            [],
                        ),
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.X",
                            [SimpleScope("ClassVariable.AssignName.var3", [])],
                            ["AssignName.var3"],
                            [],
                        ),
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.B",
                            [SimpleScope("ClassVariable.AssignName.var2", [])],
                            ["AssignName.var2"],
                            [],
                            ["ClassDef.A", "ClassDef.X"],
                        ),
                    ],
                ),
            ],
        ),
        (  # language=Python "Class Scope within Function Scope"
            """
def function_scope():
    var1 = 10

    class B:
        var2 = 20
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleFunctionScope(
                            "GlobalVariable.FunctionDef.function_scope",
                            [
                                SimpleScope("LocalVariable.AssignName.var1", []),
                                SimpleClassScope(
                                    "LocalVariable.ClassDef.B",
                                    [SimpleScope("ClassVariable.AssignName.var2", [])],
                                    ["AssignName.var2"],
                                    [],
                                ),
                            ],
                            [],
                            [],
                        ),
                    ],
                ),
            ],
        ),
        (  # language=Python "Function Scope within Function Scope"
            """
def function_scope():
    var1 = 10

    def local_function_scope():
        var2 = 20
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleFunctionScope(
                            "GlobalVariable.FunctionDef.function_scope",
                            [
                                SimpleScope("LocalVariable.AssignName.var1", []),
                                SimpleFunctionScope(
                                    "LocalVariable.FunctionDef.local_function_scope",
                                    [SimpleScope("LocalVariable.AssignName.var2", [])],
                                    [],
                                    []
                                ),
                            ],
                            [],
                            []
                        ),
                    ],
                ),
            ],
        ),
        (  # language=Python "Complex Scope"
            """
def function_scope():
    var1 = 10

    def local_function_scope():
        var2 = 20

        class LocalClassScope:
            var3 = 30

            def local_class_function_scope(self):
                var4 = 40
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleFunctionScope(
                            "GlobalVariable.FunctionDef.function_scope",
                            [
                                SimpleScope("LocalVariable.AssignName.var1", []),
                                SimpleFunctionScope(
                                    "LocalVariable.FunctionDef.local_function_scope",
                                    [
                                        SimpleScope("LocalVariable.AssignName.var2", []),
                                        SimpleClassScope(
                                            "LocalVariable.ClassDef.LocalClassScope",
                                            [
                                                SimpleScope("ClassVariable.AssignName.var3", []),
                                                SimpleFunctionScope(
                                                    "ClassVariable.FunctionDef.local_class_function_scope",
                                                    [
                                                        SimpleScope("Parameter.AssignName.self", []),
                                                        SimpleScope(
                                                            "LocalVariable.AssignName.var4",
                                                            [],
                                                        ),
                                                    ],
                                                    [],
                                                    []
                                                ),
                                            ],
                                            ["AssignName.var3", "FunctionDef.local_class_function_scope"],
                                            [],
                                        ),
                                    ],
                                    [],
                                    []
                                ),
                            ],
                            [],
                            []
                        ),
                    ],
                ),
            ],
        ),
        (  # language=Python "ASTWalker"
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

            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope("Import.ImportFrom.collections.abc.Callable", []),
                        SimpleScope("Import.ImportFrom.typing.Any", []),
                        SimpleScope("Import.Import.astroid", []),
                        SimpleScope("GlobalVariable.AssignName._EnterAndLeaveFunctions", []),
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.ASTWalker",
                            [
                                SimpleScope("ClassVariable.AssignName.additional_locals", []),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.__init__",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("Parameter.AssignName.handler", []),
                                        SimpleScope("InstanceVariable.MemberAccess.self._handler", []),
                                        SimpleScope("InstanceVariable.MemberAccess.self._cache", []),
                                    ],
                                    ["Name.handler",
                                     "Name._EnterAndLeaveFunctions"],
                                    [],
                                    ["AssignName.handler"],
                                ),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.walk",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("Parameter.AssignName.node", []),
                                    ],
                                    ["Name.node"],
                                    ["Call.__walk"],
                                    ["AssignName.node"]
                                ),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.__walk",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("Parameter.AssignName.node", []),
                                        SimpleScope("Parameter.AssignName.visited_nodes", []),
                                        SimpleScope("LocalVariable.AssignName.child_node", []),
                                    ],
                                    ["Name.node", "Name.visited_nodes", "Name.child_node"],
                                    ["Call.add", "Call.__enter", "Call.get_children", "Call.__walk", "Call.__leave"],
                                    ["AssignName.node", "AssignName.visited_nodes"]
                                ),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.__enter",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("Parameter.AssignName.node", []),
                                        SimpleScope("LocalVariable.AssignName.method", []),
                                    ],
                                    ["Name.node", "Name.method"],
                                    ["Call.__get_callbacks", "Call.method"],
                                    ["AssignName.node"]
                                ),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.__leave",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("Parameter.AssignName.node", []),
                                        SimpleScope("LocalVariable.AssignName.method", []),
                                    ],
                                    ["Name.node", "Name.method"],
                                    ["Call.__get_callbacks", "Call.methode"],
                                    ["AssignName.node"]
                                ),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.__get_callbacks",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("Parameter.AssignName.node", []),
                                        SimpleScope("LocalVariable.AssignName.klass", []),
                                        SimpleScope("LocalVariable.AssignName.methods", []),
                                        SimpleScope("LocalVariable.AssignName.handler", []),
                                        SimpleScope("LocalVariable.AssignName.class_name", []),
                                        SimpleScope("LocalVariable.AssignName.enter_method", []),
                                        SimpleScope("LocalVariable.AssignName.leave_method", []),
                                        SimpleScope("LocalVariable.AssignName.enter_method", []),
                                        SimpleScope("LocalVariable.AssignName.leave_method", []),
                                    ],
                                    ["Name.node", "MemberAccessValue.node.__class__", "Name.klass", "Name.methods",
                                     "MemberAccessVaalue.self._handler", "Name.handler", "Name.class_name",
                                     "Name.enter_method", "Name.leave_method"],
                                    ["Call.get", "Call.lower", "Call.getattr"],
                                    ["AssignName.node"]
                                ),
                            ],
                            [
                                "AssignName.additional_locals",
                                "FunctionDef.__init__",
                                "FunctionDef.walk",
                                "FunctionDef.__walk",
                                "FunctionDef.__enter",
                                "FunctionDef.__leave",
                                "FunctionDef.__get_callbacks",
                            ],
                            ["AssignAttr._handler", "AssignAttr._cache"],
                        ),
                    ],
                ),
            ],
        ),
        (  # language=Python "AssignName"
            """
a = "a"
            """,  # language=none
            [SimpleScope("Module", [SimpleScope("GlobalVariable.AssignName.a", [])])],
        ),
        (  # language=Python "List Comprehension in Module"
            """
nums = ["aaa", "bb", "ase"]
[len(num) for num in nums]
            """,  # language=none
            [SimpleScope("Module",
                         [
                             SimpleScope("GlobalVariable.AssignName.nums", []),
                             SimpleScope("ListComp", [SimpleScope("LocalVariable.AssignName.num", [])]),
                         ])],
        ),
        (  # language=Python "List Comprehension in Class"
            """
class A:
    nums = ["aaa", "bb", "ase"]
    x = [len(num) for num in nums]
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.A",
                            [
                                SimpleScope("ClassVariable.AssignName.nums", []),
                                SimpleScope("ClassVariable.AssignName.x", []),
                                SimpleScope("ListComp", [SimpleScope("LocalVariable.AssignName.num", [])]),
                            ],
                            ["AssignName.nums", "AssignName.x"],
                            [],
                            [],
                        ),
                    ],
                ),
            ],
        ),
        (  # language=Python "List Comprehension in Function"
            """
def fun():
    nums = ["aaa", "bb", "ase"]
    x = [len(num) for num in nums]
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleFunctionScope(
                            "GlobalVariable.FunctionDef.fun",
                            [
                                SimpleScope("LocalVariable.AssignName.nums", []),
                                SimpleScope("LocalVariable.AssignName.x", []),
                                SimpleScope("ListComp", [SimpleScope("LocalVariable.AssignName.num", [])]),
                            ],
                            [],
                            ["Call.len"],
                        ),
                    ],
                ),
            ],
        ),
        (  # language=Python "With Statement"
            """
file = "file.txt"
with file:
    a = 1
            """,  # language=none
            [SimpleScope("Module", [
                SimpleScope("GlobalVariable.AssignName.file", []),
                SimpleScope("GlobalVariable.AssignName.a", [])
            ])],
        ),
        (  # language=Python "With Statement File"
            """
file = "file.txt"
with open(file, "r") as f:
    a = 1
    f.read()
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleScope("GlobalVariable.AssignName.file", []),
                        SimpleScope("GlobalVariable.AssignName.f", []),
                        SimpleScope("GlobalVariable.AssignName.a", []),
                    ],
                ),
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
                SimpleScope(
                    "Module",
                    [
                        SimpleFunctionScope(
                            "GlobalVariable.FunctionDef.fun",
                            [
                                SimpleScope("LocalVariable.AssignName.f", []),
                                SimpleScope("LocalVariable.AssignName.text", []),
                            ],
                            [],
                            ["Call.open", "Call.read", "Call.print", "Call.close"],
                        ),
                    ],
                ),
            ],
        ),
        (  # language=Python "With Statement Class"
            """
class MyContext:
    def __enter__(self):
        print("Entering the context")
        return self

    def __exit__(self):
        print("Exiting the context")

with MyContext() as context:
    print("Inside the context")
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.MyContext",
                            [
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.__enter__",
                                    [SimpleScope("Parameter.AssignName.self", [])],
                                    [],
                                    ["Call.print"],
                                ),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.__exit__",
                                    [SimpleScope("Parameter.AssignName.self", [])],
                                    [],
                                    ["Call.print"],
                                ),
                            ],
                            ["FunctionDef.__enter__", "FunctionDef.__exit__"],
                            [],
                            [],
                        ),
                        SimpleScope("GlobalVariable.AssignName.context", []),
                    ],
                ),
            ],
        ),
        (  # language=Python "Lambda"
            """
lambda x, y: x + y
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleFunctionScope("GlobalVariable.Lambda",
                                            [SimpleScope("Parameter.AssignName.x", []),
                                             SimpleScope("Parameter.AssignName.y", [])],
                                            ["Name.x", "Name.y"],
                                            [],
                                            ["AssignName.x", "AssignName.y"]
                                            ),
                    ],
                ),
            ],
        ),
        (  # language=Python "Lambda"
            """
(lambda x, y: x + y)(10, 20)
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleFunctionScope("GlobalVariable.Lambda",
                                            [SimpleScope("Parameter.AssignName.x", []),
                                             SimpleScope("Parameter.AssignName.y", [])],
                                            ["Name.x", "Name.y"],
                                            [],
                                            ["AssignName.x", "AssignName.y"]
                                            ),
                    ],
                ),
            ],
        ),
        (  # language=Python "Lambda with name"
            """
double = lambda x: 2 * x
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleFunctionScope("GlobalVariable.Lambda.double",
                                            [SimpleScope("Parameter.AssignName.x", [])],
                                            ["Name.x"],
                                            [],
                                            ["AssignName.x"]
                                            ),
                    ],
                ),
            ],
        ),
    ],
    ids=[
        "Seminar Example",
        "Function Scope",
        "Function Scope with variable",
        "Function Scope with global variables",
        "Function Scope with Parameter",
        "Class Scope with class attribute and Class function",
        "Class Scope with instance attribute and Class function",
        "Class Scope with instance attribute and Modul function",
        "Class Scope within Class Scope",
        "Class Scope with subclass",
        "Class Scope within Function Scope",
        "Function Scope within Function Scope",
        "Complex Scope",
        "ASTWalker",
        "AssignName",
        "List Comprehension in Module",
        "List Comprehension in Class",
        "List Comprehension in Function",
        "With Statement",
        "With Statement File",
        "With Statement Function",
        "With Statement Class",
        "Lambda",
        "Lambda call",
        "Lambda with name",
    ],  # TODO: add tests for match, try except and generator expressions
)
def test_get_module_data_scope(code: str, expected: list[SimpleScope | SimpleClassScope]) -> None:
    scope = get_module_data(code).scope
    # assert result == expected
    transformed_result = [
        transform_scope_node(node) for node in scope
    ]  # The result is simplified to make the comparison easier
    assert transformed_result == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "ClassDef"
            """
class A:
    pass
            """,  # language=none
            {"A": SimpleClassScope("GlobalVariable.ClassDef.A", [], [], [], [])},
        ),
        (  # language=Python "ClassDef with class attribute"
            """
class A:
    var1 = 1
            """,  # language=none
            {
                "A": SimpleClassScope(
                    "GlobalVariable.ClassDef.A",
                    [SimpleScope("ClassVariable.AssignName.var1", [])],
                    ["AssignName.var1"],
                    [],
                    [],
                ),
            },
        ),
        (  # language=Python "ClassDef with multiple class attribute"
            """
class A:
    var1 = 1
    var2 = 2
            """,  # language=none
            {
                "A": SimpleClassScope(
                    "GlobalVariable.ClassDef.A",
                    [
                        SimpleScope("ClassVariable.AssignName.var1", []),
                        SimpleScope("ClassVariable.AssignName.var2", []),
                    ],
                    ["AssignName.var1", "AssignName.var2"],
                    [],
                    [],
                ),
            },
        ),
        (  # language=Python "ClassDef with multiple class attribute (same name)"
            """
class A:
    if True:
        var1 = 1
    else:
        var1 = 2
            """,  # language=none
            {
                "A": SimpleClassScope(
                    "GlobalVariable.ClassDef.A",
                    [
                        SimpleScope("ClassVariable.AssignName.var1", []),
                        SimpleScope("ClassVariable.AssignName.var1", []),
                    ],
                    ["AssignName.var1", "AssignName.var1"],
                    [],
                    [],
                ),
            },
        ),
        (  # language=Python "ClassDef with instance attribute"
            """
class A:
    def __init__(self):
        self.var1 = 1
            """,  # language=none
            {
                "A": SimpleClassScope(
                    "GlobalVariable.ClassDef.A",
                    [
                        SimpleFunctionScope(
                            "ClassVariable.FunctionDef.__init__",
                            [
                                SimpleScope("Parameter.AssignName.self", []),
                                SimpleScope("InstanceVariable.MemberAccess.self.var1", []),
                            ],
                            [],
                            []
                        ),
                    ],
                    ["FunctionDef.__init__"],
                    ["AssignAttr.var1"],
                    [],
                ),
            },
        ),
        (  # language=Python "ClassDef with multiple instance attributes (and type annotations)"
            """
class A:
    def __init__(self):
        self.var1: int = 1
        self.name: str = "name"
        self.state: bool = True
            """,  # language=none
            {
                "A": SimpleClassScope(
                    "GlobalVariable.ClassDef.A",
                    [
                        SimpleFunctionScope(
                            "ClassVariable.FunctionDef.__init__",
                            [
                                SimpleScope("Parameter.AssignName.self", []),
                                SimpleScope("InstanceVariable.MemberAccess.self.var1", []),
                                SimpleScope("InstanceVariable.MemberAccess.self.name", []),
                                SimpleScope("InstanceVariable.MemberAccess.self.state", []),
                            ],
                            [],
                            []
                        ),
                    ],
                    ["FunctionDef.__init__"],
                    ["AssignAttr.var1", "AssignAttr.name", "AssignAttr.state"],
                    [],
                ),
            },
        ),
        (  # language=Python "ClassDef with conditional instance attributes (instance attributes with the same name)"
            """
class A:
    def __init__(self):
        if True:
            self.var1 = 1
        else:
            self.var1 = 0
            """,  # language=none
            {
                "A": SimpleClassScope(
                    "GlobalVariable.ClassDef.A",
                    [
                        SimpleFunctionScope(
                            "ClassVariable.FunctionDef.__init__",
                            [
                                SimpleScope("Parameter.AssignName.self", []),
                                SimpleScope("InstanceVariable.MemberAccess.self.var1", []),
                                SimpleScope("InstanceVariable.MemberAccess.self.var1", []),
                            ],
                            [],
                            []
                        ),
                    ],
                    ["FunctionDef.__init__"],
                    ["AssignAttr.var1", "AssignAttr.var1"],
                    [],
                ),
            },
        ),
        (  # language=Python "ClassDef with class and instance attribute"
            """
class A:
    var1 = 1

    def __init__(self):
        self.var1 = 1
            """,  # language=none
            {
                "A": SimpleClassScope(
                    "GlobalVariable.ClassDef.A",
                    [
                        SimpleScope("ClassVariable.AssignName.var1", []),
                        SimpleFunctionScope(
                            "ClassVariable.FunctionDef.__init__",
                            [
                                SimpleScope("Parameter.AssignName.self", []),
                                SimpleScope("InstanceVariable.MemberAccess.self.var1", []),
                            ],
                            [],
                            []
                        ),
                    ],
                    ["AssignName.var1", "FunctionDef.__init__"],
                    ["AssignAttr.var1"],
                    [],
                ),
            },
        ),
        (  # language=Python "ClassDef with nested class"
            """
class A:
    class B:
        pass
            """,  # language=none
            {
                "A": SimpleClassScope(
                    "GlobalVariable.ClassDef.A",
                    [SimpleClassScope("ClassVariable.ClassDef.B", [], [], [], [])],
                    ["ClassDef.B"],
                    [],
                    [],
                ),
                "B": SimpleClassScope("ClassVariable.ClassDef.B", [], [], [], []),
            },
        ),
        (  # language=Python "Multiple ClassDef"
            """
class A:
    pass

class B:
    pass
            """,  # language=none
            {
                "A": SimpleClassScope("GlobalVariable.ClassDef.A", [], [], [], []),
                "B": SimpleClassScope("GlobalVariable.ClassDef.B", [], [], [], []),
            },
        ),
        (  # language=Python "ClassDef with superclass"
            """
class A:
    pass

class B(A):
    pass
            """,  # language=none
            {
                "A": SimpleClassScope("GlobalVariable.ClassDef.A", [], [], [], []),
                "B": SimpleClassScope("GlobalVariable.ClassDef.B", [], [], [], ["ClassDef.A"]),
            },
        ),
    ],
    ids=[
        "ClassDef",
        "ClassDef with class attribute",
        "ClassDef with multiple class attribute",
        "ClassDef with conditional class attribute (same name)",
        "ClassDef with instance attribute",
        "ClassDef with multiple instance attributes (and type annotations)",
        "ClassDef with conditional instance attributes (instance attributes with same name)",
        "ClassDef with class and instance attribute",
        "ClassDef with nested class",
        "Multiple ClassDef",
        "ClassDef with super class",
    ],
)
def test_get_module_data_classes(code: str, expected: dict[str, SimpleClassScope]) -> None:
    classes = get_module_data(code).classes

    transformed_classes = {
        klassname: transform_scope_node(klass) for klassname, klass in classes.items()
    }  # The result is simplified to make the comparison easier
    assert transformed_classes == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "Trivial function"
            """
def f():
    pass
            """,  # language=none
            {
                "f": [SimpleFunctionScope("GlobalVariable.FunctionDef.f", [], [], [])]
            }
        ),
        (  # language=Python "Function with child"
            """
def f():
    var1 = 1
            """,  # language=none
            {
                "f": [SimpleFunctionScope("GlobalVariable.FunctionDef.f",
                                          [SimpleScope("LocalVariable.AssignName.var1", [])], [], [])]
            }
        ),
        (  # language=Python "Function with parameter"
            """
def f(name):
    var1 = name
            """,  # language=none
            {
                "f": [SimpleFunctionScope("GlobalVariable.FunctionDef.f",
                                          [SimpleScope("Parameter.AssignName.name", []),
                                           SimpleScope("LocalVariable.AssignName.var1", [])],
                                          ["Name.name"],
                                          [],
                                          ["AssignName.name"]
                                          )]
            }
        ),
        (  # language=Python "Function with values"
            """
def f():
    name = "name"
    var1 = name
            """,  # language=none
            {
                "f": [SimpleFunctionScope("GlobalVariable.FunctionDef.f",
                                          [SimpleScope("LocalVariable.AssignName.name", []),
                                           SimpleScope("LocalVariable.AssignName.var1", [])], ["Name.name"], [])]
            }
        ),
        (  # language=Python "Function with return"
            """
def f():
    var1 = 1
    return var1
            """,  # language=none
            {
                "f": [SimpleFunctionScope("GlobalVariable.FunctionDef.f",
                                          [SimpleScope("LocalVariable.AssignName.var1", [])], ["Name.var1"], [])]
            }
        ),
        (  # language=Python "Function with nested return"
            """
def f(a, b):
    var1 = 1
    return a + b + var1
            """,  # language=none
            {
                "f": [SimpleFunctionScope("GlobalVariable.FunctionDef.f",
                                          [SimpleScope("Parameter.AssignName.a", []),
                                           SimpleScope("Parameter.AssignName.b", []),
                                           SimpleScope("LocalVariable.AssignName.var1", [])],
                                          ["Name.a", "Name.b", "Name.var1"],
                                          [],
                                          ["AssignName.a", "AssignName.b"]
                                          )]
            }
        ),
        (  # language=Python "Function with nested names"
            """
def f(a, b):
    var1 = 1
    var2 = a + b + var1
    return var2
            """,  # language=none
            {
                "f": [SimpleFunctionScope("GlobalVariable.FunctionDef.f",
                                          [
                                              SimpleScope("Parameter.AssignName.a", []),
                                              SimpleScope("Parameter.AssignName.b", []),
                                              SimpleScope("LocalVariable.AssignName.var1", []),
                                              SimpleScope("LocalVariable.AssignName.var2", [])
                                          ],
                                          ["Name.a", "Name.b", "Name.var1", "Name.var2"],
                                          [],
                                          ["AssignName.a", "AssignName.b"]
                                          )]
            }
        ),
        (  # language=Python "Function with call"
            """
def f():
    f()
            """,  # language=none
            {
                "f": [SimpleFunctionScope("GlobalVariable.FunctionDef.f", [], [], ["Call.f"])]
            }
        ),
        (  # language=Python "Function with same name"
            """
def f():
    f()

def f():
    pass
            """,  # language=none
            {
                "f": [SimpleFunctionScope("GlobalVariable.FunctionDef.f", [], [], ["Call.f"]),
                      SimpleFunctionScope("GlobalVariable.FunctionDef.f", [], [], [])]
            }
        ),
    ],
    ids=[
        "Trivial function",
        "Function with child",
        "Function with parameter",
        "Function with values",
        "Function with return",
        "Function with nested return",
        "Function with nested names",
        "Function with call",
        "Function with same name",
    ]
)
def test_get_module_data_functions(code: str, expected: dict[str, list[str]]) -> None:
    functions = get_module_data(code).functions
    transformed_functions = {
        fun_name: [transform_scope_node(fun) for fun in fun_list] for fun_name, fun_list in functions.items()
    }  # The result is simplified to make the comparison easier

    assert transformed_functions == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "No global variables"
            """
def f():
    pass
            """,  # language=none
            set(),
        ),
        (  # language=Python "Variable on Module Scope"
            """
var1 = 10
            """,  # language=none
            {"var1"},
        ),
        (  # language=Python "Multiple Variables on Module Scope"
            """
var1 = 10
var2 = 20
var3 = 30
            """,  # language=none
            {"var1", "var2", "var3"},
        ),
    ],
    ids=[
        "No global variables",
        "Variable on Module Scope",
        "Multiple Variables on Module Scope",
    ]
)
def test_get_module_data_globals(code: str, expected: str) -> None:
    globs = get_module_data(code).global_variables
    transformed_globs = {f"{glob}" for glob in globs}  # The result is simplified to make the comparison easier
    assert transformed_globs == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "parameter in function scope"
            """
def local_parameter(pos_arg):
    return 2 * pos_arg
            """,  # language= None
            {"local_parameter": ["pos_arg"]},
        ),
        (  # language=Python "parameter in function scope with keyword only"
            """
def local_parameter(*, key_arg_only):
    return 2 * key_arg_only
            """,  # language= None
            {"local_parameter": ["key_arg_only"]},
        ),
        (  # language=Python "parameter in function scope with positional only"
            """
def local_parameter(pos_arg_only, /):
    return 2 * pos_arg_only
            """,  # language= None
            {"local_parameter": ["pos_arg_only"]},
        ),
        (  # language=Python "parameter in function scope with default value"
            """
def local_parameter(def_arg=10):
    return def_arg
            """,  # language= None
            {"local_parameter": ["def_arg"]},
        ),
        (  # language=Python "parameter in function scope with type annotation"
            """
def local_parameter(def_arg: int):
    return def_arg
            """,  # language= None
            {"local_parameter": ["def_arg"]},
        ),
        (  # language=Python "parameter in function scope with *args"
            """
def local_parameter(*args):
    return args
            """,  # language= None
            {"local_parameter": ["args"]},
        ),
        (  # language=Python "parameter in function scope with **kwargs"
            """
def local_parameter(**kwargs):
    return kwargs
            """,  # language= None
            {"local_parameter": ["kwargs"]},
        ),
        (  # language=Python "parameter in function scope with *args and **kwargs"
            """
def local_parameter(*args, **kwargs):
    return args, kwargs
            """,  # language= None
            {"local_parameter": ["args", "kwargs"]},
        ),
        (  # language=Python "two parameters in function scope"
            """
def local_double_parameter(a, b):
    return a, b
            """,  # language= None
            {"local_double_parameter": ["a", "b"]},
        ),
        (  # language=Python "two parameters in function scope"
            """
def local_parameter1(a):
    return a

def local_parameter2(a):
    return a
            """,  # language= None
            {"local_parameter1": ["a"], "local_parameter2": ["a"]},
        ),
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
        "two parameters in function scope",
        "two functions with same parameter name"
    ],
)
def test_get_module_data_parameters(code: str, expected: str) -> None:
    parameters = get_module_data(code).parameters
    transformed_parameters = {
        fun_name.name: [f"{param.name}" for param in param_list[1]] for fun_name, param_list in parameters.items()
    }
    assert transformed_parameters == expected


@pytest.mark.parametrize(
    ("code", "expected"),  # expected is a tuple of (value_nodes, target_nodes)
    [
        (  # Assign
            """
                def variable():
                    var1 = 20
            """,
            ({}, {"var1": "AssignName.var1"}),
        ),
        (  # Assign Parameter
            """
                def parameter(a):
                    var1 = a
            """,
            ({"a": "Name.a"}, {"var1": "AssignName.var1", "a": "AssignName.a"}),
        ),
        (  # Global unused
            """
                def glob():
                    global glob1
            """,
            ({}, {}),
        ),
        (  # Global and Assign
            """
                def glob():
                    global glob1
                    var1 = glob1
            """,
            ({"glob1": "Name.glob1"}, {"var1": "AssignName.var1"}),
        ),
        (  # Assign Class Attribute
            """
                def class_attr():
                    var1 = A.class_attr
            """,
            ({"A": "Name.A", "A.class_attr": "MemberAccessValue.A.class_attr"}, {"var1": "AssignName.var1"}),
        ),
        (  # Assign Instance Attribute
            """
                def instance_attr():
                    b = B()
                    var1 = b.instance_attr
            """,
            (
                {"b": "Name.b", "b.instance_attr": "MemberAccessValue.b.instance_attr"},
                {"b": "AssignName.b", "var1": "AssignName.var1"},
            ),
        ),
        (  # Assign MemberAccessValue
            """
                def chain():
                    var1 = test.instance_attr.field.next_field
            """,
            (
                {
                    "test": "Name.test",
                    "test.instance_attr": "MemberAccessValue.test.instance_attr",
                    "test.instance_attr.field": "MemberAccessValue.test.instance_attr.field",
                    "test.instance_attr.field.next_field": "MemberAccessValue.test.instance_attr.field.next_field",
                },
                {"var1": "AssignName.var1"},
            ),
        ),
        (  # Assign MemberAccessTarget
            """
                def chain_reversed():
                    test.instance_attr.field.next_field = var1
            """,
            (
                {"var1": "Name.var1"},
                {
                    "test": "Name.test",
                    "test.instance_attr": "MemberAccessTarget.test.instance_attr",
                    "test.instance_attr.field": "MemberAccessTarget.test.instance_attr.field",
                    "test.instance_attr.field.next_field": "MemberAccessTarget.test.instance_attr.field.next_field",
                },
            ),
        ),
        (  # AssignAttr
            """
                def assign_attr():
                    a.res = 1
            """,
            ({}, {"a": "Name.a", "a.res": "MemberAccessTarget.a.res"}),
        ),
        (  # AugAssign
            """
                def aug_assign():
                    var1 += 1
            """,
            ({}, {"var1": "AssignName.var1"}),
        ),
        (  # Return
            """
                def assign_return():
                    return var1
            """,
            ({"var1": "Name.var1"}, {}),
        ),
        (  # While
            """
                def while_loop():
                    while var1 > 0:
                        do_something()
            """,
            ({"var1": "Name.var1"}, {}),
        ),
        (  # For
            """
                def for_loop():
                    for var1 in range(10):
                        do_something()
            """,
            ({}, {"var1": "AssignName.var1"}),
        ),
        (  # If
            """
                def if_state():
                    if var1 > 0:
                        do_something()
            """,
            ({"var1": "Name.var1"}, {}),
        ),
        (  # If Else
            """
                def if_else_state():
                    if var1 > 0:
                        do_something()
                    else:
                        do_something_else()
            """,
            ({"var1": "Name.var1"}, {}),
        ),
        (  # If Elif
            """
                def if_elif_state():
                    if var1 & True:
                        do_something()
                    elif var1 | var2:
                        do_something_else()
            """,
            ({"var1": "Name.var1", "var2": "Name.var2"}, {}),
        ),
        (  # Try Except Finally
            """
                try:
                    result = num1 / num2
                except ZeroDivisionError as error:
                    error
                finally:
                    final = num3
            """,
            (
                {"error": "Name.error", "num1": "Name.num1", "num2": "Name.num2", "num3": "Name.num3"},
                {"error": "AssignName.error", "final": "AssignName.final", "result": "AssignName.result"},
            ),
        ),
        (  # AnnAssign
            """
                def ann_assign():
                    var1: int = 10
            """,
            ({}, {"var1": "AssignName.var1"}),
        ),
        (  # FuncCall
            """
                def func_call():
                    var1 = func(var2)
            """,
            ({"var2": "Name.var2"}, {"var1": "AssignName.var1"}),
        ),
        (  # FuncCall Parameter
            """
                def func_call_par(param):
                    var1 = param + func(param)
            """,
            ({"param": "Name.param"}, {"param": "AssignName.param", "var1": "AssignName.var1"}),
        ),
        (  # BinOp
            """
                def bin_op():
                    var1 = 20 + var2
            """,
            ({"var2": "Name.var2"}, {"var1": "AssignName.var1"}),
        ),
        (  # BoolOp
            """
                def bool_op():
                    var1 = True and var2
            """,
            ({"var2": "Name.var2"}, {"var1": "AssignName.var1"}),
        ),
    ],
    ids=[
        "Assign",
        "Assign Parameter",
        "Global unused",
        "Global and Assign",
        "Assign Class Attribute",
        "Assign Instance Attribute",
        "Assign MemberAccessValue",
        "Assign MemberAccessTarget",
        "AssignAttr",
        "AugAssign",
        "Return",
        "While",
        "For",
        "If",
        "If Else",
        "If Elif",
        "Try Except Finally",
        "AnnAssign",
        "FuncCall",
        "FuncCall Parameter",
        "BinOp",
        "BoolOp",
    ],
)
def test_get_module_data_value_and_target_nodes(code: str, expected: str) -> None:
    module_data = get_module_data(code)
    value_nodes = module_data.value_nodes
    target_nodes = module_data.target_nodes

    # assert (value_nodes, target_nodes) == expected
    value_nodes_transformed = transform_value_nodes(value_nodes)
    target_nodes_transformed = transform_target_nodes(target_nodes)
    assert (value_nodes_transformed, target_nodes_transformed) == expected


@pytest.mark.parametrize(("code", "expected"), [])
def test_get_module_data_function_calls(code: str, expected: str) -> None:
    function_calls = get_module_data(code).function_calls
    raise NotImplementedError("TODO: implement test")
    assert function_calls == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "internal stuff"
            """
b = 1
c = 2
d = 3
def g():
    pass

def f():
    # global b  # TODO: [LATER] to detect this case, we need to collect the global statements on function level
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
                    {
                        SimpleFunctionReference("AssignName.b.line11", "NonLocalVariableWrite"),
                        SimpleFunctionReference("AssignName.b.line14", "NonLocalVariableWrite"),
                    },
                    {
                        SimpleFunctionReference("Name.c.line13", "NonLocalVariableRead"),
                        SimpleFunctionReference("Name.d.line14", "NonLocalVariableRead"),
                    },
                    {
                        SimpleFunctionReference("Call.g.line15", "Call"),
                        SimpleFunctionReference("Call.open.line16", "Call"),
                    },
                ),
                ".g.5.0": SimpleReasons("g", set(), set(), set()),
            },
        ),
        (  # language=Python "control flow statements"
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
                        SimpleFunctionReference("AssignName.c.line10", "NonLocalVariableWrite"),
                        SimpleFunctionReference("AssignName.b.line13", "NonLocalVariableWrite"),
                    },
                    # {
                    #     SimpleFunctionReference("Name.b.line7", "NonLocalVariableRead"),
                    # }
                ),
            },
        ),
        (  # language=Python "class attribute"
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
                        SimpleFunctionReference("MemberAccessTarget.a.class_attr1.line7", "MemberAccessTarget"),
                    },
                    set(),
                    {
                        SimpleFunctionReference("Call.A.line6", "Call"),
                    }
                ),
                ".g.9.0": SimpleReasons(
                    "g",
                    set(),
                    {
                        SimpleFunctionReference("MemberAccessValue.a.class_attr1.line11", "MemberAccessValue"),
                    },
                    {
                        SimpleFunctionReference("Call.A.line10", "Call"),
                    }
                ),
            },
        ),
        (  # language=Python "instance attribute"
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
    c = a.instance_attr1  # NonLocalVariableWrite  # TODO [Later] we should detect that this is a local variable

def g2(x):
    c = x.instance_attr1  # NonLocalVariableRead

def g3():
    global b
    c = b.instance_attr1  # NonLocalVariableRead
            """,  # language=none
            {
                ".__init__.3.4": SimpleReasons(
                    "__init__"
                ),
                ".f1.6.0": SimpleReasons(
                    "f1", {
                        SimpleFunctionReference("MemberAccessTarget.a.instance_attr1.line8", "MemberAccessTarget"),
                    },
                    set(),
                    {SimpleFunctionReference("Call.A.line7", "Call")}
                ),
                ".f2.11.0": SimpleReasons(
                    "f2",
                    {
                        SimpleFunctionReference("MemberAccessTarget.x.instance_attr1.line12", "MemberAccessTarget"),
                    },
                ),
                ".f3.14.0": SimpleReasons(
                    "f3",
                    {
                        SimpleFunctionReference("MemberAccessTarget.b.instance_attr1.line16", "MemberAccessTarget"),
                    },
                ),
                ".g1.18.0": SimpleReasons(
                    "g1", set(), {
                        SimpleFunctionReference("MemberAccessValue.a.instance_attr1.line20", "MemberAccessValue"),
                    }, {SimpleFunctionReference("Call.A.line19", "Call")}
                ),
                ".g2.22.0": SimpleReasons(
                    "g2",
                    set(),
                    {
                        SimpleFunctionReference("MemberAccessValue.x.instance_attr1.line23", "MemberAccessValue"),
                    },
                ),
                ".g3.25.0": SimpleReasons(
                    "g3",
                    set(),
                    {
                        SimpleFunctionReference("MemberAccessValue.b.instance_attr1.line27", "MemberAccessValue"),
                    },
                ),
            },
        ),
        (  # language=Python "chained attributes"
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
                ".__init__.3.4": SimpleReasons(
                    "__init__"
                ),
                ".set_name.6.4": SimpleReasons(
                    "set_name",
                    {SimpleFunctionReference("MemberAccessTarget.self.name.line7", "MemberAccessTarget")}
                ),
                ".f.12.0": SimpleReasons(
                    "f",
                    set(),
                    {
                        SimpleFunctionReference("MemberAccessValue.b.upper_class.name.line14", "MemberAccessValue"),
                        SimpleFunctionReference("MemberAccessValue.b.upper_class.line14", "MemberAccessValue"),
                        SimpleFunctionReference("MemberAccessValue.b.upper_class.line15", "MemberAccessValue"),
                    },
                    {
                        SimpleFunctionReference("Call.B.line13", "Call"),
                        SimpleFunctionReference("Call.set_name.line15", "Call"),
                    }
                ),
            }
        ),
        (  # language=Python "chained class function call"
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
                ".__init__.3.4": SimpleReasons(
                    "__init__"
                ),
                ".f.6.4": SimpleReasons(
                    "f", set(), set(), set()
                ),
                ".g.12.0": SimpleReasons(
                    "g",
                    set(),
                    set(),
                    {
                        SimpleFunctionReference("Call.A.line13", "Call"),
                        SimpleFunctionReference("Call.f.line13", "Call"),
                    }
                ),
            }
        ),
        (  # language=Python "two classes with same attribute name"
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
                ".__init__.5.4": SimpleReasons(
                    "__init__"
                ),
                ".__init__.11.4": SimpleReasons(
                    "__init__"
                ),
                ".f.14.0": SimpleReasons(
                    "f",
                    set(),
                    {
                        SimpleFunctionReference("MemberAccessValue.a.name.line17", "MemberAccessValue"),
                        SimpleFunctionReference("MemberAccessValue.b.name.line18", "MemberAccessValue"),
                    },
                    {
                        SimpleFunctionReference("Call.A.line15", "Call"),
                        SimpleFunctionReference("Call.B.line16", "Call"),
                    }
                )
            }
        ),
        (  # language=Python "multiple classes with same function name - same signature"
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
    x = A.add(1, 2)
    y = B.add(1, 2)
    if x == y:
        pass
            """,  # language=none
            {
                ".add.6.4": SimpleReasons(
                    "add",
                    set(),
                    {
                        SimpleFunctionReference("Name.z.line8", "NonLocalVariableRead")
                    },
                    set()
                ),
                ".add.12.4": SimpleReasons(
                    "add",
                ),
                ".f.15.0": SimpleReasons(
                    "f",
                    set(),
                    set(),
                    {
                        SimpleFunctionReference("Call.add.line16", "Call"),
                        SimpleFunctionReference("Call.add.line17", "Call"),
                    }
                )
            }
        ),  # since we only return a list of all possible references, we can't distinguish between the two functions
        (  # language=Python "multiple classes with same function name - different signature"
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
                        SimpleFunctionReference("Call.add.line13", "Call"),
                        SimpleFunctionReference("Call.add.line14", "Call"),
                    }
                )
            }
        ),  # TODO: [LATER] we should detect the different signatures
    ],
    ids=[
        "internal stuff",
        "control flow statements",
        "class attribute",
        "instance attribute",
        "chained attributes",
        "chained class function call",
        "two classes with same attribute name",
        "multiple classes with same function name - same signature",
        # TODO: Fix the bug where z is not detected as NonLocalVariableRead
        "multiple classes with same function name - different signature",
        # TODO: [LATER] we should detect the different signatures
    ],
)
def test_get_module_data_function_references(code: str, expected: dict[str, SimpleReasons]) -> None:
    function_references = get_module_data(code).function_references

    transformed_function_references = transform_function_references(function_references)
    # assert function_references == expected

    assert transformed_function_references == expected

# TODO: testcases for cyclic calls and recursive calls
