from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import astroid

if TYPE_CHECKING:
    from collections.abc import Generator


@dataclass
class ModuleData:
    """
    Contains all data collected for a module.

    Attributes
    ----------
    scope : Scope
        The module's scope, this contains all child scopes.
    classes : dict[str, ClassScope]
        All classes and their ClassScope.
    functions : dict[str, list[FunctionScope]]
        All functions and a list of their FunctionScopes.
        The value is a list since there can be multiple functions with the same name.
    global_variables : dict[str, Scope]
        All global variables and their Scope.
    value_nodes : dict[astroid.Name | MemberAccessValue, Scope]
        All value nodes and their Scope.
        Value nodes are nodes that are read from.
    target_nodes : dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope]
        All target nodes and their Scope.
        Target nodes are nodes that are written to.
    parameters : dict[astroid.FunctionDef, tuple[Scope, list[astroid.AssignName]]]
        All parameters of functions and a tuple of their Scope and a set of their target nodes.
        These are used to determine the scope of the parameters for each function.
    function_calls : dict[astroid.Call, Scope]
        All function calls and their Scope.
    """

    scope: Scope
    classes: dict[str, ClassScope]
    functions: dict[str, list[FunctionScope]]
    global_variables: dict[str, Scope]
    value_nodes: dict[astroid.Name | MemberAccessValue, Scope]
    target_nodes: dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope]
    parameters: dict[astroid.FunctionDef, tuple[Scope, list[astroid.AssignName]]]
    function_calls: dict[astroid.Call, Scope]


@dataclass
class MemberAccess(astroid.NodeNG):
    """Represents a member access.

    Superclass for MemberAccessTarget and MemberAccessValue.
    Represents a member access, e.g. `a.b` or `a.b.c`.

    Attributes
    ----------
    node : astroid.Attribute | astroid.AssignAttr
        The original node that represents the member access.
        Needed as fallback when determining the parent node if the receiver is None.
    receiver : MemberAccess | astroid.NodeNG | None
        The receiver is the node that is accessed, it can be nested, e.g. `a` in `a.b` or `a.b` in `a.b.c`.
        The receiver can be nested.
        Is None if the receiver is not of type Name, Call or Attribute
    member : str
        The member is the name of the node that accesses the receiver, e.g. `b` in `a.b`.
    parent : astroid.NodeNG | None
        The parent node of the member access.
    name : str
        The name of the member access, e.g. `a.b`.
        Is set in __post_init__, after the member access has been created.
        If the MemberAccess is nested, the name of the receiver will be set to "UNKNOWN" since it is hard to determine
        correctly for all possible cases, and we do not need it for the analysis.
    """

    node: astroid.Attribute | astroid.AssignAttr
    receiver: MemberAccess | astroid.NodeNG | None
    member: str
    parent: astroid.NodeNG | None = field(default=None)
    name: str = field(init=False)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"

    def __post_init__(self) -> None:
        if isinstance(self.receiver, astroid.AssignAttr | astroid.Attribute):
            self.name = f"{self.receiver.attrname}.{self.member}"
        elif isinstance(self.receiver, astroid.Name):
            self.name = f"{self.receiver.name}.{self.member}"
        else:
            self.name = f"UNKNOWN.{self.member}"


