from __future__ import annotations

from dataclasses import dataclass, field
from abc import ABC
from types import NoneType

import astroid

from library_analyzer.processing.api.model import Expression, Reference


@dataclass
class ModuleData:
    """
    Contains all data that is collected for a module.
    scope: The module's scope, this contains all child scopes.
    classes: All classes and their scope.
    functions: All functions and their scope.
    globals: All global variables and their scope.
    names: All names that are defined in the module and their scope.
    parameters: All parameters of functions and their scope.
    names_list: All names that are defined in the module.
    function_calls: All function calls and their scope.
    """
    scope: Scope | ClassScope
    classes: dict[str, ClassScope]
    functions: dict[str, Scope | list[Scope]]
    # members: dict[str, list[Symbol]]  # this contains all names of function names and attribute names and their declaratioon
    globals: dict[str, Scope | ClassScope]
    value_nodes: dict[astroid.Name | MemberAccessValue, Scope | ClassScope]
    target_nodes: dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope | ClassScope]
    parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, set[astroid.AssignName]]]
    function_calls: dict[astroid.Call, Scope | ClassScope]


@dataclass
class MemberAccess(Expression):
    receiver: MemberAccess | astroid.NodeNG
    member: astroid.NodeNG
    parent: astroid.NodeNG | None = field(default=None)
    name: str = field(init=False)

    # TODO: when detecting MemberAccess, we will only search for the nodes name in all class scopes ->
    #  add a list of all classes of a module to easily access their instance nodes (their names)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"

    def __hash__(self) -> int:
        return hash(str(self))

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

    def __str__(self) -> str:
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

    def __str__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}.line{self.id.line}"

    def __eq__(self, other: Symbol) -> bool:
        if isinstance(other, Symbol):
            return self.name == other.name and self.id == other.id
        return False

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class Parameter(Symbol):  # TODO: find correct node type and add fields with further infos for each subclass
    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class LocalVariable(Symbol):
    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class GlobalVariable(Symbol):
    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class ClassVariable(Symbol):
    klass: astroid.ClassDef | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        if self.klass is None:
            return f"{self.__class__.__name__}.UNKNOWN_CLASS.{self.name}.line{self.id.line}"
        return f"{self.__class__.__name__}.{self.klass.name}.{self.name}.line{self.id.line}"


@dataclass
class InstanceVariable(Symbol):
    klass: astroid.ClassDef | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}.{self.klass.name}.{self.name}.line{self.id.line}"


@dataclass
class Import(Symbol):
    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class Builtin(Symbol):
    def __str__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"

    def __hash__(self) -> int:
        return hash(str(self))


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

    _symbol: Symbol = field(default_factory=Symbol)
    _children: list[Scope | ClassScope] = field(default_factory=list)
    _parent: Scope | ClassScope | None = None

    def __iter__(self) -> Scope | ClassScope:
        yield self

    def __next__(self) -> Scope | ClassScope:
        return self

    def __str__(self) -> str:
        return f"{self.__class__.__name__}.{self.symbol.name}.line{self.symbol.id.line}"

    def root(self) -> Scope | ClassScope:
        if self.parent:
            return self.parent.root()
        return self

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
    def parent(self, new_parent: Scope | ClassScope | NoneType) -> None:
        if not isinstance(new_parent, (Scope, ClassScope, NoneType)):
            raise TypeError("Invalid parent type.")
        self._parent = new_parent


@dataclass
class ClassScope(Scope):
    """Represents a Scope that defines the scope of a class.

    Attributes
    ----------
        class_variables     is a list of AssignName nodes that define class variables
        instance_variables  is a list of AssignAttr nodes that define instance variables
        super_classes       is a list of ClassScope instances that represent the super classes of the class
    """

    class_variables: dict[str, astroid.AssignName] = field(default_factory=dict)  # right now, we do not cover the unlikely case of multiple class variables with the same name
    instance_variables: dict[str, astroid.AssignAttr] = field(default_factory=dict)  # right now, we do not cover the unlikely case of multiple instance variables with the same name
    super_classes: list[ClassScope] | None = field(default=None)
