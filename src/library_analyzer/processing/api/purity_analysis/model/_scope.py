from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import astroid

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator

    from library_analyzer.processing.api.purity_analysis.model import PurityResult


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
    global_variables : dict[str, Scope | ClassScope]
        All global variables and their Scope or ClassScope.
    value_nodes : dict[astroid.Name | MemberAccessValue, Scope | ClassScope]
        All value nodes and their Scope or ClassScope.
        Value nodes are nodes that are read from.
    target_nodes : dict[astroid.AssignName | astroid.Name | MemberAccessTarget, Scope | ClassScope]
        All target nodes and their Scope or ClassScope.
        Target nodes are nodes that are written to.
    parameters : dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]]
        All parameters of functions and a tuple of their Scope or ClassScope and a set of their target nodes.
        These are used to determine the scope of the parameters for each function.
    function_calls : dict[astroid.Call, Scope | ClassScope]
        All function calls and their Scope or ClassScope.
    function_references : dict[NodeID, Reasons]
        All nodes relevant for reference resolving inside functions.
    """

    scope: Scope | ClassScope
    classes: dict[str, ClassScope]
    functions: dict[str, list[FunctionScope]]
    global_variables: dict[str, Scope | ClassScope]
    value_nodes: dict[astroid.Name | MemberAccessValue, Scope | ClassScope]
    target_nodes: dict[
        astroid.AssignName | astroid.Name | MemberAccessTarget,
        Scope | ClassScope,
    ]
    parameters: dict[astroid.FunctionDef, tuple[Scope | ClassScope, list[astroid.AssignName]]]
    function_calls: dict[astroid.Call, Scope | ClassScope]
    function_references: dict[NodeID, Reasons]


@dataclass
class MemberAccess(astroid.NodeNG):  # TODO: since this is a subclass it should implement fromlineno and tolineno since they are expected as @cached_property
    """Represents a member access.

    Superclass for MemberAccessTarget and MemberAccessValue.
    Represents a member access, e.g. `a.b` or `a.b.c`.

    Attributes
    ----------
    receiver : MemberAccess | astroid.NodeNG
        The receiver is the node that is accessed, it can be nested, e.g. `a` in `a.b` or `a.b` in `a.b.c`.
    member : astroid.NodeNG
        The member is the node that accesses the receiver, e.g. `b` in `a.b`.
    parent : astroid.NodeNG | None
        The parent node of the member access.
    name : str
        The name of the member access, e.g. `a.b`.
        Is set in __post_init__, after the member access has been created.
    """

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

    def get_top_level_receiver(self) -> astroid.NodeNG:
        """Get the top level receiver.

        Returns
        -------
        astroid.NodeNG
            The top level receiver.
        """
        if isinstance(self.receiver, MemberAccess):
            return self.receiver.get_top_level_receiver()
        return self.receiver


@dataclass
class MemberAccessTarget(MemberAccess):
    """Represents a member access target.

    Member access target is a member access written to, e.g. `a.b` in `a.b = 1`.
    """

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class MemberAccessValue(MemberAccess):
    """Represents a member access value.

    Member access value is a member access read from, e.g. `a.b` in `print(a.b)`.
    """

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
    line : int | None
        The line of the node in the source code.
    col : int | None
        The column of the node in the source code.
    """

    module: astroid.Module | str | None
    name: str
    line: int | None = None
    col: int | None = None

    def __repr__(self) -> str:
        if self.line is None or self.col is None:
            if self.module is None:
                return f"{self.name}"
            return f"{self.module}.{self.name}"
        return f"{self.module}.{self.name}.{self.line}.{self.col}"

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class Symbol(ABC):
    """Represents a node in the scope tree.

    Attributes
    ----------
    node : astroid.NodeNG | MemberAccess
        The node that defines the symbol.
    id : NodeID
        The id of that node.
    name : str
        The name of the symbol (for easier access).
    """

    node: astroid.NodeNG | MemberAccess
    id: NodeID
    name: str

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}.line{self.id.line}"

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class Parameter(Symbol):
    """Represents a parameter of a function."""

    def __hash__(self) -> int:
        return hash(str(self))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}.line{self.id.line}"