@dataclass
class MemberAccessTarget(MemberAccess):
    """Represents a member access target.

    Member access target is a member access written to, e.g. `a.b` in `a.b = 1`.
    """

    node: astroid.AssignAttr

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class MemberAccessValue(MemberAccess):
    """Represents a member access value.

    Member access value is a member access read from, e.g. `a.b` in `print(a.b)`.
    """

    node: astroid.Attribute

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class NodeID:
    """Represents an id of a node.

    Attributes
    ----------
    module : astroid.Module | str | None
        The module of the node.
        Is None for combined nodes.
    name : str
        The name of the node.
    line : int
        The line of the node in the source code.
        Is -1 for combined nodes, builtins or any other node that do not have a line.
    col : int | None
        The column of the node in the source code.
        Is -1 for combined nodes, builtins or any other node that do not have a line.
    """

    module: astroid.Module | str | None
    name: str
    line: int | None = None
    col: int | None = None

    def __str__(self) -> str:
        if self.line is None or self.col is None:
            if self.module is None:
                return f"{self.name}"
            return f"{self.module}.{self.name}"
        return f"{self.module}.{self.name}.{self.line}.{self.col}"

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class Symbol(ABC):
    """Represents a node that defines a Name.

    A Symbol is a node that defines a Name, e.g. a function, a class, a variable, etc.
    It can be referenced by another node.

    Attributes
    ----------
    node : astroid.NodeNG | MemberAccess
        The node that defines the symbol.
    id : NodeID
        The id of that node.
    name : str
        The name of the symbol (for easier access).
    """

    node: astroid.ClassDef | astroid.FunctionDef | astroid.AssignName | MemberAccessTarget
    id: NodeID
    name: str

    def __str__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}.line{self.id.line}"

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class Parameter(Symbol):
    """Represents a parameter of a function."""

    node: astroid.AssignName

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}.line{self.id.line}"


@dataclass
class LocalVariable(Symbol):
    """Represents a local variable."""

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}.line{self.id.line}"


@dataclass
class GlobalVariable(Symbol):
    """Represents a global variable."""

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}.line{self.id.line}"


@dataclass
class ClassVariable(Symbol):
    """Represents a class variable.

    Attributes
    ----------
    klass : astroid.ClassDef | None
        The class that defines the class variable.
    """

    klass: astroid.ClassDef | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        if self.klass is None:
            return f"{self.__class__.__name__}.UNKNOWN_CLASS.{self.name}.line{self.id.line}"
        return f"{self.__class__.__name__}.{self.klass.name}.{self.name}.line{self.id.line}"


@dataclass
class InstanceVariable(Symbol):
    """Represents an instance variable.

    Attributes
    ----------
    klass : astroid.ClassDef | None
        The class that defines the instance variable.
    """

    klass: astroid.ClassDef | None = field(default=None)

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        if self.klass is None:
            return f"{self.__class__.__name__}.UNKNOWN_CLASS.{self.name}.line{self.id.line}"
        return f"{self.__class__.__name__}.{self.klass.name}.{self.name}.line{self.id.line}"


