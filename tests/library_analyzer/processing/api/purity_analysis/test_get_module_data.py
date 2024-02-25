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
    super_class : list[str] | None
        The list of super classes, if the class has any.
    """

    class_variables: list[str]
    instance_variables: list[str]
    super_class: list[str] | None = None


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
    parameters : list[str]
        The list of parameter nodes used in the function as string.
    globals : list[str]
        The list of global nodes used in the function as string.
    """

    targets: list[str]
    values: list[str]
    calls: list[str]
    parameters: list[str] = field(default_factory=list)
    globals: list[str] = field(default_factory=list)


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
                    c_str = to_string_class(c.node.node)
                    if c_str is not None:
                        instance_vars_transformed.append(
                            c_str)  # type: ignore[misc] # it is not possible that c_str is None
            for child in node.class_variables.values():
                for c in child:
                    c_str = to_string_class(c.node)
                    if c_str is not None:
                        class_vars_transformed.append(
                            c_str)  # type: ignore[misc] # it is not possible that c_str is None
            if node.super_classes:
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
                super_classes_transformed if super_classes_transformed else None,
            )
        if isinstance(node, FunctionScope):
            targets_transformed = []
            values_transformed = []
            calls_transformed = []
            parameters_transformed = []
            globals_transformed = []

            for target in node.target_symbols.values():
                for t in target:
                    string = to_string_func(t.node)
                    if string not in targets_transformed:
                        targets_transformed.append(string)

            for value in node.value_references.values():
                for v in value:
                    string = to_string_func(v.node)
                    if string not in values_transformed:
                        values_transformed.append(string)
            for call in node.call_references.values():
                for c in call:
                    string = to_string_func(c.node)
                    if string not in calls_transformed:
                        calls_transformed.append(string)
            for parameter in node.parameters.values():
                parameters_transformed.append(to_string_func(parameter.node))
            for globs in node.globals_used.values():
                for g in globs:
                    globals_transformed.append(to_string_func(g.node))

            return SimpleFunctionScope(
                to_string(node.symbol),
                [transform_scope_node(child) for child in node.children],
                targets_transformed,
                values_transformed,
                calls_transformed,
                parameters_transformed,
                globals_transformed,
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
    elif isinstance(symbol.node, astroid.ListComp | astroid.SetComp | astroid.DictComp | astroid.GeneratorExp | astroid.TryExcept | astroid.TryFinally | astroid.With):
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
        None if the node is a Lambda, TryExcept, TryFinally or a Comprehension instance.
    """
    if isinstance(node, astroid.AssignAttr):
        return f"{node.__class__.__name__}.{node.attrname}"
    elif isinstance(node, astroid.AssignName | astroid.FunctionDef | astroid.ClassDef):
        return f"{node.__class__.__name__}.{node.name}"
    elif isinstance(node, astroid.Lambda | astroid.TryExcept | astroid.TryFinally | astroid.ListComp | astroid.SetComp | astroid.DictComp | astroid.GeneratorExp):
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
            attribute_names.append(member_access.member)
        else:
            attribute_names.append(member_access.member)
        member_access = member_access.receiver
    if isinstance(member_access, astroid.Name):
        attribute_names.append(member_access.name)

    return ".".join(reversed(attribute_names))


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
                                    ["AssignName.self", "Name.self", "MemberAccessTarget.self.value", "MemberAccessTarget.self.test"],
                                    [],
                                    [],
                                    ["AssignName.self"],
                                ),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.f",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("LocalVariable.AssignName.var1", []),
                                    ],
                                    ["AssignName.self", "AssignName.var1"],
                                    [],
                                    [],
                                    ["AssignName.self"]
                                ),
                            ],
                            ["FunctionDef.__init__", "FunctionDef.f"],
                            ["AssignAttr.value", "AssignAttr.test"],
                        ),
                        SimpleFunctionScope("GlobalVariable.FunctionDef.g",
                                            [SimpleScope("LocalVariable.AssignName.var2", [])],
                                            ["AssignName.var2"],
                                            [],
                                            []),
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
                            ["AssignName.res"],
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
                            ["AssignName.res"],
                            ["Name.var1", "Name.res"],
                            [],
                            [],
                            ["AssignName.var1"],
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
                            ["AssignName.res"],
                            ["Name.var1", "Name.var2", "Name.res"],
                            [],
                            [],
                            ["AssignName.var1", "AssignName.var2"],
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
                            ["AssignName.parameter", "AssignName.res"],
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
                                    ["AssignName.self", "AssignName.var1"],
                                    ["MemberAccessValue.A.class_attr1", "Name.A", "Name.var1"],
                                    [],
                                    ["AssignName.self"]
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
                                    ["AssignName.self", "Name.self", "MemberAccessTarget.self.instance_attr1"],
                                    [],
                                    [],
                                    ["AssignName.self"]
                                ),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.local_instance_attr",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("LocalVariable.AssignName.var1", []),
                                    ],
                                    ["AssignName.self", "AssignName.var1"],
                                    ["MemberAccessValue.self.instance_attr1", "Name.self", "Name.var1"],
                                    [],
                                    ["AssignName.self"]
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
                                    ["AssignName.self", "Name.self","MemberAccessTarget.self.instance_attr1"],
                                    [],
                                    [],
                                    ["AssignName.self"]
                                ),
                            ],
                            ["FunctionDef.__init__"],
                            ["AssignAttr.instance_attr1"],
                        ),
                        SimpleFunctionScope(
                            "GlobalVariable.FunctionDef.local_instance_attr",
                            [SimpleScope("LocalVariable.AssignName.var1", [])],
                            ["AssignName.var1"],
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
                            ["AssignName.var1"],
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
                                    ["AssignName.var2"],
                                    [],
                                    []
                                ),
                            ],
                            ["AssignName.var1"],
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
                                                    ["AssignName.self", "AssignName.var4"],
                                                    [],
                                                    [],
                                                    ["AssignName.self"]
                                                ),
                                            ],
                                            ["AssignName.var3", "FunctionDef.local_class_function_scope"],
                                            [],
                                        ),
                                    ],
                                    ["AssignName.var2"],
                                    [],
                                    [],
                                    []
                                ),
                            ],
                            ["AssignName.var1"],
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
                                    ["AssignName.self", "Name.self", "AssignName.handler", "MemberAccessTarget.self._handler", "MemberAccessTarget.self._cache"],
                                    ["Name.handler"],
                                    [],
                                    ["AssignName.self", "AssignName.handler"],
                                ),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.walk",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("Parameter.AssignName.node", []),
                                    ],
                                    ["AssignName.self", "AssignName.node"],
                                    ["MemberAccessValue.self.__walk", "Name.self", "Name.node"],
                                    ["Call.__walk", "Call.set"],
                                    ["AssignName.self", "AssignName.node"]
                                ),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.__walk",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("Parameter.AssignName.node", []),
                                        SimpleScope("Parameter.AssignName.visited_nodes", []),
                                        SimpleScope("LocalVariable.AssignName.child_node", []),
                                    ],
                                    ["AssignName.self", "AssignName.node", "AssignName.visited_nodes", "AssignName.child_node"],
                                    ["Name.node", "Name.visited_nodes", "MemberAccessValue.visited_nodes.add",
                                     "MemberAccessValue.self.__enter", "Name.self", "MemberAccessValue.node.get_children", "MemberAccessValue.self.__walk",
                                      "Name.child_node", "MemberAccessValue.self.__leave"],
                                    ["Call.AssertionError", "Call.add", "Call.__enter", "Call.get_children", "Call.__walk", "Call.__leave"],
                                    ["AssignName.self", "AssignName.node", "AssignName.visited_nodes"]
                                ),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.__enter",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("Parameter.AssignName.node", []),
                                        SimpleScope("LocalVariable.AssignName.method", []),
                                    ],
                                    ["AssignName.self", "AssignName.node", "AssignName.method"],
                                    ["MemberAccessValue.self.__get_callbacks", "Name.self", "Name.node", "Name.method"],
                                    ["Call.__get_callbacks", "Call.method"],
                                    ["AssignName.self", "AssignName.node"]
                                ),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.__leave",
                                    [
                                        SimpleScope("Parameter.AssignName.self", []),
                                        SimpleScope("Parameter.AssignName.node", []),
                                        SimpleScope("LocalVariable.AssignName.method", []),
                                    ],
                                    ["AssignName.self", "AssignName.node", "AssignName.method"],
                                    ["MemberAccessValue.self.__get_callbacks", "Name.self", "Name.node", "Name.method"],
                                    ["Call.__get_callbacks", "Call.method"],
                                    ["AssignName.self", "AssignName.node"]
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
                                    ["AssignName.self", "AssignName.node", "AssignName.klass", "AssignName.methods",
                                     "AssignName.handler", "AssignName.class_name", "AssignName.enter_method",
                                     "AssignName.leave_method", "MemberAccessTarget.self._cache"],
                                    ["MemberAccessValue.node.__class__", "Name.node", "MemberAccessValue.self._cache.get",
                                     "MemberAccessValue.self._cache", "Name.self", "Name.klass", "Name.methods",
                                     "MemberAccessValue.self._handler", "MemberAccessValue.klass.__name__.lower",
                                     "MemberAccessValue.klass.__name__", "Name.handler", "Name.class_name",
                                     "Name.enter_method", "Name.leave_method"],
                                    ["Call.get", "Call.lower", "Call.getattr"],
                                    ["AssignName.self", "AssignName.node"],
                                    []
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
        (  # language=Python "Multiple AssignName"
            """
a = b = c = 1
            """,  # language=none
            [SimpleScope("Module", [SimpleScope("GlobalVariable.AssignName.a", []),
                                    SimpleScope("GlobalVariable.AssignName.b", []),
                                    SimpleScope("GlobalVariable.AssignName.c", [])])],
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
                            ["AssignName.nums", "AssignName.x"],
                            [],
                            ["Call.len"],
                        ),
                    ],
                ),
            ],
        ),
        (  # language=Python "Dict Comprehension in Module"
            """
nums = [1, 2, 3, 4]
{num: num*num for num in nums}
            """,  # language=none
            [SimpleScope("Module",
                         [
                             SimpleScope("GlobalVariable.AssignName.nums", []),
                             SimpleScope("DictComp", [SimpleScope("LocalVariable.AssignName.num", [])]),
                         ])],
        ),
        (  # language=Python "Set Comprehension in Module"
            """
nums = [1, 2, 3, 4]
{num*num for num in nums if num % 2 == 0}
            """,  # language=none
            [SimpleScope("Module",
                         [
                             SimpleScope("GlobalVariable.AssignName.nums", []),
                             SimpleScope("SetComp", [SimpleScope("LocalVariable.AssignName.num", [])]),
                         ])],
        ),
        (  # language=Python "Generator Expression in Module"
            """
(num*num for num in range(10))
            """,  # language=none
            [SimpleScope("Module",
                         [
                             SimpleScope("GeneratorExp", [SimpleScope("LocalVariable.AssignName.num", [])]),
                         ])],
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
                            ["AssignName.f", "AssignName.text"],
                            ["MemberAccessValue.f.read", "Name.f", "Name.text", "MemberAccessValue.f.close"],
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
                                    ["AssignName.self"],
                                    ["Name.self"],
                                    ["Call.print"],
                                    ["AssignName.self"]
                                ),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.__exit__",
                                    [SimpleScope("Parameter.AssignName.self", [])],
                                    ["AssignName.self"],
                                    [],
                                    ["Call.print"],
                                    ["AssignName.self"]
                                ),
                            ],
                            ["FunctionDef.__enter__", "FunctionDef.__exit__"],
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
                                            ["AssignName.x", "AssignName.y"],
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
                                            ["AssignName.x", "AssignName.y"],
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
                                            ["AssignName.x"],
                                            ["Name.x"],
                                            [],
                                            ["AssignName.x"]
                                            ),
                    ],
                ),
            ],
        ),
        (  # language=Python "Assign to dict"
            """
class A:
    d = {}

    def f(self):
        self.d["a"] = 1
            """,  # language=none
            [
                SimpleScope(
                    "Module",
                    [
                        SimpleClassScope(
                            "GlobalVariable.ClassDef.A",
                            [
                                SimpleScope("ClassVariable.AssignName.d", []),
                                SimpleFunctionScope(
                                    "ClassVariable.FunctionDef.f",
                                    [SimpleScope("Parameter.AssignName.self", [])],
                                    ["AssignName.self", "MemberAccessTarget.self.d", "Name.self"],
                                    [],
                                    [],
                                    ["AssignName.self"]
                                ),
                            ],
                            ["AssignName.d", "FunctionDef.f"],
                            [],
                        ),
                    ],
                ),
            ],
        ),
        (  # language=Python "Annotations"
            """
from typing import Union

def f(a: int | str, b: Union[int, str]) -> tuple[float, str]:
    return float(a), str(b)
            """,  # language=none
            [SimpleScope("Module", [
                SimpleScope("Import.ImportFrom.typing.Union", []),
                SimpleFunctionScope("GlobalVariable.FunctionDef.f",
                                    [SimpleScope("Parameter.AssignName.a", []),
                                     SimpleScope("Parameter.AssignName.b", [])],
                                    ["AssignName.a", "AssignName.b"],
                                    ["Name.a", "Name.b"],
                                    ["Call.float", "Call.str"],
                                    ["AssignName.a", "AssignName.b"]
                                    ),
            ])],
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
        "Multiple AssignName",
        "List Comprehension in Module",
        "List Comprehension in Class",
        "List Comprehension in Function",
        "Dict Comprehension in Module",
        "Set Comprehension in Module",
        "Generator Expression in Module",
        "With Statement",
        "With Statement File",
        "With Statement Function",
        "With Statement Class",
        "Lambda",
        "Lambda call",
        "Lambda with name",
        "Assign to dict",
        "Annotations",
    ],  # TODO: add tests for match, try except
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
            {"A": SimpleClassScope("GlobalVariable.ClassDef.A", [], [], [])},
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
                            ["AssignName.self", "Name.self", "MemberAccessTarget.self.var1"],
                            [],
                            [],
                            ["AssignName.self"]
                        ),
                    ],
                    ["FunctionDef.__init__"],
                    ["AssignAttr.var1"],
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
                            ["AssignName.self", "Name.self", "MemberAccessTarget.self.var1", "MemberAccessTarget.self.name", "MemberAccessTarget.self.state"],
                            [],
                            [],
                            ["AssignName.self"]
                        ),
                    ],
                    ["FunctionDef.__init__"],
                    ["AssignAttr.var1", "AssignAttr.name", "AssignAttr.state"],
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
                            ["AssignName.self", "Name.self", "MemberAccessTarget.self.var1"],
                            [],
                            [],
                            ["AssignName.self"]
                        ),
                    ],
                    ["FunctionDef.__init__"],
                    ["AssignAttr.var1", "AssignAttr.var1"],
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
                            ["AssignName.self", "Name.self", "MemberAccessTarget.self.var1"],
                            [],
                            [],
                            ["AssignName.self"]
                        ),
                    ],
                    ["AssignName.var1", "FunctionDef.__init__"],
                    ["AssignAttr.var1"],
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
                    [SimpleClassScope("ClassVariable.ClassDef.B", [], [], [])],
                    ["ClassDef.B"],
                    [],
                ),
                "B": SimpleClassScope("ClassVariable.ClassDef.B", [], [], []),
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
                "A": SimpleClassScope("GlobalVariable.ClassDef.A", [], [], []),
                "B": SimpleClassScope("GlobalVariable.ClassDef.B", [], [], []),
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
                "A": SimpleClassScope("GlobalVariable.ClassDef.A", [], [], []),
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
                "f": [SimpleFunctionScope("GlobalVariable.FunctionDef.f", [], [], [], [])]
            }
        ),
        (  # language=Python "Function with child"
            """
def f():
    var1 = 1
            """,  # language=none
            {
                "f": [SimpleFunctionScope("GlobalVariable.FunctionDef.f",
                                          [SimpleScope("LocalVariable.AssignName.var1", [])],
                                          ["AssignName.var1"], [], [])]
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
                                          ["AssignName.name", "AssignName.var1"],
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
                                           SimpleScope("LocalVariable.AssignName.var1", [])],
                                          ["AssignName.name", "AssignName.var1"],
                                          ["Name.name"], [])]
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
                                          [SimpleScope("LocalVariable.AssignName.var1", [])],
                                          ["AssignName.var1"],
                                          ["Name.var1"], [])]
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
                                          ["AssignName.a", "AssignName.b", "AssignName.var1"],
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
                                          ["AssignName.a", "AssignName.b", "AssignName.var1", "AssignName.var2"],
                                          ["Name.a", "Name.b", "Name.var1", "Name.var2"],
                                          [],
                                          ["AssignName.a", "AssignName.b"]
                                          )]
            }
        ),
        (  # language=Python "Function with value in call"
            """
def f(a):
    print(a)
            """,  # language=none
            {
                "f": [SimpleFunctionScope("GlobalVariable.FunctionDef.f",
                                          [
                                              SimpleScope("Parameter.AssignName.a", []),
                                          ],
                                          ["AssignName.a"],
                                          ["Name.a"],
                                          ["Call.print"],
                                          ["AssignName.a"]
                                          )]
            }
        ),
        (  # language=Python "Function with value in loop"
            """
def f(a):
    for i in range(10):
        pass

    while a:
        pass
            """,  # language=none
            {
                "f": [SimpleFunctionScope("GlobalVariable.FunctionDef.f",
                                          [
                                              SimpleScope("Parameter.AssignName.a", []),
                                              SimpleScope("LocalVariable.AssignName.i", [])
                                          ],
                                          ["AssignName.a", "AssignName.i"],
                                          ["Name.a"],
                                          ["Call.range"],
                                          ["AssignName.a"]
                                          )]
            }
        ),
        (  # language=Python "Function with call"
            """
def f():
    f()
            """,  # language=none
            {
                "f": [SimpleFunctionScope("GlobalVariable.FunctionDef.f", [], [], [], ["Call.f"])]
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
                "f": [SimpleFunctionScope("GlobalVariable.FunctionDef.f", [], [], [], ["Call.f"]),
                      SimpleFunctionScope("GlobalVariable.FunctionDef.f", [], [], [], [])]
            }
        ),
        (  # language=Python "Function with reassignment of global variable"
            """
a = True
if a:
    var1 = 10
else:
    var1 = 20

def f():
    global var1
    print(var1)
            """,  # language=none
            {
                "f": [SimpleFunctionScope("GlobalVariable.FunctionDef.f",
                                          [],
                                          [],
                                          ["Name.var1"],
                                          ["Call.print"],
                                          [],
                                          ["AssignName.var1", "AssignName.var1"])]
            }
        ),
        (  # language=Python "Functions with different uses of globals"
            """
var1, var2 = 10, 20

def f():
    global var1

def g():
    global var1, var2

def h():
    for i in range(var1):
        global var2
        pass

            """,  # language=none
            {
                "f": [SimpleFunctionScope("GlobalVariable.FunctionDef.f", [], [], [], [], [], ["AssignName.var1"])],
                "g": [SimpleFunctionScope("GlobalVariable.FunctionDef.g", [], [], [], [], [], ["AssignName.var1", "AssignName.var2"])],
                "h": [SimpleFunctionScope("GlobalVariable.FunctionDef.h", [SimpleScope("LocalVariable.AssignName.i", [])], ["AssignName.i"], ["Name.var1"], ["Call.range"], [], ["AssignName.var1", "AssignName.var2"])]
            }
        ),
        (  # language=Python "Function with shadowing of global variable"
            """
var1 = 10

def f():
    var1 = 1  # this is not a global variable
    for i in range(var1):
        pass

            """,  # language=none
            {
                "f": [SimpleFunctionScope("GlobalVariable.FunctionDef.f",
                                          [
                                              SimpleScope("LocalVariable.AssignName.var1", []),
                                              SimpleScope("LocalVariable.AssignName.i", [])
                                          ],
                                          ["AssignName.var1", "AssignName.i"],
                                          ["Name.var1"],
                                          ["Call.range"],
                                          [],
                                          [])]
            }
        ),
        (  # language=Python "Function with List Comprehension with global"
            """
nums = ["aaa", "bb", "ase"]

def f():
    global nums
    x = [len(num) for num in nums]
            """,  # language=none
            {
                "f": [SimpleFunctionScope(
                            "GlobalVariable.FunctionDef.f",
                            [
                                SimpleScope("LocalVariable.AssignName.x", []),
                                SimpleScope("ListComp", [SimpleScope("LocalVariable.AssignName.num", [])]),
                            ],
                            ["AssignName.x"],
                            ["Name.nums"],
                            ["Call.len"],
                            [],
                            ["AssignName.nums"]
                        )]
            }
        ),
        (  # language=Python "Function with List Comprehension with global and condition"
            """
nums = ["aaa", "bb", "ase"]
var1 = 10

def f():
    global nums, var1
    x = [len(num) for num in nums if var1 > 10]
            """,  # language=none
            {
                "f": [SimpleFunctionScope(
                            "GlobalVariable.FunctionDef.f",
                            [
                                SimpleScope("LocalVariable.AssignName.x", []),
                                SimpleScope("ListComp", [SimpleScope("LocalVariable.AssignName.num", [])]),
                            ],
                            ["AssignName.x"],
                            ["Name.nums", "Name.var1"],
                            ["Call.len"],
                            [],
                            ["AssignName.nums", "AssignName.var1"]
                        )]
            }
        ),
        (  # language=Python "Function with List Comprehension without global"
            """
nums = ["aaa", "bb", "ase"]

def f():
    x = [len(num) for num in nums]
            """,  # language=none
            {
                "f": [SimpleFunctionScope(
                    "GlobalVariable.FunctionDef.f",
                    [
                        SimpleScope("LocalVariable.AssignName.x", []),
                        SimpleScope("ListComp", [SimpleScope("LocalVariable.AssignName.num", [])]),
                    ],
                    ["AssignName.x"],
                    ["Name.nums"],
                    ["Call.len"],
                    [],
                    ["AssignName.nums"]
                )]
            }
        ),
        (  # language=Python "Function with Lambda with global"
            """
var1 = 1

def f():
    global var1
    return (lambda y: var1 + y)(4)
            """,  # language=none
            {
                "f": [SimpleFunctionScope(
                    "GlobalVariable.FunctionDef.f",
                    [
                        SimpleFunctionScope("LocalVariable.Lambda",
                                            [SimpleScope("Parameter.AssignName.y", [])],
                                            ["AssignName.y"],
                                            ["Name.var1", "Name.y"],
                                            [],
                                            ["AssignName.y"],
                                            ["AssignName.var1"]
                                            ),
                    ],
                    [],
                    ["Name.var1"],
                    [],
                    [],
                    ["AssignName.var1"]
                )]
            }
        ),
        (  # language=Python "Function with Lambda without global"
            """
var1 = 1

def f():
    return (lambda y: var1 + y)(4)
            """,  # language=none
            {
                "f": [SimpleFunctionScope(
                    "GlobalVariable.FunctionDef.f",
                    [
                        SimpleFunctionScope("LocalVariable.Lambda",
                                            [SimpleScope("Parameter.AssignName.y", [])],
                                            ["AssignName.y"],
                                            ["Name.var1", "Name.y"],
                                            [],
                                            ["AssignName.y"],
                                            ["AssignName.var1"]
                                            ),
                    ],
                    [],
                    ["Name.var1"],
                    [],
                    [],
                    ["AssignName.var1"]
                )]
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
        "Function with value in call",
        "Function with value in loop",
        "Function with call",
        "Function with same name",
        "Function with reassignment of global variable",
        "Functions with different uses of globals",
        "Function with shadowing of global variable",
        "Function with List Comprehension with global",
        "Function with List Comprehension with global and condition",
        "Function with List Comprehension without global",
        "Function with Lambda with global",
        "Function with Lambda without global",
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
        (  # language=Python "Multiple variables on Module Scope single assignment"
            """
var1 = 10
var2 = 20
var3 = 30
            """,  # language=none
            {"var1", "var2", "var3"},
        ),
        (  # language=Python "Multiple variables on Module Scope multiple assignment"
            """
var1, var2 = 10, 20
            """,  # language=none
            {"var1", "var2"},
        ),
        (  # language=Python "Multiple variables on Module Scope chained assignment"
            """
var1 = var2 = 10
            """,  # language=none
            {"var1", "var2"},
        ),
        (  # language=Python "Reassignment of variable on Module Scope"
            """
var1 = 1
var1 = 2
            """,  # language=none
            {"var1"},
        ),
    ],
    ids=[
        "No global variables",
        "Variable on Module Scope",
        "Multiple variables on Module Scope single assignment",
        "Multiple variables on Module Scope multiple assignment",
        "Multiple variables on Module Scope chained assignment",
        "Reassignment of variable on Module Scope"
    ]
)
def test_get_module_data_globals(code: str, expected: str) -> None:
    globs = get_module_data(code).global_variables
    transformed_globs = {f"{glob}" for glob in globs}  # The result is simplified to make the comparison easier
    assert transformed_globs == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (  # language=Python "Parameter in function scope"
            """
def local_parameter(pos_arg):
    return 2 * pos_arg
            """,  # language= None
            {"local_parameter": ["pos_arg"]},
        ),
        (  # language=Python "Parameter in function scope with keyword only"
            """
def local_parameter(*, key_arg_only):
    return 2 * key_arg_only
            """,  # language= None
            {"local_parameter": ["key_arg_only"]},
        ),
        (  # language=Python "Parameter in function scope with positional only"
            """
def local_parameter(pos_arg_only, /):
    return 2 * pos_arg_only
            """,  # language= None
            {"local_parameter": ["pos_arg_only"]},
        ),
        (  # language=Python "Parameter in function scope with default value"
            """
def local_parameter(def_arg=10):
    return def_arg
            """,  # language= None
            {"local_parameter": ["def_arg"]},
        ),
        (  # language=Python "Parameter in function scope with type annotation"
            """
def local_parameter(def_arg: int):
    return def_arg
            """,  # language= None
            {"local_parameter": ["def_arg"]},
        ),
        (  # language=Python "Parameter in function scope with *args"
            """
def local_parameter(*args):
    return args
            """,  # language= None
            {"local_parameter": ["args"]},
        ),
        (  # language=Python "Parameter in function scope with **kwargs"
            """
def local_parameter(**kwargs):
    return kwargs
            """,  # language= None
            {"local_parameter": ["kwargs"]},
        ),
        (  # language=Python "Parameter in function scope with *args and **kwargs"
            """
def local_parameter(*args, **kwargs):
    return args, kwargs
            """,  # language= None
            {"local_parameter": ["args", "kwargs"]},
        ),
        (  # language=Python "Two Parameters in function scope"
            """
def local_double_parameter(a, b):
    return a, b
            """,  # language= None
            {"local_double_parameter": ["a", "b"]},
        ),
        (  # language=Python "Two Parameters in function scope"
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
        "Parameter in function scope",
        "Parameter in function scope with keyword only",
        "Parameter in function scope with positional only",
        "Parameter in function scope with default value",
        "Parameter in function scope with type annotation",
        "Parameter in function scope with *args",
        "Parameter in function scope with **kwargs",
        "Parameter in function scope with *args and **kwargs",
        "Two parameters in function scope",
        "Two functions with same parameter name"
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
