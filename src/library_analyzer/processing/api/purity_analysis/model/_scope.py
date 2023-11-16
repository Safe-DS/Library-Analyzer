from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable

import astroid

if TYPE_CHECKING:
    from collections.abc import Generator


@dataclass
class ModuleData:
    """
    Contains all data that is collected for a module.

    Attributes
    ----------
        scope               The module's scope, this contains all child scopes.
        classes             All classes and their scope.
        functions           All functions and their scope.
        global_variables    All global variables and their scope.
        value_nodes         All value nodes and their scope.
        target_nodes        All target nodes and their scope.
        parameters          All parameters of functions and their scope.
        function_calls      All function calls and their scope.
        function_references All for reference resolving relevant nodes inside of functions
    """

    scope: Scope | ClassScope
    classes: dict[str, ClassScope]
    functions: dict[str, list[FunctionScope]]
    global_variables: dict[str, Scope | ClassScope]
    value_nodes: dict[astroid.Name | MemberAccessValue, Scope | ClassScope]  # TODO: dict[str, list[Scope]]
    target_nodes: dict[
        astroid.AssignName | astroid.Name | MemberAccessTarget,
        Scope | ClassScope,
    ]  # TODO: dict[str, list[Scope]]
    parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, set[astroid.AssignName]]]
    function_calls: dict[astroid.Call, Scope | ClassScope]
    function_references: dict[str, Reasons]


@dataclass
class MemberAccess(astroid.NodeNG):
    receiver: MemberAccess | astroid.NodeNG
    member: astroid.NodeNG
    parent: astroid.NodeNG | None = field(default=None)
    name: str = field(init=False)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"

    def __post_init__(self) -> None:
        if isinstance(self.receiver, astroid.Call):
            self.expression = self.receiver.func
        if isinstance(self.member, astroid.AssignAttr | astroid.Attribute):
            self.name = f"{self.receiver.name}.{self.member.attrname}"
        else:
            self.name = f"{self.receiver.name}.{self.member.name}"


@dataclass
class MemberAccessTarget(MemberAccess):
    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class MemberAccessValue(MemberAccess):
    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class NodeID:
    module: astroid.Module | str
    name: str
    line: int
    col: int

    def __repr__(self) -> str:
        return f"{self.module}.{self.name}.{self.line}.{self.col}"


@dataclass
class Symbol(ABC):
    """Represents a node in the scope tree.

    Attributes
    ----------
        node    is the node which defines the symbol.
        id      is the id of the node.
        name    is the name of the symbol.

    """

    node: astroid.NodeNG | MemberAccess
    id: NodeID
    name: str

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}.line{self.id.line}"


@dataclass
class Parameter(Symbol):
    def __hash__(self) -> int:
        return hash(str(self))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}.line{self.id.line}"


@dataclass
class LocalVariable(Symbol):
    def __hash__(self) -> int:
        return hash(str(self))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}.line{self.id.line}"


@dataclass
class GlobalVariable(Symbol):
    def __hash__(self) -> int:
        return hash(str(self))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}.line{self.id.line}"


@dataclass
class ClassVariable(Symbol):
    klass: astroid.ClassDef | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __repr__(self) -> str:
        if self.klass is None:
            return f"{self.__class__.__name__}.UNKNOWN_CLASS.{self.name}.line{self.id.line}"
        return f"{self.__class__.__name__}.{self.klass.name}.{self.name}.line{self.id.line}"


@dataclass
class InstanceVariable(Symbol):
    klass: astroid.ClassDef | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __repr__(self) -> str:
        if self.klass is None:
            return f"{self.__class__.__name__}.UNKNOWN_CLASS.{self.name}.line{self.id.line}"
        return f"{self.__class__.__name__}.{self.klass.name}.{self.name}.line{self.id.line}"


@dataclass
class Import(Symbol):
    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class Builtin(Symbol):
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"