@dataclass
class LocalVariable(Symbol):
    """Represents a local variable."""

    def __hash__(self) -> int:
        return hash(str(self))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}.line{self.id.line}"


@dataclass
class GlobalVariable(Symbol):
    """Represents a global variable."""

    def __hash__(self) -> int:
        return hash(str(self))

    def __repr__(self) -> str:
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

    def __repr__(self) -> str:
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

    def __repr__(self) -> str:
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

    def __repr__(self) -> str:
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
    _symbol : Symbol
        The symbol that defines the scope.
    _children : list[Scope | ClassScope]
        The list of Scope or ClassScope instances that are defined in the scope of the Symbol node.
        Is None if the node is a leaf node.
    _parent : Scope | ClassScope | None
        The parent node in the scope tree, there is None if the node is the root node.
    """  # TODO: Lars do we want Attributes here or in the properties?

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
    def parent(self) -> Scope | ClassScope | None:
        """Scope | ClassScope | None : Parent of the scope.

        The parent node in the scope tree.
        Is None if the node is the root node.
        """
        return self._parent

    @parent.setter
    def parent(self, new_parent: Scope | ClassScope | None) -> None:
        if not isinstance(new_parent, Scope | ClassScope | None):
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
    super_classes : list[ClassScope]
        The list of super classes of the class.
    """

    class_variables: dict[str, list[Symbol]] = field(default_factory=dict)
    instance_variables: dict[str, list[Symbol]] = field(default_factory=dict)
    super_classes: list[ClassScope] = field(default_factory=list)
    # TODO: init!


@dataclass
class FunctionScope(Scope):
    """Represents a Scope that defines the scope of a function.

    Attributes
    ----------
    values : dict[str, Symbol]
        The dict of all value nodes used inside the corresponding function.
    calls : dict[str, Scope | ClassScope]
        The dict of all function calls inside the corresponding function.
    parameters : dict[str, Parameter]
        The parameters of the function.
    globals : dict[str, GlobalVariable]
        The global variables used inside the function.
        It stores the globally assigned nodes (Assignment of the used variable).
    """

    values: dict[str, list[Symbol]] = field(default_factory=dict)
    calls: dict[str, Scope | ClassScope] = field(default_factory=dict)
    parameters: dict[str, Parameter] = field(default_factory=dict)
    globals: dict[str, list[GlobalVariable]] = field(default_factory=dict)

    def remove_call_node_by_name(self, name: str) -> None:
        """Remove a call node by name.

        Removes a call node from the dict of call nodes by name.
        This is used to remove cyclic calls from the dict of call nodes after the call graph has been built.

        Parameters
        ----------
        name  : str
            The name of the call node to remove.
        """
        self.calls.pop(name, None)