@dataclass
class Import(Symbol):
    """Represents an import."""

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class Builtin(Symbol):
    """Represents a builtin (function)."""

    def __str__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class BuiltinOpen(Builtin):
    """Represents the builtin open like function.

    When dealing with open-like functions the call node is needed to determine the file path.

    Attributes
    ----------
    call : astroid.Call
        The call node of the open-like function.
    """

    call: astroid.Call

    def __str__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class Reference:
    """Represents a node that references a Name.

    A Reference is a node that references a Name,
    e.g., a function call, a variable read, etc.


    Attributes
    ----------
    node : astroid.Call | astroid.Name | MemberAccessValue
        The node that defines the symbol.
    id : NodeID
        The id of that node.
    name : str
        The name of the symbol (for easier access).
    """

    node: astroid.Call | astroid.Name | MemberAccessValue
    id: NodeID
    name: str

    def __str__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}.line{self.id.line}"

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
    _symbol : Symbol
        The symbol that defines the scope.
    _children : list[Scope | ClassScope]
        The list of Scope or ClassScope instances that are defined in the scope of the Symbol node.
        Is None if the node is a leaf node.
    _parent : Scope | ClassScope | None
        The parent node in the scope tree, there is None if the node is the root node.
    """

    _symbol: Symbol
    _children: list[Scope] = field(default_factory=list)
    _parent: Scope | None = None

    def __iter__(self) -> Generator[Scope | ClassScope, None, None]:
        yield self

    def __next__(self) -> Scope | ClassScope:
        return self

    def __str__(self) -> str:
        return f"{self.symbol.name}.line{self.symbol.id.line}"

    def __hash__(self) -> int:
        return hash(str(self))

    @property
    def symbol(self) -> Symbol:
        """Symbol : The symbol that defines the scope."""
        return self._symbol

    @symbol.setter
    def symbol(self, new_symbol: Symbol) -> None:
        if not isinstance(new_symbol, Symbol):
            raise TypeError("Invalid node type.")
        self._symbol = new_symbol

    @property
    def children(self) -> list[Scope | ClassScope]:
        """list[Scope | ClassScope] : Children of the scope.

        The list of Scope or ClassScope instances that are defined in the scope of the Symbol node.
        Is None if the node is a leaf node.
        """
        return self._children

    @children.setter
    def children(self, new_children: list[Scope | ClassScope]) -> None:
        if not isinstance(new_children, list):
            raise TypeError("Children must be a list.")
        self._children = new_children

    @property
    def parent(self) -> Scope | None:
        """Scope | ClassScope | None : Parent of the scope.

        The parent node in the scope tree.
        Is None if the node is the root node.
        """
        return self._parent

    @parent.setter
    def parent(self, new_parent: Scope | None) -> None:
        if not isinstance(new_parent, Scope | None):
            raise TypeError("Invalid parent type.")
        self._parent = new_parent

    def get_module_scope(self) -> Scope:
        """Return the module scope.

        Gets the module scope for each scope in the scope tree.
        The module scope is the root node of the scope tree.

        Returns
        -------
        Scope
            The module scope.
        """
        if self.parent is None:
            return self
        return self.parent.get_module_scope()


@dataclass
class ClassScope(Scope):
    """Represents a Scope that defines the scope of a class.

    Attributes
    ----------
    class_variables : dict[str, list[Symbol]]
        The name of the class variable and a list of its Symbols (which represent a declaration).
        There can be multiple declarations of the same class variable, e.g. `a = 1` and `a = 2`
        since we cannot determine which one is used since we do not analyze the control flow.
        Also, it is impossible to distinguish between a declaration and a reassignment.
    instance_variables : dict[str, list[Symbol]]
        The name of the instance variable and a list of its Symbols (which represent a declaration).
    init_function : FunctionScope | None
        The init function of the class if it exists else None.
    super_classes : list[ClassScope]
        The list of super classes of the class if any.
    """

    class_variables: dict[str, list[Symbol]] = field(default_factory=dict)
    instance_variables: dict[str, list[Symbol]] = field(default_factory=dict)
    init_function: FunctionScope | None = None
    super_classes: list[ClassScope] = field(default_factory=list)


@dataclass
class FunctionScope(Scope):
    """Represents a Scope that defines the scope of a function.

    Attributes
    ----------
    target_symbols : dict[str, list[Symbol]]
        The dict of all target nodes used inside the corresponding function.
        Target nodes are specified as all nodes that can be written to and which can be represented as a Symbol.
        This includes assignments, parameters,
    value_references : dict[str, list[Reference]]
        The dict of all value nodes used inside the corresponding function.
    call_references : dict[str, list[Reference]]
        The dict of all function calls inside the corresponding function.
        The key is the name of the call node, the value is a list of all References of call nodes with that name.
    parameters : dict[str, Parameter]
        The parameters of the function.
    globals_used : dict[str, list[GlobalVariable]]
        The global variables used inside the function.
        It stores the globally assigned nodes (Assignment of the used variable).
    """

    target_symbols: dict[str, list[Symbol]] = field(default_factory=dict)
    value_references: dict[str, list[Reference]] = field(default_factory=dict)
    call_references: dict[str, list[Reference]] = field(default_factory=dict)
    parameters: dict[str, Parameter] = field(default_factory=dict)
    globals_used: dict[str, list[GlobalVariable]] = field(default_factory=dict)

    def remove_call_reference_by_id(self, call_id: str) -> None:
        """Remove a call node by name.

        Removes a call node from the dict of call nodes by name.
        This is used to remove cyclic calls from the dict of call nodes after the call graph has been built.

        Parameters
        ----------
        call_id  : str
            The name of the call node to remove.
        """
        self.call_references.pop(call_id, None)