@dataclass
class Scope:
    """Represents a node in the scope tree.

    The scope tree is a tree that represents the scope of a module. It is used to determine the scope of a reference.
    On the top level, there is a ScopeNode for the module. Each Scope has a list of children, which are the nodes
    that are defined in the scope of the node. Each Scope also has a reference to its parent node.

    Attributes
    ----------
        _symbol      is the symbol that defines the scope of the node.
        _children    is a list of Scope or ClassScope instances that are defined in the scope of the node, is None if the node is a leaf node.
        _parent      is the parent node in the scope tree, is None if the node is the root node.
    """

    _symbol: Symbol
    _children: list[Scope | ClassScope] = field(default_factory=list)
    _parent: Scope | ClassScope | None = None

    def __iter__(self) -> Generator[Scope | ClassScope, None, None]:
        yield self

    def __next__(self) -> Scope | ClassScope:
        return self

    def __repr__(self) -> str:
        return f"{self.symbol.name}.line{self.symbol.id.line}"

    def __hash__(self) -> int:
        return hash(str(self))

    @property
    def symbol(self) -> Symbol:
        return self._symbol

    @symbol.setter
    def symbol(self, new_symbol: Symbol) -> None:
        if not isinstance(new_symbol, Symbol):
            raise TypeError("Invalid node type.")
        self._symbol = new_symbol

    @property
    def children(self) -> list[Scope | ClassScope]:
        return self._children

    @children.setter
    def children(self, new_children: list[Scope | ClassScope]) -> None:
        if not isinstance(new_children, list):
            raise TypeError("Children must be a list.")
        self._children = new_children

    @property
    def parent(self) -> Scope | ClassScope | None:
        return self._parent

    @parent.setter
    def parent(self, new_parent: Scope | ClassScope | None) -> None:
        if not isinstance(new_parent, Scope | ClassScope | None):
            raise TypeError("Invalid parent type.")
        self._parent = new_parent


@dataclass
class ClassScope(Scope):
    """Represents a Scope that defines the scope of a class.

    Attributes
    ----------
        class_variables     a dict of class variables and their Symbols
        instance_variables  a dict of instance variables and their Symbols
        super_classes       a list of ClassScope instances that represent the super classes of the class
    """

    class_variables: dict[str, list[Symbol]] = field(default_factory=dict)
    instance_variables: dict[str, list[Symbol]] = field(default_factory=dict)
    super_classes: list[ClassScope] = field(default_factory=list)


@dataclass
class FunctionScope(Scope):
    """Represents a Scope that defines the scope of a function.

    Attributes
    ----------
        values      a list of all value nodes in the scope
        calls       a set of all called functions in the scope
    """

    # parameters: dict[str, list[Symbol]] = field(default_factory=dict)
    values: list[Scope | ClassScope] = field(default_factory=list)
    calls: list[Scope | ClassScope] = field(default_factory=list)

    def __getitem__(self, item):
        return self.values[item]

    def remove_call_node_by_name(self, name: str) -> None:
        for call in self.calls:
            if call.symbol.name == name:
                self.calls.remove(call)
                break


@dataclass
class Reasons:
    """
    Contains all reasons why a function is not pure.

    Attributes
    ----------
        function_name   the name of the function
        writes          a set of all nodes that are written to
        reads           a set of all nodes that are read from
        calls           a set of all nodes that are called
    """
    function_name: astroid.FunctionDef
    writes: set[FunctionReference] = field(default_factory=set)
    reads: set[FunctionReference] = field(default_factory=set)
    calls: set[FunctionReference] = field(default_factory=set)

    def __iter__(self) -> Iterable[FunctionReference]:
        return iter(self.writes.union(self.reads).union(self.calls))

    def has_reasons(self) -> bool:
        return len(self.writes) > 0 or len(self.reads) > 0 or len(self.calls) > 0

    def has_calls(self) -> bool:
        return len(self.calls) > 0

    def join_reasons(self, other: Reasons) -> Reasons:
        self.writes.update(other.writes)
        self.reads.update(other.reads)
        self.calls.update(other.calls)
        return self

    @staticmethod
    def join_reasons_list(reasons_list: list[Reasons]) -> Reasons:
        if not reasons_list:
            raise ValueError("List of Reasons is empty.")

        for reason in reasons_list:
            reasons_list[0].join_reasons(reason)
        return reasons_list[0]


@dataclass
class FunctionReference:  # TODO: find a better name for this class  # FunctionPointer?
    node: astroid.NodeNG
    kind: str

    def __hash__(self) -> int:
        return hash(str(self))