@dataclass
class Reasons:
    """
    Represents a function and the raw reasons for impurity.

    Raw reasons means that the reasons are just collected and not yet processed.

    Attributes
    ----------
    function : astroid.FunctionDef | MemberAccess | None
        The function that is analyzed.
    writes : set[Symbol]
        A set of all nodes that are written to.
    reads : set[Symbol]
        A set of all nodes that are read from.
    calls : set[Symbol]
        A set of all nodes that are called.
    result : PurityResult | None
        The result of the purity analysis
        This also works as a flag to determine if the purity analysis has already been performed:
        If it is None, the purity analysis has not been performed
    unknown_calls : list[astroid.Call | astroid.NodeNG] | None
        A list of all unknown calls.
        Unknown calls are calls to functions that are not defined in the module or are simply not existing.
    """

    function: astroid.FunctionDef | MemberAccess | None = field(default=None)
    writes: set[Symbol] = field(default_factory=set)
    reads: set[Symbol] = field(default_factory=set)
    calls: set[Symbol] = field(default_factory=set)
    result: PurityResult | None = field(default=None)
    unknown_calls: list[astroid.Call | astroid.NodeNG] | None = field(default=None)

    def __iter__(self) -> Iterator[Symbol]:
        return iter(self.writes.union(self.reads).union(self.calls))

    def get_call_by_name(self, name: str) -> Symbol:
        """Get a call by name.

        Parameters
        ----------
        name  : str
            The name of the call to get.

        Returns
        -------
        Symbol
            The Symbol of the call.

        Raises
        ------
        ValueError
            If no call to the function with the given name is found.
        """
        for call in self.calls:
            if isinstance(call.node, astroid.Call):
                # make sure we do not get an AttributeError because of the inconsistent names in the astroid API
                if isinstance(call.node.func, astroid.Attribute) and call.node.func.attrname == name:
                    return call
                return call
            else:  # noqa: PLR5501
                # make sure we do not get an AttributeError because of the inconsistent names in the astroid API
                if isinstance(call.node.func, astroid.Attribute) and call.node.attrname == name:  # noqa: SIM114
                    return call
                elif call.node.name == name:
                    return call

        raise ValueError("No call to the function found.")

    def join_reasons(self, other: Reasons) -> Reasons:
        """Join two Reasons objects.

        When a function has multiple reasons for impurity, the Reasons objects are joined.
        This means that the writes, reads, calls and unknown_calls are merged.

        Parameters
        ----------
        other : Reasons
            The other Reasons object.

        Returns
        -------
        Reasons
            The updated Reasons object.
        """
        self.writes.update(other.writes)
        self.reads.update(other.reads)
        self.calls.update(other.calls)
        # join unknown calls - since they can be None we need to deal with that
        if self.unknown_calls is not None and other.unknown_calls is not None:
            self.unknown_calls.extend(other.unknown_calls)
        elif self.unknown_calls is None and other.unknown_calls is not None:
            self.unknown_calls = other.unknown_calls
        elif other.unknown_calls is None:
            pass

        return self

    @staticmethod
    def join_reasons_list(reasons_list: list[Reasons], combined_node_name: str = None) -> Reasons:
        """Join a list of Reasons objects.

        Combines a list of Reasons objects into one Reasons object.

        Parameters
        ----------
        reasons_list : list[Reasons]
            The list of Reasons objects.

        combined_node_name : str
            Indicates if the Reasons object is a combined node.
            If it is a combined node, the function is set to None since it does not exist.

        Returns
        -------
        Reasons
            The combined Reasons object.

        Raises
        ------
        ValueError
            If the list of Reasons objects is empty.
        """
        if not reasons_list:
            raise ValueError("List of Reasons is empty.")

        result = Reasons()
        for reason in reasons_list:
            result.join_reasons(reason)
        if combined_node_name is not None:
            result.function = combined_node_name
        return result

    def remove_class_method_calls_from_reads(self) -> None:
        """Remove all class method calls from the read set.

        After all read, write and call sets have been filled, we can remove all class method calls from the read sets.
        This is necessary because class method calls are not considered to be read operations.
        This is achieved by comparing the call names and lines with the read names and lines and removing the reads if they match.
        """
        call_names_and_lines: set[tuple[str, int]] = set()
        for call in self.calls:
            if isinstance(call.node, astroid.Call):
                if isinstance(call.node.func, astroid.Attribute):
                    name_line_tuple = (call.node.func.attrname, call.node.fromlineno)
                else:
                    name_line_tuple = (call.node.func.name, call.node.lineno)

                call_names_and_lines.add(name_line_tuple)

        filtered_reads: set[Symbol] = set()

        for read in self.reads:
            if not any(  # check if the read is a class method call, differentiate between MemberAccessValue and normal Name
                f".{call_name}." in f".{read.node.name}." and read.node.member.fromlineno == call_line
                if isinstance(read.node, MemberAccessValue)
                else f".{call_name}." in f".{read.node.name}." and read.node.lineno == call_line
                for call_name, call_line in call_names_and_lines
            ):
                filtered_reads.add(read)

        self.reads = filtered_reads
