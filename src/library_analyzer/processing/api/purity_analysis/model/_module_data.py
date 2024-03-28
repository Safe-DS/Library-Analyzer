from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import astroid

if TYPE_CHECKING:
    from collections.abc import Iterator


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
    imports : dict[str, Import]
        All imported symbols.
    """

    scope: Scope
    classes: dict[str, ClassScope]
    functions: dict[str, list[FunctionScope]]
    imports: dict[str, Import]


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

    @classmethod
    def construct_member_access_target(cls, node: astroid.Attribute | astroid.AssignAttr) -> MemberAccessTarget:
        """Construct a MemberAccessTarget node.

        Construct a MemberAccessTarget node from an Attribute or AssignAttr node.
        The receiver is the node that is accessed, and the member is the node that accesses the receiver.
        The receiver can be nested.

        Parameters
        ----------
        node : astroid.Attribute | astroid.AssignAttr
            The node to construct the MemberAccessTarget node from.

        Returns
        -------
        MemberAccessTarget
            The constructed MemberAccessTarget node.
        """
        receiver = node.expr
        member = node.attrname

        try:
            if isinstance(receiver, astroid.Name):
                return MemberAccessTarget(node=node, receiver=receiver, member=member)
            elif isinstance(receiver, astroid.Call):
                return MemberAccessTarget(node=node, receiver=receiver.func, member=member)
            elif isinstance(receiver, astroid.Attribute):
                return MemberAccessTarget(
                    node=node,
                    receiver=cls.construct_member_access_target(receiver),
                    member=member,
                )
            else:
                return MemberAccessTarget(node=node, receiver=None, member=member)
        # Since it is tedious to add testcases for this function, ignore the coverage for now
        except TypeError as err:  # pragma: no cover
            raise TypeError(f"Unexpected node type {type(node)}") from err  # pragma: no cover


@dataclass
class MemberAccessValue(MemberAccess):
    """Represents a member access value.

    Member access value is a member access read from, e.g. `a.b` in `print(a.b)`.
    """

    node: astroid.Attribute

    def __hash__(self) -> int:
        return hash(str(self))

    @classmethod
    def construct_member_access_value(cls, node: astroid.Attribute) -> MemberAccessValue:
        """Construct a MemberAccessValue node.

        Construct a MemberAccessValue node from an Attribute node.
        The receiver is the node that is accessed, and the member is the node that accesses the receiver.
        The receiver can be nested.

        Parameters
        ----------
        node : astrid.Attribute
            The node to construct the MemberAccessValue node from.

        Returns
        -------
        MemberAccessValue
            The constructed MemberAccessValue node.
        """
        receiver = node.expr
        member = node.attrname

        try:
            if isinstance(receiver, astroid.Name):
                return MemberAccessValue(node=node, receiver=receiver, member=member)
            elif isinstance(receiver, astroid.Call):
                return MemberAccessValue(node=node, receiver=receiver.func, member=member)
            elif isinstance(receiver, astroid.Attribute):
                return MemberAccessValue(node=node, receiver=cls.construct_member_access_value(receiver), member=member)
            else:
                return MemberAccessValue(node=node, receiver=None, member=member)
        # Since it is tedious to add testcases for this function, ignore the coverage for now
        except TypeError as err:  # pragma: no cover
            raise TypeError(f"Unexpected node type {type(node)}") from err  # pragma: no cover


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
        Is None for combined nodes, builtins or any other node that do not have a line.
    col : int | None
        The column of the node in the source code.
        Is None for combined nodes, builtins or any other node that do not have a line.
    """

    module: astroid.Module | str | None
    name: str
    line: int | None = None
    col: int | None = None

    def __str__(self) -> str:
        if isinstance(self.module, astroid.Module):
            self.module = self.module.name

        if self.module is not None:
            if self.line is not None and self.col is not None:
                return f"{self.module}.{self.name}.{self.line}.{self.col}"
            else:
                return f"{self.module}.{self.name}"
        elif self.line is not None and self.col is not None:
            return f"{self.name}.{self.line}.{self.col}"
        else:
            return f"{self.name}"

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other):
        if not isinstance(other, NodeID):
            raise TypeError(f"Cannot compare NodeID with {type(other)}")
        return self.module == other.module and self.name == other.name and self.line == other.line and self.col == other.col

    def __lt__(self, other):
        if not isinstance(other, NodeID):
            raise TypeError(f"Cannot compare NodeID with {type(other)}")

        if self.line is None:
            if other.line is None:
                return False  # Both lines are None, consider them equal
            return True  # self.line is None, other.line is not, so other is greater
        elif other.line is None:
            return False  # other.line is None, self.line is not, so self is greater

        if self.line != other.line:
            return self.line < other.line

        if self.col != other.col:
            return self.col < other.col

        # If both line and column are equal, compare by name,
        return self.name < other.name

    @classmethod
    def calc_node_id(
        cls,
        node: (
            astroid.NodeNG
            | astroid.Module
            | astroid.ClassDef
            | astroid.FunctionDef
            | astroid.AssignName
            | astroid.Name
            | astroid.AssignAttr
            | astroid.Import
            | astroid.ImportFrom
            | astroid.Call
            | astroid.Lambda
            | astroid.ListComp
            | MemberAccess
        ),
    ) -> NodeID:
        """Calculate the NodeID of the given node.

        The NodeID is calculated by using the name of the module, the name of the node, the line number and the column offset.
        The NodeID is used to identify nodes in the module.

        Parameters
        ----------
        node : astroid.NodeNG | astroid.Module | astroid.ClassDef | astroid.FunctionDef | astroid.AssignName | astroid.Name | astroid.AssignAttr | astroid.Import | astroid.ImportFrom | astroid.Call | astroid.Lambda | astroid.ListComp | MemberAccess

        Returns
        -------
        NodeID
            The NodeID of the given node.
        """
        if isinstance(node, MemberAccess):
            module = node.node.root().name
        else:
            module = node.root().name

        match node:
            case astroid.Module():
                return NodeID(None, node.name, 0, 0)
            case astroid.ClassDef():
                return NodeID(module, node.name, node.lineno, node.col_offset)
            case astroid.FunctionDef():
                return NodeID(module, node.name, node.fromlineno, node.col_offset)
            case astroid.AssignName():
                return NodeID(module, node.name, node.lineno, node.col_offset)
            case astroid.Name():
                return NodeID(module, node.name, node.lineno, node.col_offset)
            case MemberAccess():
                return NodeID(module, node.name, node.node.lineno, node.node.col_offset)
            case astroid.Import():  # TODO: we need a special treatment for imports and import from
                return NodeID(module, node.names[0][0], node.lineno, node.col_offset)
            case astroid.ImportFrom():
                return NodeID(module, node.names[0][1], node.lineno, node.col_offset)
            case astroid.AssignAttr():
                return NodeID(module, node.attrname, node.lineno, node.col_offset)
            case astroid.Call():
                # Make sure there is no AttributeError because of the inconsistent names in the astroid API.
                if isinstance(node.func, astroid.Attribute):
                    return NodeID(module, node.func.attrname, node.lineno, node.col_offset)
                elif isinstance(node.func, astroid.Name):
                    return NodeID(module, node.func.name, node.lineno, node.col_offset)
                else:
                    return NodeID(module, "UNKNOWN", node.lineno, node.col_offset)
            case astroid.Lambda():
                if isinstance(node.parent, astroid.Assign) and node.name != "LAMBDA":
                    return NodeID(module, node.name, node.lineno, node.col_offset)
                return NodeID(module, "LAMBDA", node.lineno, node.col_offset)
            case astroid.ListComp():
                return NodeID(module, "LIST_COMP", node.lineno, node.col_offset)
            case astroid.NodeNG():
                return NodeID(module, node.as_string(), node.lineno, node.col_offset)
            case _:
                raise ValueError(f"Node type {node.__class__.__name__} is not supported yet.")


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
    """Represents an import.

    Attributes
    ----------
    node : astroid.ImportFrom | astroid.Import
        The node that defines the import.
    name : str
        The name of the symbol that is imported if any is given.
        Else it is equal to the module name.
    module : str
        The name of the module that is imported.
    alias : str | None
        If the node is of type Import alias is the alias name for the module name if any is given.
        If the node is of type ImportFrom alias is the alias name for the name of the symbol if any is given.
    inferred_node : astroid.NodeNG | None
        When the import is used as a reference (or a symbol)
        the inferred_node is the node of the used reference (or symbol) in the original module.
        It was inferred by the reference analysis by using astroids safe_infer method.
        If the method could not infer the node, the inferred_node is None.
    call: astroid.Call | None
        The original call node as fallback for the case, that the purity of the inferred_node cannot be inferred.
        Only is set if the symbol represents a call.
    """

    node: astroid.ImportFrom | astroid.Import
    module: str
    alias: str | None = None
    inferred_node: astroid.NodeNG | None = None
    call: astroid.Call | None = None

    def __str__(self) -> str:
        if isinstance(self.node, astroid.ImportFrom):
            if self.name:
                return f"{self.__class__.__name__}.{self.module}.{self.name}.line{self.id.line}"
            return f"{self.__class__.__name__}.{self.module}.line{self.id.line}"
        else:
            if self.name != self.module:
                return f"{self.__class__.__name__}.{self.module}.{self.name}.line{self.id.line}"
            return f"{self.__class__.__name__}.{self.module}.line{self.id.line}"

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class Builtin(Symbol):
    """Represents a builtin (function).

    Attributes
    ----------
    call : astroid.Call
        The call node of the function.
    """

    call: astroid.Call

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
class CombinedSymbol(Symbol):
    """Represents a combined symbol.

    A combined symbol is used to represent a combined node in the call graph.
    Since the node for a combined node does not exist, it is set to None.


    Attributes
    ----------
    node : None

    """

    node: None

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"


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
        if self.id is None:
            return f"{self.__class__.__name__}.{self.name}"
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

    def __iter__(self) -> Iterator[Scope | ClassScope]:
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
        The list of superclasses of the class if any.
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
